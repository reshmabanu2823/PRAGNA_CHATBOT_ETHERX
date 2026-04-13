import mongoose from 'mongoose'

export const validateObjectId = (id) => {
  return mongoose.Types.ObjectId.isValid(id)
}

export const handleError = (res, error, message) => {
  console.error(`${message}:`, error)

  if (error.name === 'ValidationError') {
    const errors = Object.values(error.errors).map((e) => e.message)
    return res.status(400).json({ error: errors.join(', ') })
  }

  if (error.name === 'CastError') {
    return res.status(400).json({ error: 'Invalid ID format' })
  }

  if (error.code === 11000) {
    const field = Object.keys(error.keyValue)[0]
    return res.status(400).json({ error: `${field} already exists` })
  }

  return res.status(500).json({
    error: message,
    details: process.env.NODE_ENV === 'development' ? error.message : undefined,
  })
}

export const generatePagination = (page, limit, total) => {
  const pageNum = Math.max(1, parseInt(page) || 1)
  const limitNum = Math.min(100, Math.max(1, parseInt(limit) || 20))
  const skip = (pageNum - 1) * limitNum

  return {
    page: pageNum,
    limit: limitNum,
    skip,
    total,
    pages: Math.ceil(total / limitNum),
  }
}

export const formatResponse = (success, data, message, pagination = null) => {
  const response = { success, ...data }

  if (message) response.message = message
  if (pagination) response.pagination = pagination

  return response
}

export const asyncHandler = (fn) => {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next)
  }
}
