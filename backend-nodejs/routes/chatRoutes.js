import express from 'express'
import * as chatController from '../controllers/chatController.js'
import { authenticate } from '../middleware/auth.js'
import { validateChat, validateChatUpdate } from '../middleware/validation.js'

const router = express.Router()

// All routes require authentication
router.use(authenticate)

// Chat CRUD operations
router.post('/', validateChat, chatController.createChat)
router.get('/', chatController.getUserChats)
router.get('/:chatId', chatController.getChatById)
router.put('/:chatId', validateChatUpdate, chatController.renameChat)
router.delete('/:chatId', chatController.deleteChat)

// Chat-specific operations
router.put('/:chatId/pin', chatController.togglePinChat)
router.put('/:chatId/archive', chatController.toggleArchiveChat)
router.post('/:chatId/restore', chatController.restoreChat)

// Sharing
router.post('/:chatId/share', chatController.shareChat)
router.get('/share/:shareToken', chatController.getSharedChat)
router.delete('/:chatId/share', chatController.revokeShareLink)

// Participants management
router.post('/:chatId/add-user', chatController.addUserToChat)
router.delete('/:chatId/remove-user', chatController.removeUserFromChat)

export default router
