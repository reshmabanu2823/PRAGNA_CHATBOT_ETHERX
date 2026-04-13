import mongoose from 'mongoose'

const messageSchema = new mongoose.Schema(
  {
    _id: mongoose.Schema.Types.ObjectId,
    chat_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Chat',
      required: true,
      index: true,
    },
    sender_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
      index: true,
    },
    content: {
      type: String,
      required: true,
      maxlength: 5000,
    },
    message_type: {
      type: String,
      enum: ['text', 'image', 'file', 'system', 'voice'],
      default: 'text',
    },
    attachments: [
      {
        type: String,
        url: String,
        name: String,
        size: Number,
        mime_type: String,
      },
    ],
    edited_at: Date,
    edited_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
    },
    is_deleted: {
      type: Boolean,
      default: false,
    },
    deleted_at: Date,
    // Reactions (emoji counts)
    reactions: [
      {
        emoji: String,
        user_ids: [mongoose.Schema.Types.ObjectId],
      },
    ],
    // Mentions
    mentions: [
      {
        user_id: {
          type: mongoose.Schema.Types.ObjectId,
          ref: 'User',
        },
        mentioned_at: Date,
      },
    ],
    reply_to: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Message',
    },
    read_by: [
      {
        user_id: {
          type: mongoose.Schema.Types.ObjectId,
          ref: 'User',
        },
        read_at: Date,
      },
    ],
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
messageSchema.index({ chat_id: 1, created_at: -1 })
messageSchema.index({ sender_id: 1 })
messageSchema.index({ created_at: -1 })
messageSchema.index({ chat_id: 1, is_deleted: 1 })
messageSchema.index({ content: 'text' }) // Full-text search

// Pre-save middleware
messageSchema.pre('save', function (next) {
  this.updated_at = new Date()
  next()
})

// Method to soft delete
messageSchema.methods.softDelete = function () {
  this.is_deleted = true
  this.deleted_at = new Date()
  return this.save()
}

// Method to add reaction
messageSchema.methods.addReaction = function (emoji, userId) {
  let reaction = this.reactions.find((r) => r.emoji === emoji)

  if (!reaction) {
    reaction = { emoji, user_ids: [] }
    this.reactions.push(reaction)
  }

  if (!reaction.user_ids.includes(userId)) {
    reaction.user_ids.push(userId)
  }

  return this.save()
}

// Method to remove reaction
messageSchema.methods.removeReaction = function (emoji, userId) {
  const reaction = this.reactions.find((r) => r.emoji === emoji)

  if (reaction) {
    reaction.user_ids = reaction.user_ids.filter((id) => id.toString() !== userId.toString())

    if (reaction.user_ids.length === 0) {
      this.reactions = this.reactions.filter((r) => r.emoji !== emoji)
    }
  }

  return this.save()
}

// Method to mark as read
messageSchema.methods.markAsRead = function (userId) {
  const alreadyRead = this.read_by.find((r) => r.user_id.toString() === userId.toString())

  if (!alreadyRead) {
    this.read_by.push({
      user_id: userId,
      read_at: new Date(),
    })
  }

  return this.save()
}

export const Message = mongoose.model('Message', messageSchema)
