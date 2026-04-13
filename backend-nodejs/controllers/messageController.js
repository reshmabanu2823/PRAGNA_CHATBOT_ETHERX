import { Message } from '../models/Message.js'
import { Chat } from '../models/Chat.js'
import mongoose from 'mongoose'
import * as redis from '../utils/redis.js'
import { validateObjectId, handleError } from '../utils/helpers.js'

/**
 * Send message
 */
export const sendMessage = async (req, res) => {
  try {
    const { chatId } = req.params
    const { content, message_type = 'text', reply_to, mentions = [] } = req.body
    const senderId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    if (!content || content.trim().length === 0) {
      return res.status(400).json({ error: 'Message content is required' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    if (!chat.participants.includes(senderId)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    const message = new Message({
      _id: new mongoose.Types.ObjectId(),
      chat_id: chatId,
      sender_id: senderId,
      content: content.trim(),
      message_type,
      reply_to: reply_to || undefined,
      mentions: mentions.map((id) => ({
        user_id: id,
        mentioned_at: new Date(),
      })),
    })

    await message.save()

    // Update chat
    chat.last_message = message._id
    chat.message_count = (chat.message_count || 0) + 1
    chat.updated_at = new Date()
    await chat.save()

    // Reset unread for sender
    chat.updateUserState(senderId, { unread_count: 0, last_read_at: new Date() })
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache([...chat.participants])

    // Populate before returning
    const populated = await Message.findById(message._id).populate('sender_id', 'name email avatar_url')

    res.status(201).json({
      success: true,
      message: populated,
    })
  } catch (error) {
    handleError(res, error, 'Failed to send message')
  }
}

/**
 * Get messages in chat
 */
export const getMessages = async (req, res) => {
  try {
    const { chatId } = req.params
    const { page = 1, limit = 50 } = req.query
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const pageNum = Math.max(1, parseInt(page))
    const limitNum = Math.min(100, Math.max(1, parseInt(limit)))
    const skip = (pageNum - 1) * limitNum

    // Check chat access
    const chat = await Chat.findById(chatId)
    if (!chat || !chat.participants.includes(userId)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    // Get messages
    const messages = await Message.find({
      chat_id: chatId,
      is_deleted: false,
    })
      .populate('sender_id', 'name email avatar_url')
      .populate('reply_to')
      .sort({ created_at: -1 })
      .skip(skip)
      .limit(limitNum)
      .lean()

    const total = await Message.countDocuments({
      chat_id: chatId,
      is_deleted: false,
    })

    res.json({
      success: true,
      messages: messages.reverse(),
      pagination: {
        page: pageNum,
        limit: limitNum,
        total,
        pages: Math.ceil(total / limitNum),
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to fetch messages')
  }
}

/**
 * Search messages
 */
export const searchMessages = async (req, res) => {
  try {
    const { chatId } = req.params
    const { query = '', page = 1, limit = 20 } = req.query
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    if (!query || query.trim().length === 0) {
      return res.status(400).json({ error: 'Search query is required' })
    }

    // Check chat access
    const chat = await Chat.findById(chatId)
    if (!chat || !chat.participants.includes(userId)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    const pageNum = Math.max(1, parseInt(page))
    const limitNum = Math.min(100, Math.max(1, parseInt(limit)))
    const skip = (pageNum - 1) * limitNum

    const messages = await Message.find(
      { $text: { $search: query }, chat_id: chatId, is_deleted: false },
      { score: { $meta: 'textScore' } }
    )
      .populate('sender_id', 'name email avatar_url')
      .sort({ score: { $meta: 'textScore' } })
      .skip(skip)
      .limit(limitNum)

    const total = await Message.countDocuments({
      $text: { $search: query },
      chat_id: chatId,
      is_deleted: false,
    })

    res.json({
      success: true,
      messages,
      pagination: {
        page: pageNum,
        limit: limitNum,
        total,
        pages: Math.ceil(total / limitNum),
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to search messages')
  }
}

/**
 * Edit message
 */
export const editMessage = async (req, res) => {
  try {
    const { messageId } = req.params
    const { content } = req.body
    const userId = req.user._id

    if (!validateObjectId(messageId)) {
      return res.status(400).json({ error: 'Invalid message ID' })
    }

    if (!content || content.trim().length === 0) {
      return res.status(400).json({ error: 'Content is required' })
    }

    const message = await Message.findById(messageId)

    if (!message) {
      return res.status(404).json({ error: 'Message not found' })
    }

    if (message.sender_id.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Can only edit own messages' })
    }

    if (message.is_deleted) {
      return res.status(410).json({ error: 'Message is deleted' })
    }

    message.content = content.trim()
    message.edited_at = new Date()
    message.edited_by = userId
    await message.save()

    // Cache invalidation
    const populated = await Message.findById(message._id).populate('sender_id', 'name email avatar_url')

    res.json({
      success: true,
      message: populated,
    })
  } catch (error) {
    handleError(res, error, 'Failed to edit message')
  }
}

/**
 * Delete message (soft delete)
 */
export const deleteMessage = async (req, res) => {
  try {
    const { messageId } = req.params
    const userId = req.user._id

    if (!validateObjectId(messageId)) {
      return res.status(400).json({ error: 'Invalid message ID' })
    }

    const message = await Message.findById(messageId)

    if (!message) {
      return res.status(404).json({ error: 'Message not found' })
    }

    if (message.sender_id.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Can only delete own messages' })
    }

    await message.softDelete()

    res.json({
      success: true,
      message: 'Message deleted',
    })
  } catch (error) {
    handleError(res, error, 'Failed to delete message')
  }
}

/**
 * React to message
 */
export const addReaction = async (req, res) => {
  try {
    const { messageId } = req.params
    const { emoji } = req.body
    const userId = req.user._id

    if (!validateObjectId(messageId)) {
      return res.status(400).json({ error: 'Invalid message ID' })
    }

    if (!emoji) {
      return res.status(400).json({ error: 'Emoji is required' })
    }

    const message = await Message.findById(messageId)

    if (!message) {
      return res.status(404).json({ error: 'Message not found' })
    }

    await message.addReaction(emoji, userId)

    res.json({
      success: true,
      message,
    })
  } catch (error) {
    handleError(res, error, 'Failed to add reaction')
  }
}

/**
 * Remove reaction from message
 */
export const removeReaction = async (req, res) => {
  try {
    const { messageId } = req.params
    const { emoji } = req.body
    const userId = req.user._id

    if (!validateObjectId(messageId)) {
      return res.status(400).json({ error: 'Invalid message ID' })
    }

    if (!emoji) {
      return res.status(400).json({ error: 'Emoji is required' })
    }

    const message = await Message.findById(messageId)

    if (!message) {
      return res.status(404).json({ error: 'Message not found' })
    }

    await message.removeReaction(emoji, userId)

    res.json({
      success: true,
      message,
    })
  } catch (error) {
    handleError(res, error, 'Failed to remove reaction')
  }
}

/**
 * Mark message as read
 */
export const markAsRead = async (req, res) => {
  try {
    const { messageId } = req.params
    const userId = req.user._id

    if (!validateObjectId(messageId)) {
      return res.status(400).json({ error: 'Invalid message ID' })
    }

    const message = await Message.findById(messageId)

    if (!message) {
      return res.status(404).json({ error: 'Message not found' })
    }

    await message.markAsRead(userId)

    res.json({
      success: true,
      message,
    })
  } catch (error) {
    handleError(res, error, 'Failed to mark message as read')
  }
}
