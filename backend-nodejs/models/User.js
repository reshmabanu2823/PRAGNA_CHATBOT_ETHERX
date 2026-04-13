import mongoose from 'mongoose'

const userSchema = new mongoose.Schema(
  {
    _id: mongoose.Schema.Types.ObjectId,
    name: {
      type: String,
      required: true,
      trim: true,
      minlength: 1,
      maxlength: 50,
    },
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      match: [/^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$/, 'Please enter a valid email'],
    },
    password: {
      type: String,
      required: true,
      minlength: 6,
      select: false,
    },
    avatar_url: String,
    phone: String,
    is_active: {
      type: Boolean,
      default: true,
    },
    last_seen: Date,
    created_at: {
      type: Date,
      default: Date.now,
    },
    updated_at: {
      type: Date,
      default: Date.now,
    },
  },
  { timestamps: true }
)

// Indexes for performance
userSchema.index({ email: 1 }, { unique: true })
userSchema.index({ created_at: -1 })
userSchema.index({ last_seen: -1 })

// Pre-save middleware for updated_at
userSchema.pre('save', function (next) {
  this.updated_at = new Date()
  next()
})

export const User = mongoose.model('User', userSchema)
