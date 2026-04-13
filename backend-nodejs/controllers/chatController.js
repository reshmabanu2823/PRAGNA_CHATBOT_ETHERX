import { v4 as uuidv4 } from 'uuid'
import { Chat } from '../models/Chat.js'
import { Message } from '../models/Message.js'
import { ActivityLog } from '../models/ActivityLog.js'
import { User } from '../models/User.js'
import mongoose from 'mongoose'
import * as redis from '../utils/redis.js'
import { validateObjectId, handleError } from '../utils/helpers.js'

/**
 * Create a new chat
 */
export const createChat = async (req, res) => {
  try {
    const { title, description, is_group, participants, avatar_url } = req.body
    const userId = req.user._id

    // Validation
    if (!title || title.trim().length === 0) {
      return res.status(400).json({ error: 'Chat title is required' })
    }

    if (is_group && (!participants || participants.length === 0)) {
      return res.status(400).json({ error: 'Group chat requires participants' })
    }

    // Ensure user is in participants
    const allParticipants = is_group ? [...new Set([userId, ...participants])] : [userId]

    // Validate all participants exist
    const users = await User.find({ _id: { $in: allParticipants } })
    if (users.length !== allParticipants.length) {
      return res.status(400).json({ error: 'One or more participants not found' })
    }

    const chat = new Chat({
      _id: new mongoose.Types.ObjectId(),
      title: title.trim(),
      description,
      is_group,
      participants: allParticipants,
      created_by: userId,
      admin_ids: [userId],
      avatar_url,
      user_states: allParticipants.map((pid) => ({
        user_id: pid,
        is_pinned: false,
        is_archived: false,
      })),
    })

    await chat.save()

    // Cache invalidation
    await redis.invalidateUserChatsCache(userId)

    // Activity log
    await logActivity(chat._id, userId, 'chat_created', null, {
      title,
      is_group,
      participants_count: allParticipants.length,
    })

    res.status(201).json({
      success: true,
      chat: formatChat(chat, userId),
      message: 'Chat created successfully',
    })
  } catch (error) {
    handleError(res, error, 'Failed to create chat')
  }
}

/**
 * Get all chats for user (with per-user filtering)
 */
export const getUserChats = async (req, res) => {
  try {
    const userId = req.user._id
    const { page = 1, limit = 20, search = '', is_archived = null } = req.query

    // Check cache first
    const cacheKey = `user_chats:${userId}:${page}:${limit}:${search}:${is_archived}`
    const cached = await redis.get(cacheKey)
    if (cached) {
      return res.json(JSON.parse(cached))
    }

    const pageNum = Math.max(1, parseInt(page))
    const limitNum = Math.min(100, Math.max(1, parseInt(limit)))
    const skip = (pageNum - 1) * limitNum

    // Build query
    let query = {
      participants: userId,
      is_deleted: false,
      'user_states.user_id': userId,
    }

    if (search) {
      query.$text = { $search: search }
    }

    // Filter by archive status per user
    const userStatesMatch = {
      $elemMatch: {
        user_id: userId,
      },
    }

    if (is_archived !== null) {
      userStatesMatch.$elemMatch.is_archived = is_archived === 'true'
    }

    query.user_states = userStatesMatch

    // Get chats
    const chats = await Chat.find(query)
      .populate('participants', 'name email avatar_url')
      .populate('created_by', 'name email')
      .populate('last_message')
      .sort({ updated_at: -1 })
      .skip(skip)
      .limit(limitNum)
      .lean()

    const total = await Chat.countDocuments(query)

    const formattedChats = chats.map((chat) => formatChat(chat, userId))

    const response = {
      success: true,
      chats: formattedChats,
      pagination: {
        page: pageNum,
        limit: limitNum,
        total,
        pages: Math.ceil(total / limitNum),
      },
    }

    // Cache for 5 minutes
    await redis.set(cacheKey, JSON.stringify(response), 300)

    res.json(response)
  } catch (error) {
    handleError(res, error, 'Failed to fetch chats')
  }
}

