import Joi from 'joi'

const validateRequest = (schema) => {
  return (req, res, next) => {
    const { error, value } = schema.validate(req.body, { abortEarly: false })

    if (error) {
      const messages = error.details.map((err) => err.message).join(', ')
      return res.status(400).json({ error: messages })
    }

    req.body = value
    next()
  }
}

// Chat validation schemas
const chatSchema = Joi.object({
  title: Joi.string().required().min(1).max(100),
  description: Joi.string().allow('').max(500),
  is_group: Joi.boolean().default(false),
  participants: Joi.array().items(Joi.string()).default([]),
  avatar_url: Joi.string().uri().allow(''),
})

const chatUpdateSchema = Joi.object({
  title: Joi.string().min(1).max(100),
  description: Joi.string().allow('').max(500),
  avatar_url: Joi.string().uri().allow(''),
})

// Message validation schemas
const messageSchema = Joi.object({
  content: Joi.string().required().min(1).max(5000),
  message_type: Joi.string().valid('text', 'image', 'file', 'video').default('text'),
  reply_to: Joi.string().allow(''),
  mentions: Joi.array().items(Joi.string()).default([]),
})

// Reaction validation schema
const reactionSchema = Joi.object({
  emoji: Joi.string().required().max(10),
})

// Export middleware functions
export const validateChat = validateRequest(chatSchema)
export const validateChatUpdate = validateRequest(chatUpdateSchema)
export const validateMessage = validateRequest(messageSchema)
export const validateReaction = validateRequest(reactionSchema)

// Generic error validation middleware
export const errorHandler = (err, req, res, next) => {
  console.error('Error:', err)

  if (err.name === 'ValidationError') {
    return res.status(400).json({ error: err.message })
  }

  if (err.name === 'CastError') {
    return res.status(400).json({ error: 'Invalid ID format' })
  }

  if (err.name === 'JsonWebTokenError') {
    return res.status(401).json({ error: 'Invalid token' })
  }

  res.status(500).json({
    error: 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { details: err.message }),
  })
}
