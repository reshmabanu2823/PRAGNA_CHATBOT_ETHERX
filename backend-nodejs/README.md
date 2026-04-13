# EtherX Chat Backend (Node.js)

A scalable, real-time chat management system built with Express, MongoDB, Socket.IO, and Redis.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
- [Socket.IO Events](#socketio-events)
- [Database Models](#database-models)
- [Caching Strategy](#caching-strategy)
- [Error Handling](#error-handling)
- [Performance Optimizations](#performance-optimizations)
- [Security Features](#security-features)

## ✨ Features

- **Real-time Messaging**: Socket.IO for instant message delivery
- **Group and Direct Chats**: Support for both chat types
- **Message Features**:
  - Text, image, file, and video support
  - Emoji reactions
  - Reply to messages
  - Mention users
  - Edit and delete messages
  - Message search
  - Read receipts
- **Chat Management**:
  - Pin/Archive chats (per user)
  - Soft delete with restore capability
  - Share chat links with expiry
  - Activity logging
- **User Features**:
  - User status tracking
  - Typing indicators
  - Online/offline presence
  - Last seen timestamps
- **Caching**: Redis for performance optimization
- **Rate Limiting**: Prevent abuse and API overload
- **Comprehensive Logging**: Activity tracking and error logging
- **Security**: JWT authentication, CORS, Helmet protection

## 🛠 Tech Stack

- **Runtime**: Node.js 18+
- **Framework**: Express.js 4.x
- **Database**: MongoDB 4.4+
- **Real-time**: Socket.IO 4.x
- **Cache**: Redis 6.x
- **Authentication**: JWT (jsonwebtoken)
- **Validation**: Joi
- **Security**: Helmet, CORS, bcryptjs
- **Logging**: Morgan
- **Rate Limiting**: express-rate-limit
- **Compression**: gzip

## 📁 Project Structure

```
backend-nodejs/
├── controllers/
│   ├── chatController.js        # Chat operations
│   └── messageController.js     # Message operations
├── models/
│   ├── Chat.js                  # Chat schema
│   ├── Message.js               # Message schema
│   ├── User.js                  # User schema
│   └── ActivityLog.js           # Activity logging
├── routes/
│   ├── chatRoutes.js            # Chat API routes
│   └── messageRoutes.js         # Message API routes
├── middleware/
│   ├── auth.js                  # JWT authentication
│   └── validation.js            # Request validation
├── utils/
│   ├── database.js              # MongoDB connection
│   ├── redis.js                 # Redis client & utilities
│   └── helpers.js               # Utility functions
├── server.js                    # Main server file
├── package.json                 # Dependencies
├── .env.example                 # Environment template
└── README.md                    # This file
```

## 🚀 Installation

### Prerequisites

- Node.js 18+ or higher
- MongoDB 4.4+
- Redis 6.0+
- npm or yarn

### Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend-nodejs
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Create `.env` file**
   ```bash
   cp .env.example .env
   ```

4. **Configure environment variables** (see Configuration section)

5. **Verify MongoDB is running**
   ```bash
   # MongoDB should be running on localhost:27017
   # or use your MONGODB_URI
   ```

6. **Verify Redis is running**
   ```bash
   # Redis should be running on localhost:6379
   # or use your REDIS_HOST and REDIS_PORT
   ```

## ⚙️ Configuration

Edit `.env` file with your settings:

```env
# Server
NODE_ENV=development
PORT=5000
CLIENT_URL=http://localhost:3000
SERVER_URL=http://localhost:5000

# Database
MONGODB_URI=mongodb://localhost:27017/etherx-chat

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Authentication
JWT_SECRET=your_super_secret_key_12345
JWT_EXPIRE=7d

# File Upload
MAX_FILE_SIZE=10485760
ALLOWED_FILE_TYPES=image/jpeg,image/png,image/gif,application/pdf

# Logging
LOG_LEVEL=debug
```

## 🏃‍♂️ Running the Server

### Development
```bash
npm run dev
```
Uses `nodemon` for auto-reload on file changes.

### Production
```bash
npm start
```

### Access Points
- **API**: http://localhost:5000
- **Socket.IO**: ws://localhost:5000/chat
- **Health Check**: http://localhost:5000/health

## 📚 API Documentation

### Chat Endpoints

#### Create Chat
```
POST /api/chats
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Chat Name",
  "description": "Optional description",
  "is_group": true,
  "participants": ["user_id_1", "user_id_2"],
  "avatar_url": "https://..."
}

Response: 201
{
  "success": true,
  "chat": { /* Chat object */ },
  "message": "Chat created successfully"
}
```

#### Get User Chats
```
GET /api/chats?page=1&limit=20&search=&is_archived=false
Authorization: Bearer {token}

Response: 200
{
  "success": true,
  "chats": [ /* Array of chats */ ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  }
}
```

#### Get Chat by ID
```
GET /api/chats/{chatId}
Authorization: Bearer {token}

Response: 200
{
  "success": true,
  "chat": { /* Chat object */ }
}
```

#### Update Chat
```
PUT /api/chats/{chatId}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "New Title",
  "description": "New description",
  "avatar_url": "https://..."
}
```

#### Pin/Archive Chat
```
PUT /api/chats/{chatId}/pin
PUT /api/chats/{chatId}/archive
```

#### Add User to Chat
```
POST /api/chats/{chatId}/add-user
Authorization: Bearer {token}

{
  "userId": "user_id"
}
```

#### Share Chat
```
POST /api/chats/{chatId}/share
Authorization: Bearer {token}

{
  "expiryDays": 7
}

Response:
{
  "success": true,
  "share_token": "uuid",
  "share_url": "http://localhost:5000/api/chats/share/{token}",
  "expires_at": "2024-01-15T00:00:00Z"
}
```

### Message Endpoints

#### Send Message
```
POST /api/messages/{chatId}/messages
Authorization: Bearer {token}

{
  "content": "Hello, World!",
  "message_type": "text",
  "reply_to": "message_id",
  "mentions": ["user_id"]
}

Response: 201
{
  "success": true,
  "message": { /* Message object */ }
}
```

#### Get Messages
```
GET /api/messages/{chatId}/messages?page=1&limit=50
Authorization: Bearer {token}

Response: 200
{
  "success": true,
  "messages": [ /* Array of messages */ ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 250,
    "pages": 5
  }
}
```

#### Search Messages
```
GET /api/messages/{chatId}/search?query=hello&page=1&limit=20
Authorization: Bearer {token}

Response: 200
{
  "success": true,
  "messages": [ /* Matching messages */ ],
  "pagination": { /* ... */ }
}
```

#### Edit Message
```
PUT /api/messages/{messageId}
Authorization: Bearer {token}

{
  "content": "Updated message content"
}
```

#### Delete Message
```
DELETE /api/messages/{messageId}
Authorization: Bearer {token}

Response: 200
{
  "success": true,
  "message": "Message deleted"
}
```

#### React to Message
```
POST /api/messages/{messageId}/react
Authorization: Bearer {token}

{
  "emoji": "👍"
}
```

#### Mark as Read
```
PUT /api/messages/{messageId}/read
Authorization: Bearer {token}
```

## 🔌 Socket.IO Events

### Connection
```javascript
socket.on('user_identified', (userId) => {})
socket.on('connect', () => {})
socket.on('disconnect', () => {})
```

### Chat Presence
```javascript
socket.emit('join_chat', chatId)
socket.emit('leave_chat', chatId)
socket.emit('user_online', userId)
socket.emit('user_offline', userId)

// Listen for
socket.on('user_online', (data) => {})
socket.on('user_offline', (data) => {})
```

### Typing Indicators
```javascript
socket.emit('user_typing', { userId, userName })
socket.emit('user_stop_typing', { userId })

socket.on('user_typing', (data) => {})
socket.on('user_stop_typing', (data) => {})
```

### Messages
```javascript
socket.emit('message_sent', messageData)
socket.emit('message_edited', messageData)
socket.emit('message_deleted', messageData)
socket.emit('message_reacted', reactionData)
socket.emit('message_read', readData)

socket.on('message_sent', (data) => {})
socket.on('message_edited', (data) => {})
socket.on('message_deleted', (data) => {})
socket.on('message_reacted', (data) => {})
socket.on('message_read', (data) => {})
```

## 📊 Database Models

### Chat Model
```javascript
{
  _id: ObjectId,
  title: String,
  description: String,
  is_group: Boolean,
  participants: [ObjectId],
  created_by: ObjectId,
  admin_ids: [ObjectId],
  is_deleted: Boolean,
  deleted_at: Date,
  deleted_by: ObjectId,
  user_states: [{
    user_id: ObjectId,
    is_pinned: Boolean,
    is_archived: Boolean,
    is_muted: Boolean,
    unread_count: Number,
    last_read_at: Date
  }],
  last_message: ObjectId,
  message_count: Number,
  avatar_url: String,
  share_token: String,
  share_token_expires_at: Date,
  created_at: Date,
  updated_at: Date
}
```

### Message Model
```javascript
{
  _id: ObjectId,
  chat_id: ObjectId,
  sender_id: ObjectId,
  content: String,
  message_type: String, // 'text', 'image', 'file', 'system', 'voice'
  attachments: [{
    url: String,
    name: String,
    size: Number,
    mime_type: String
  }],
  edited_at: Date,
  edited_by: ObjectId,
  is_deleted: Boolean,
  deleted_at: Date,
  reactions: [{
    emoji: String,
    user_ids: [ObjectId]
  }],
  mentions: [{
    user_id: ObjectId,
    mentioned_at: Date
  }],
  reply_to: ObjectId,
  read_by: [{
    user_id: ObjectId,
    read_at: Date
  }],
  created_at: Date,
  updated_at: Date
}
```

### User Model
```javascript
{
  _id: ObjectId,
  name: String,
  email: String (unique),
  password: String (hashed),
  avatar_url: String,
  phone: String,
  is_active: Boolean,
  last_seen: Date,
  created_at: Date,
  updated_at: Date
}
```

## 🚀 Caching Strategy

### Redis Keys
- `chat:{chatId}` - Cached chat data (10 minutes TTL)
- `user_chats:{userId}:{page}:{limit}:{search}:{archived}` - User's chat list (5 minutes TTL)
- `messages:{chatId}:{page}:{limit}` - Paginated messages (5 minutes TTL)

### Cache Invalidation
- When a chat is updated
- When a message is sent
- When participants change
- When chat is shared/unshared

## 🛡️ Security Features

1. **JWT Authentication**: All protected routes require valid JWT tokens
2. **Password Hashing**: Passwords are hashed with bcryptjs
3. **CORS**: Configured to only accept requests from allowed origins
4. **Helmet**: HTTP security headers
5. **Rate Limiting**: 100 requests per 15 minutes per IP
6. **Input Validation**: Joi schema validation
7. **SQL Injection Protection**: MongoDB with parameterized queries
8. **XSS Protection**: Helmet provides XSS protection
9. **CSRF Protection**: Can be added via middleware if needed

## ⚡ Performance Optimizations

1. **Database Indexes**: 
   - Composite indexes on frequently queried fields
   - Text indexes for full-text search
   
2. **Pagination**: Results are paginated (default 20, max 100)

3. **Redis Caching**: High-frequency data is cached

4. **Compression**: gzip compression for responses

5. **Connection Pooling**: MongoDB connection pool (max 10)

6. **Lean Queries**: Using `.lean()` when projection is not needed

7. **Population**: Strategic use of `.populate()` only when needed

8. **Timestamps**: Indexed for sorting

## 📝 Error Handling

All errors return a structured JSON response:

```json
{
  "error": "Error message",
  "details": "Additional details (development only)"
}
```

Common HTTP Status Codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `410` - Gone (e.g., expired share link)
- `500` - Internal Server Error

## 🔄 API Flow Example

### Sending a Message
1. Client sends POST to `/api/messages/{chatId}/messages`
2. Middleware authenticates the request
3. Validation ensures required fields
4. Controller creates message document
5. Chat's `last_message` and `message_count` updated
6. Redis cache invalidated
7. Socket.IO broadcasts to chat room
8. Response sent to client

### Getting Chats
1. Client sends GET to `/api/chats`
2. Check Redis cache first
3. If not cached, query MongoDB with user filters
4. Populate related documents
5. Cache result for 5 minutes
6. Return paginated results

## 🧪 Testing

```bash
npm test
```

## 📄 License

This project is part of the EtherX ChatBot ecosystem.

## 🤝 Contributing

1. Create a feature branch
2. Make changes and test locally
3. Commit with meaningful messages
4. Push to repository
5. Create Pull Request

## 📞 Support

For issues and questions, please open an issue on the repository.
