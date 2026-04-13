import express from 'express'
import http from 'http'
import { Server as SocketIOServer } from 'socket.io'
import cors from 'cors'
import helmet from 'helmet'
import morgan from 'morgan'
import compression from 'compression'
import rateLimit from 'express-rate-limit'
import dotenv from 'dotenv'

import connectDB from './utils/database.js'
import * as redis from './utils/redis.js'
import { errorHandler } from './middleware/validation.js'
import authRoutes from './routes/authRoutes.js'
import chatRoutes from './routes/chatRoutes.js'
import messageRoutes from './routes/messageRoutes.js'

dotenv.config()

const app = express()
const server = http.createServer(app)
const io = new SocketIOServer(server, {
  cors: {
    origin: process.env.CLIENT_URL || 'http://localhost:3000',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    credentials: true,
  },
})

// Middleware
app.use(helmet())
app.use(compression())
app.use(morgan('dev'))
app.use(cors({
  origin: process.env.CLIENT_URL || 'http://localhost:3000',
  credentials: true,
}))

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests, please try again later',
})

app.use(limiter)

// Body parsing
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ limit: '10mb', extended: true }))

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() })
})

// API Routes
app.use('/api/auth', authRoutes)
app.use('/api/chats', chatRoutes)
app.use('/api/messages', messageRoutes)

// Error handling middleware
app.use(errorHandler)

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' })
})

// Socket.IO namespace for real-time features
const chatNamespace = io.of('/chat')

// Track active connections
const userSockets = new Map()

chatNamespace.on('connection', (socket) => {
  console.log(`🔗 User connected: ${socket.id}`)

  // Store user socket association
  socket.on('user_identified', (userId) => {
    userSockets.set(userId, socket.id)
    socket.join(`user_${userId}`)
    console.log(`👤 User ${userId} associated with socket ${socket.id}`)
  })

  // Join chat room
  socket.on('join_chat', (chatId) => {
    socket.join(`chat_${chatId}`)
    console.log(`📌 Socket ${socket.id} joined chat ${chatId}`)

    // Notify others that user is typing
    socket.on('user_typing', (data) => {
      socket.to(`chat_${chatId}`).emit('user_typing', {
        userId: data.userId,
        userName: data.userName,
      })
    })

    socket.on('user_stop_typing', (data) => {
      socket.to(`chat_${chatId}`).emit('user_stop_typing', {
        userId: data.userId,
      })
    })
  })

  // Leave chat room
  socket.on('leave_chat', (chatId) => {
    socket.leave(`chat_${chatId}`)
    console.log(`🚪 Socket ${socket.id} left chat ${chatId}`)
  })

  // Message events
  socket.on('message_sent', (data) => {
    chatNamespace.to(`chat_${data.chatId}`).emit('message_sent', data)
  })

  socket.on('message_edited', (data) => {
    chatNamespace.to(`chat_${data.chatId}`).emit('message_edited', data)
  })

  socket.on('message_deleted', (data) => {
    chatNamespace.to(`chat_${data.chatId}`).emit('message_deleted', data)
  })

  // Reaction events
  socket.on('message_reacted', (data) => {
    chatNamespace.to(`chat_${data.chatId}`).emit('message_reacted', data)
  })

  // Read receipt events
  socket.on('message_read', (data) => {
    chatNamespace.to(`chat_${data.chatId}`).emit('message_read', data)
  })

  // User presence
  socket.on('user_online', (userId) => {
    chatNamespace.emit('user_online', { userId, socketId: socket.id })
  })

  socket.on('user_offline', (userId) => {
    chatNamespace.emit('user_offline', { userId })
  })

  // Disconnect
  socket.on('disconnect', () => {
    // Remove user socket association
    for (const [userId, socketId] of userSockets.entries()) {
      if (socketId === socket.id) {
        userSockets.delete(userId)
        chatNamespace.emit('user_offline', { userId })
        console.log(`👤 User ${userId} disconnected`)
        break
      }
    }
    console.log(`🔌 User disconnected: ${socket.id}`)
  })

  // Error handling
  socket.on('error', (error) => {
    console.error(`❌ Socket error for ${socket.id}:`, error)
  })
})

// Server startup
const PORT = process.env.PORT || 5000

const startServer = async () => {
  try {
    // Connect to MongoDB
    await connectDB()

    // Connect to Redis
    await redis.connect()

    // Start server
    server.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`)
      console.log(`📡 Socket.IO listening on ws://localhost:${PORT}`)
      console.log(`🔗 Environment: ${process.env.NODE_ENV || 'development'}`)
    })
  } catch (error) {
    console.error('❌ Failed to start server:', error)
    process.exit(1)
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down gracefully...')

  try {
    server.close(() => {
      console.log('✅ Server closed')
    })

    await redis.disconnect()
    console.log('✅ Redis disconnected')

    process.exit(0)
  } catch (error) {
    console.error('❌ Error during shutdown:', error)
    process.exit(1)
  }
})

// Start the server
startServer()

export { app, server, io }
