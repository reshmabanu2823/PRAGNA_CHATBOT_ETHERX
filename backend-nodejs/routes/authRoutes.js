import express from 'express'
import * as authController from '../controllers/authController.js'
import { authenticate } from '../middleware/auth.js'
import Joi from 'joi'

const router = express.Router()

// Validation schemas
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

const registerSchema = Joi.object({
  name: Joi.string().required().min(1).max(50),
  email: Joi.string().email().required(),
  password: Joi.string().required().min(6).max(100),
  avatar_url: Joi.string().uri().allow(''),
})

const loginSchema = Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().required(),
})

const updateProfileSchema = Joi.object({
  name: Joi.string().min(1).max(50),
  avatar_url: Joi.string().uri().allow(''),
  phone: Joi.string().allow(''),
})

const changePasswordSchema = Joi.object({
  currentPassword: Joi.string().required(),
  newPassword: Joi.string().required().min(6),
})

// Public routes
router.post('/register', validateRequest(registerSchema), authController.register)
router.post('/login', validateRequest(loginSchema), authController.login)

// Protected routes
router.get('/user', authenticate, authController.getCurrentUser)
router.put('/profile', authenticate, validateRequest(updateProfileSchema), authController.updateProfile)
router.post('/change-password', authenticate, validateRequest(changePasswordSchema), authController.changePassword)
router.post('/logout', authenticate, authController.logout)
router.put('/status', authenticate, authController.updateUserStatus)

// User lookup
router.get('/users/:userId', authenticate, authController.getUserById)
router.get('/search', authenticate, authController.searchUsers)

export default router