/**
 * Get single chat by ID
 */
export const getChatById = async (req, res) => {
  try {
    const { chatId } = req.params
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    // Check cache
    const cached = await redis.get(`chat:${chatId}`)
    if (cached) {
      const chat = JSON.parse(cached)
      if (!chat.participants.includes(userId.toString())) {
        return res.status(403).json({ error: 'Access denied' })
      }
      return res.json({ success: true, chat })
    }

    const chat = await Chat.findById(chatId)
      .populate('participants', 'name email avatar_url')
      .populate('created_by', 'name email')
      .populate('admin_ids', 'name email')

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    // Check if user is participant
    if (!chat.participants.some((p) => p._id.toString() === userId.toString())) {
      return res.status(403).json({ error: 'Access denied' })
    }

    // Cache for 10 minutes
    await redis.set(`chat:${chatId}`, JSON.stringify(chat), 600)

    res.json({
      success: true,
      chat: formatChat(chat, userId),
    })
  } catch (error) {
    handleError(res, error, 'Failed to fetch chat')
  }
}

/**
 * Rename chat
 */
export const renameChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const { title } = req.body
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    if (!title || title.trim().length === 0) {
      return res.status(400).json({ error: 'Title is required' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    // Check permissions (creator or admin)
    if (!chat.admin_ids.includes(userId) && chat.created_by.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Only admins can rename chat' })
    }

    const oldTitle = chat.title
    chat.title = title.trim()
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(chat.participants)

    // Activity log
    await logActivity(chatId, userId, 'chat_renamed', oldTitle, title)

    res.json({
      success: true,
      chat: formatChat(chat, userId),
      message: 'Chat renamed successfully',
    })
  } catch (error) {
    handleError(res, error, 'Failed to rename chat')
  }
}

/**
 * Pin/Unpin chat (per user)
 */
export const togglePinChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    if (!chat.participants.includes(userId)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    const userState = chat.getUserState(userId)
    const wasPinned = userState?.is_pinned || false
    chat.updateUserState(userId, { is_pinned: !wasPinned })
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(userId)

    // Activity log
    await logActivity(
      chatId,
      userId,
      wasPinned ? 'chat_unpinned' : 'chat_pinned',
      wasPinned,
      !wasPinned
    )

    res.json({
      success: true,
      chat: formatChat(chat, userId),
      message: wasPinned ? 'Chat unpinned' : 'Chat pinned',
    })
  } catch (error) {
    handleError(res, error, 'Failed to toggle pin')
  }
}

/**
 * Archive/Unarchive chat (per user)
 */
export const toggleArchiveChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    if (!chat.participants.includes(userId)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    const userState = chat.getUserState(userId)
    const wasArchived = userState?.is_archived || false
    chat.updateUserState(userId, { is_archived: !wasArchived })
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(userId)

    // Activity log
    await logActivity(
      chatId,
      userId,
      wasArchived ? 'chat_unarchived' : 'chat_archived',
      wasArchived,
      !wasArchived
    )

    res.json({
      success: true,
      chat: formatChat(chat, userId),
      message: wasArchived ? 'Chat unarchived' : 'Chat archived',
    })
  } catch (error) {
    handleError(res, error, 'Failed to toggle archive')
  }
}

/**
 * Share chat (generate shareable link)
 */
export const shareChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const { expiryDays } = req.body
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    // Check permissions
    if (!chat.admin_ids.includes(userId) && chat.created_by.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Only admins can share chat' })
    }

    const shareToken = uuidv4()
    chat.share_token = shareToken
    chat.is_shared = true
    chat.share_token_expires_at = expiryDays
      ? new Date(Date.now() + expiryDays * 24 * 60 * 60 * 1000)
      : null

    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)

    // Activity log
    await logActivity(chatId, userId, 'chat_shared', null, { share_token: shareToken })

    const shareUrl = `${process.env.SERVER_URL}/api/chat/share/${shareToken}`

    res.json({
      success: true,
      share_token: shareToken,
      share_url: shareUrl,
      expires_at: chat.share_token_expires_at,
      message: 'Chat shared successfully',
    })
  } catch (error) {
    handleError(res, error, 'Failed to share chat')
  }
}

