import mongoose from 'mongoose'

const activityLogSchema = new mongoose.Schema(
  {
    _id: mongoose.Schema.Types.ObjectId,
    chat_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Chat',
      required: true,
      index: true,
    },
    actor_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    action: {
      type: String,
      enum: [
        'chat_created',
        'chat_renamed',
        'chat_pinned',
        'chat_unpinned',
        'chat_archived',
        'chat_unarchived',
        'chat_deleted',
        'chat_restored',
        'user_added',
        'user_removed',
        'admin_promoted',
        'admin_demoted',
        'group_settings_changed',
        'chat_shared',
        'share_link_revoked',
      ],
      index: true,
    },
    target_user_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
    },
    old_value: mongoose.Schema.Types.Mixed,
    new_value: mongoose.Schema.Types.Mixed,
    metadata: mongoose.Schema.Types.Mixed,
    created_at: {
      type: Date,
      default: Date.now,
      index: true,
    },
  },
  { timestamps: false }
)

// Indexes
activityLogSchema.index({ chat_id: 1, created_at: -1 })
activityLogSchema.index({ actor_id: 1, created_at: -1 })
activityLogSchema.index({ action: 1 })

export const ActivityLog = mongoose.model('ActivityLog', activityLogSchema)
