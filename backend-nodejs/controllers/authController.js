import bcryptjs from 'bcryptjs'
import jwt from 'jsonwebtoken'
import { User } from '../models/User.js'
import { handleError } from '../utils/helpers.js'
import mongoose from 'mongoose'

/**
 * Register a new user
 */
export const register = async (req, res) => {
  try {
    const { name, email, password, avatar_url } = req.body

    // Validation
    if (!name || !email || !password) {
      return res.status(400).json({ error: 'Name, email, and password are required' })
    }

    // Check if user exists
    const existingUser = await User.findOne({ email: email.toLowerCase() })
    if (existingUser) {
      return res.status(400).json({ error: 'Email already registered' })
    }

    // Hash password
    const hashedPassword = await bcryptjs.hash(password, 10)

    // Create user
    const user = new User({
      _id: new mongoose.Types.ObjectId(),
      name: name.trim(),
      email: email.toLowerCase(),
      password: hashedPassword,
      avatar_url: avatar_url || null,
    })

    await user.save()

    // Generate token
    const token = jwt.sign({ id: user._id }, process.env.JWT_SECRET || 'your-secret-key', {
      expiresIn: process.env.JWT_EXPIRE || '7d',
    })

    res.status(201).json({
      success: true,
      message: 'User registered successfully',
      token,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        avatar_url: user.avatar_url,
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to register user')
  }
}

/**
 * Login user
 */
export const login = async (req, res) => {
  try {
    const { email, password } = req.body

    // Validation
    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required' })
    }

    // Find user
    const user = await User.findOne({ email: email.toLowerCase() }).select('+password')

    if (!user) {
      return res.status(401).json({ error: 'Invalid email or password' })
    }

    // Check password
    const isPasswordValid = await bcryptjs.compare(password, user.password)

    if (!isPasswordValid) {
      return res.status(401).json({ error: 'Invalid email or password' })
    }

    // Update last seen
    user.last_seen = new Date()
    await user.save()

    // Generate token
    const token = jwt.sign({ id: user._id }, process.env.JWT_SECRET || 'your-secret-key', {
      expiresIn: process.env.JWT_EXPIRE || '7d',
    })

    res.json({
      success: true,
      message: 'Login successful',
      token,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        avatar_url: user.avatar_url,
        is_active: user.is_active,
        last_seen: user.last_seen,
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to login')
  }
}

/**
 * Get current user profile
 */
export const getCurrentUser = async (req, res) => {
  try {
    const user = await User.findById(req.user._id)

    if (!user) {
      return res.status(404).json({ error: 'User not found' })
    }

    res.json({
      success: true,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        avatar_url: user.avatar_url,
        phone: user.phone,
        is_active: user.is_active,
        last_seen: user.last_seen,
        created_at: user.created_at,
        updated_at: user.updated_at,
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to fetch user')
  }
}

/**
 * Update user profile
 */
export const updateProfile = async (req, res) => {
  try {
    const { name, avatar_url, phone } = req.body
    const userId = req.user._id

    const updates = {}
    if (name) updates.name = name.trim()
    if (avatar_url !== undefined) updates.avatar_url = avatar_url
    if (phone !== undefined) updates.phone = phone

    const user = await User.findByIdAndUpdate(userId, updates, { new: true })

    res.json({
      success: true,
      message: 'Profile updated successfully',
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        avatar_url: user.avatar_url,
        phone: user.phone,
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to update profile')
  }
}

/**
 * Change password
 */
export const changePassword = async (req, res) => {
  try {
    const { currentPassword, newPassword } = req.body
    const userId = req.user._id

    if (!currentPassword || !newPassword) {
      return res.status(400).json({ error: 'Current password and new password are required' })
    }

    if (currentPassword === newPassword) {
      return res
        .status(400)
        .json({ error: 'New password must be different from current password' })
    }

    // Get user with password
    const user = await User.findById(userId).select('+password')

    if (!user) {
      return res.status(404).json({ error: 'User not found' })
    }

    // Verify current password
    const isPasswordValid = await bcryptjs.compare(currentPassword, user.password)

    if (!isPasswordValid) {
      return res.status(401).json({ error: 'Current password is incorrect' })
    }

    // Hash new password
    user.password = await bcryptjs.hash(newPassword, 10)
    await user.save()

    res.json({
      success: true,
      message: 'Password changed successfully',
    })
  } catch (error) {
    handleError(res, error, 'Failed to change password')
  }
}

/**
 * Get user by ID
 */
export const getUserById = async (req, res) => {
  try {
    const { userId } = req.params

    const user = await User.findById(userId)

    if (!user) {
      return res.status(404).json({ error: 'User not found' })
    }

    res.json({
      success: true,
      user: {
        id: user._id,
        name: user.name,
        avatar_url: user.avatar_url,
        is_active: user.is_active,
        last_seen: user.last_seen,
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to fetch user')
  }
}

/**
 * Search users
 */
export const searchUsers = async (req, res) => {
  try {
    const { query = '', limit = 10 } = req.query
    const limitNum = Math.min(50, Math.max(1, parseInt(limit)))

    if (!query || query.trim().length === 0) {
      return res.status(400).json({ error: 'Search query is required' })
    }

    const users = await User.find(
      {
        $or: [
          { name: { $regex: query, $options: 'i' } },
          { email: { $regex: query, $options: 'i' } },
        ],
      },
      'name email avatar_url is_active last_seen'
    )
      .limit(limitNum)
      .lean()

    res.json({
      success: true,
      users,
      total: users.length,
    })
  } catch (error) {
    handleError(res, error, 'Failed to search users')
  }
}

/**
 * Update user status
 */
export const updateUserStatus = async (req, res) => {
  try {
    const { is_active } = req.body
    const userId = req.user._id

    const user = await User.findByIdAndUpdate(
      userId,
      { is_active, last_seen: new Date() },
      { new: true }
    )

    res.json({
      success: true,
      user: {
        id: user._id,
        is_active: user.is_active,
        last_seen: user.last_seen,
      },
    })
  } catch (error) {
    handleError(res, error, 'Failed to update status')
  }
}

/**
 * Logout user (optional - mainly for client-side)
 */
export const logout = async (req, res) => {
  try {
    // Update last seen
    await User.findByIdAndUpdate(req.user._id, { last_seen: new Date(), is_active: false })

    res.json({
      success: true,
      message: 'Logout successful',
    })
  } catch (error) {
    handleError(res, error, 'Failed to logout')
  }
}