/**
 * Get shared chat (read-only access)
 */
export const getSharedChat = async (req, res) => {
  try {
    const { shareToken } = req.params

    const chat = await Chat.findOne({
      share_token: shareToken,
      is_deleted: false,
    })
      .populate('participants', 'name avatar_url')
      .populate('created_by', 'name avatar_url')

    if (!chat) {
      return res.status(404).json({ error: 'Shared chat not found or expired' })
    }

    // Check expiry
    if (chat.share_token_expires_at && new Date() > new Date(chat.share_token_expires_at)) {
      return res.status(410).json({ error: 'Share link has expired' })
    }

    // Increment access count
    chat.share_access_count = (chat.share_access_count || 0) + 1
    await chat.save()

    // Get recent messages (read-only)
    const messages = await Message.find({ chat_id: chat._id, is_deleted: false })
      .populate('sender_id', 'name avatar_url')
      .sort({ created_at: -1 })
      .limit(50)
      .lean()

    res.json({
      success: true,
      chat: formatChatPublic(chat),
      messages: messages.reverse(),
      message: 'Shared chat fetched successfully (read-only)',
    })
  } catch (error) {
    handleError(res, error, 'Failed to fetch shared chat')
  }
}

/**
 * Revoke share link
 */
export const revokeShareLink = async (req, res) => {
  try {
    const { chatId } = req.params
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    // Check permissions
    if (!chat.admin_ids.includes(userId) && chat.created_by.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Only admins can revoke share link' })
    }

    const oldToken = chat.share_token
    chat.share_token = null
    chat.is_shared = false
    chat.share_token_expires_at = null
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)

    // Activity log
    await logActivity(chatId, userId, 'share_link_revoked', oldToken, null)

    res.json({
      success: true,
      message: 'Share link revoked',
    })
  } catch (error) {
    handleError(res, error, 'Failed to revoke share link')
  }
}

/**
 * Add user to group chat
 */
export const addUserToChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const { userId: newUserId } = req.body
    const requesterId = req.user._id

    if (!validateObjectId(chatId) || !validateObjectId(newUserId)) {
      return res.status(400).json({ error: 'Invalid IDs' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    if (!chat.is_group) {
      return res.status(400).json({ error: 'Cannot add users to non-group chat' })
    }

    // Check permissions
    if (!chat.admin_ids.includes(requesterId)) {
      return res.status(403).json({ error: 'Only admins can add users' })
    }

    // Check if user already in chat
    if (chat.participants.includes(newUserId)) {
      return res.status(400).json({ error: 'User already in chat' })
    }

    // Check if user exists
    const user = await User.findById(newUserId)
    if (!user) {
      return res.status(404).json({ error: 'User not found' })
    }

    // Add user
    chat.participants.push(newUserId)
    chat.user_states.push({
      user_id: newUserId,
      is_pinned: false,
      is_archived: false,
    })
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(newUserId)

    // Activity log
    await logActivity(chatId, requesterId, 'user_added', null, newUserId)

    res.json({
      success: true,
      chat: formatChat(chat, requesterId),
      message: 'User added to chat',
    })
  } catch (error) {
    handleError(res, error, 'Failed to add user')
  }
}

/**
 * Remove user from group chat
 */
export const removeUserFromChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const { userId: removeUserId } = req.body
    const requesterId = req.user._id

    if (!validateObjectId(chatId) || !validateObjectId(removeUserId)) {
      return res.status(400).json({ error: 'Invalid IDs' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat || chat.is_deleted) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    if (!chat.is_group) {
      return res.status(400).json({ error: 'Cannot remove users from non-group chat' })
    }

    // Check permissions (admin or removing self)
    if (
      !chat.admin_ids.includes(requesterId) &&
      requesterId.toString() !== removeUserId.toString()
    ) {
      return res.status(403).json({ error: 'Insufficient permissions' })
    }

    // Remove user
    chat.participants = chat.participants.filter((id) => id.toString() !== removeUserId.toString())
    chat.user_states = chat.user_states.filter(
      (state) => state.user_id.toString() !== removeUserId.toString()
    )

    // Remove from admins if applicable
    chat.admin_ids = chat.admin_ids.filter((id) => id.toString() !== removeUserId.toString())

    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(removeUserId)

    // Activity log
    await logActivity(chatId, requesterId, 'user_removed', null, removeUserId)

    res.json({
      success: true,
      chat: formatChat(chat, requesterId),
      message: 'User removed from chat',
    })
  } catch (error) {
    handleError(res, error, 'Failed to remove user')
  }
}

/**
 * Soft delete chat (only marks as deleted)
 */
export const deleteChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    // Check permissions (creator only)
    if (chat.created_by.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Only chat creator can delete' })
    }

    await chat.softDelete(userId)

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(chat.participants)

    // Activity log
    await logActivity(chatId, userId, 'chat_deleted', null, null)

    res.json({
      success: true,
      message: 'Chat deleted successfully',
    })
  } catch (error) {
    handleError(res, error, 'Failed to delete chat')
  }
}

