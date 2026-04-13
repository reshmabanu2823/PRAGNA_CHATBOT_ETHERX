import express from 'express'
import * as messageController from '../controllers/messageController.js'
import { authenticate } from '../middleware/auth.js'
import { validateMessage, validateReaction } from '../middleware/validation.js'

const router = express.Router()

// All routes require authentication
router.use(authenticate)

// Message CRUD operations
router.post('/:chatId/messages', validateMessage, messageController.sendMessage)
router.get('/:chatId/messages', messageController.getMessages)
router.put('/:messageId', validateMessage, messageController.editMessage)
router.delete('/:messageId', messageController.deleteMessage)

// Message search
router.get('/:chatId/search', messageController.searchMessages)

// Message reactions
router.post('/:messageId/react', validateReaction, messageController.addReaction)
router.delete('/:messageId/react', validateReaction, messageController.removeReaction)

// Message read status
router.put('/:messageId/read', messageController.markAsRead)

export default router
