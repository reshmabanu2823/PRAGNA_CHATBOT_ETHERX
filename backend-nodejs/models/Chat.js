import mongoose from 'mongoose'

const userChatStateSchema = new mongoose.Schema({
  user_id: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true,
  },
  is_pinned: {
    type: Boolean,
    default: false,
  },
  is_archived: {
    type: Boolean,
    default: false,
  },
  is_muted: {
    type: Boolean,
    default: false,
  },
  unread_count: {
    type: Number,
    default: 0,
  },
  last_read_at: Date,
})

const chatSchema = new mongoose.Schema(
  {
    _id: mongoose.Schema.Types.ObjectId,
    title: {
      type: String,
      required: true,
      trim: true,
      maxlength: 100,
      index: true,
    },
    description: String,
    is_group: {
      type: Boolean,
      default: false,
    },
    participants: [
      {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
      },
    ],
    created_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    admin_ids: [
      {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
      },
    ],
    is_deleted: {
      type: Boolean,
      default: false,
      index: true,
    },
    deleted_at: Date,
    deleted_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
    },
    share_token: {
      type: String,
      unique: true,
      sparse: true,
      index: true,
    },
    share_token_expires_at: Date,
    is_shared: {
      type: Boolean,
      default: false,
    },
    share_access_count: {
      type: Number,
      default: 0,
    },
    // Per-user state mapping (pin, archive per user)
    user_states: [userChatStateSchema],
    last_message: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Message',
    },
    message_count: {
      type: Number,
      default: 0,
    },
    avatar_url: String,
    tags: [String],
    settings: {
      allow_new_members: {
        type: Boolean,
        default: true,
      },
      require_admin_approval: {
        type: Boolean,
        default: false,
      },
      allow_search_history: {
        type: Boolean,
        default: true,
      },
    },
    created_at: {
      type: Date,
      default: Date.now,
      index: true,
    },
    updated_at: {
      type: Date,
      default: Date.now,
    },
  },
  { timestamps: true }
)

// Indexes for performance
chatSchema.index({ participants: 1 })
chatSchema.index({ created_by: 1 })
chatSchema.index({ title: 'text', description: 'text' }) // Full-text search
chatSchema.index({ created_at: -1 })
chatSchema.index({ 'user_states.user_id': 1 })
chatSchema.index({ is_deleted: 1 })
chatSchema.index({ share_token: 1 })

// Pre-save middleware
chatSchema.pre('save', function (next) {
  this.updated_at = new Date()
  next()
})

// Virtual for active participants (non-deleted)
chatSchema.virtual('active_participants_count').get(function () {
  return this.participants?.length || 0
})

// Method to get chat state for a specific user
chatSchema.methods.getUserState = function (userId) {
  return (
    this.user_states.find((state) => state.user_id.toString() === userId.toString()) ||
    null
  )
}

// Method to update user state
chatSchema.methods.updateUserState = function (userId, updates) {
  let userState = this.user_states.find((state) => state.user_id.toString() === userId.toString())

  if (!userState) {
    userState = {
      user_id: userId,
      ...updates,
    }
    this.user_states.push(userState)
  } else {
    Object.assign(userState, updates)
  }

  return userState
}

// Method to soft delete
chatSchema.methods.softDelete = function (deletedBy) {
  this.is_deleted = true
  this.deleted_at = new Date()
  this.deleted_by = deletedBy
  return this.save()
}

// Method to hard delete (be careful!)
chatSchema.methods.hardDelete = async function () {
  await mongoose.model('Message').deleteMany({ chat_id: this._id })
  return this.deleteOne()
}

export const Chat = mongoose.model('Chat', chatSchema)