/**
 * Restore soft-deleted chat
 */
export const restoreChat = async (req, res) => {
  try {
    const { chatId } = req.params
    const userId = req.user._id

    if (!validateObjectId(chatId)) {
      return res.status(400).json({ error: 'Invalid chat ID' })
    }

    const chat = await Chat.findById(chatId)

    if (!chat) {
      return res.status(404).json({ error: 'Chat not found' })
    }

    // Check permissions
    if (chat.created_by.toString() !== userId.toString()) {
      return res.status(403).json({ error: 'Only chat creator can restore' })
    }

    if (!chat.is_deleted) {
      return res.status(400).json({ error: 'Chat is not deleted' })
    }

    chat.is_deleted = false
    chat.deleted_at = null
    chat.deleted_by = null
    await chat.save()

    // Cache invalidation
    await redis.del(`chat:${chatId}`)
    await redis.invalidateUserChatsCache(chat.participants)

    // Activity log
    await logActivity(chatId, userId, 'chat_restored', null, null)

    res.json({
      success: true,
      chat: formatChat(chat, userId),
      message: 'Chat restored successfully',
    })
  } catch (error) {
    handleError(res, error, 'Failed to restore chat')
  }
}

// ===== HELPER FUNCTIONS =====

function formatChat(chat, userId) {
  const obj = chat.toObject ? chat.toObject() : chat
  const userState = chat.getUserState ? chat.getUserState(userId) : null

  return {
    id: obj._id,
    title: obj.title,
    description: obj.description,
    is_group: obj.is_group,
    participants: obj.participants,
    created_by: obj.created_by,
    admin_ids: obj.admin_ids,
    is_pinned: userState?.is_pinned || false,
    is_archived: userState?.is_archived || false,
    unread_count: userState?.unread_count || 0,
    last_message: obj.last_message,
    message_count: obj.message_count,
    avatar_url: obj.avatar_url,
    share_token: obj.share_token,
    is_shared: obj.is_shared,
    created_at: obj.created_at,
    updated_at: obj.updated_at,
  }
}

function formatChatPublic(chat) {
  return {
    id: chat._id,
    title: chat.title,
    description: chat.description,
    participants: chat.participants,
    created_by: chat.created_by,
    message_count: chat.message_count,
    avatar_url: chat.avatar_url,
    created_at: chat.created_at,
    updated_at: chat.updated_at,
  }
}

async function logActivity(chatId, actorId, action, oldValue = null, newValue = null) {
  try {
    await ActivityLog.create({
      _id: new mongoose.Types.ObjectId(),
      chat_id: chatId,
      actor_id: actorId,
      action,
      old_value: oldValue,
      new_value: newValue,
    })
  } catch (error) {
    console.error('Failed to log activity:', error)
  }
}
