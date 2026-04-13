# Backend Architecture & Design Patterns

Comprehensive documentation of the EtherX Chat Backend architecture, design patterns, and implementation details.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Design Patterns](#design-patterns)
3. [Data Models](#data-models)
4. [API Design](#api-design)
5. [Real-time Communication](#real-time-communication)
6. [Caching Strategy](#caching-strategy)
7. [Error Handling](#error-handling)
8. [Performance Optimization](#performance-optimization)
9. [Security Implementation](#security-implementation)

---

## Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Client Layer (Frontend)                │
│              (React/Vue SPA with Socket.IO)              │
└────────────────────────┬────────────────────────────────┘
                         │
           ┌─────────────┴─────────────┐
           │ HTTP/REST API             │  WebSocket/Socket.IO
           │ (Express)                 │  (Real-time Events)
           │                           │
┌────────────────────────────────────────────────────────┐
│              API Gateway Layer                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Middleware (Auth, Validation, Rate Limit, CORS) │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────────────────────────────────────────┐
│           Application Layer (Business Logic)           │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Controllers     │  │ Services        │              │
│  │ - chatCtrl      │  │ - Aggregation   │              │
│  │ - messageCtrl   │  │ - Validation    │              │
│  │ - authCtrl      │  │ - Transformation│              │
│  └─────────────────┘  └─────────────────┘              │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────────────────────────────────────────┐
│              Data Access Layer                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ MongoDB Models & Queries                         │  │
│  │ - Chat, Message, User, ActivityLog              │  │
│  │ - Indexes, Relationships                        │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────────────────┐   ┌─────────────────┐
│    MongoDB        │   │    Redis Cache  │
│  - Data Storage   │   │ - Session State │
│  - Persistence    │   │ - Query Cache   │
└───────────────────┘   └─────────────────┘
```

### Component Interaction

```
Request Flow:
Client → Router → Middleware → Controller → Service → Model → Database
         ↓
       Response ← Cache/Transform ← Database
         ↓
       Socket.IO → Broadcast to Users
```

---

## Design Patterns

### 1. MVC Pattern (Model-View-Controller)

**Models** (`/models`):
- Define data schemas and validation
- Include business logic methods
- Database interactions

```javascript
// Example: Message Model
const messageSchema = new Schema({
  content: String,
  reactions: [{ emoji: String, user_ids: [ObjectId] }]
})

messageSchema.methods.addReaction = (emoji, userId) => {
  // Business logic
}
```

**Views** (Client-side):
- React/Vue components display data
- Triggered by API responses

**Controllers** (`/controllers`):
- Handle HTTP requests
- Validate input
- Call models/services
- Return responses

```javascript
// Example: Chat Controller
const createChat = async (req, res) => {
  // Validate
  // Call model/service
  // Return response
}
```

### 2. Repository Pattern

Abstraction for data access - though we use Mongoose directly, the concept applies:

```javascript
// Data access layer
class ChatRepository {
  async findById(id) {
    return Chat.findById(id)
  }
  
  async findByParticipants(participants) {
    return Chat.find({ participants: { $all: participants } })
  }
}
```

### 3. Strategy Pattern

Different caching strategies:

```javascript
// Redis cache strategy
const getCachedChat = async (chatId) => {
  const cached = await redis.get(`chat:${chatId}`)
  if (cached) return cached
  
  const fresh = await Chat.findById(chatId)
  await redis.set(`chat:${chatId}`, fresh)
  return fresh
}
```

### 4. Factory Pattern

Creating objects with consistent initialization:

```javascript
function createMessage(data) {
  return new Message({
    _id: new mongoose.Types.ObjectId(),
    chat_id: data.chatId,
    sender_id: data.senderId,
    content: data.content.trim(),
    created_at: new Date()
  })
}
```

### 5. Observer Pattern (via Socket.IO)

Real-time event propagation:

```javascript
// Emit events
socket.emit('message_sent', messageData)

// Listen for events
socket.on('message_sent', (data) => {
  // React to event
})
```

### 6. Middleware Pattern

Layered request processing:

```
Request → Auth Middleware → Validation → Rate Limit → Controller → Response
           ↓                ↓              ↓
          JWT OK?       Schema valid?   Rate ok?
```

---

## Data Models

### Chat Collection Schema

```javascript
{
  _id: ObjectId,
  title: String,
  description: String,
  is_group: Boolean,
  participants: [ObjectId],           // References to User
  created_by: ObjectId,               // Reference to User
  admin_ids: [ObjectId],              // User references
  user_states: [{                     // Per-user settings
    user_id: ObjectId,
    is_pinned: Boolean,
    is_archived: Boolean,
    is_muted: Boolean,
    unread_count: Number,
    last_read_at: Date
  }],
  last_message: ObjectId,             // Reference to Message
  message_count: Number,
  is_deleted: Boolean,
  created_at: Date,
  updated_at: Date
}

// Indexes
participants: 1
created_by: 1
created_at: -1
user_states.user_id: 1
```

### Message Collection Schema

```javascript
{
  _id: ObjectId,
  chat_id: ObjectId,                  // Reference to Chat
  sender_id: ObjectId,                // Reference to User
  content: String,
  message_type: String,               // 'text', 'image', 'file', etc
  reactions: [{                       // Emoji reactions
    emoji: String,
    user_ids: [ObjectId]
  }],
  mentions: [{                        // @mentions
    user_id: ObjectId,
    mentioned_at: Date
  }],
  reply_to: ObjectId,                 // Reference to Message
  read_by: [{                         // Read receipts
    user_id: ObjectId,
    read_at: Date
  }],
  edited_at: Date,
  edited_by: ObjectId,
  is_deleted: Boolean,
  created_at: Date,
  updated_at: Date
}

// Indexes
chat_id: 1, created_at: -1
sender_id: 1
content: text (full-text search)
```

### Relationships

```
User ─┬─→ Chat (created_by)
      ├─→ Chat (participants)
      ├─→ Chat (admin_ids)
      ├─→ Message (sender_id)
      └─→ ActivityLog (actor_id)

Chat ─┬─→ Message (last_message)
      ├─→ User (participants)
      └─→ User (created_by)

Message ─┬─→ Chat (chat_id)
         ├─→ User (sender_id)
         ├─→ Message (reply_to)
         └─→ User (read_by.user_id)
```

---

## API Design

### REST Principles

```
CREATE: POST /api/chats
READ:   GET /api/chats/{id}
UPDATE: PUT /api/chats/{id}
DELETE: DELETE /api/chats/{id}
```

### Naming Conventions

**Resources (Plural Nouns):**
- `/api/chats`
- `/api/messages`
- `/api/users`

**Sub-resources:**
- `/api/chats/{id}/messages`
- `/api/chats/{id}/participants`
- `/api/messages/{id}/reactions`

**Query Parameters:**
- Filtering: `?is_archived=true`
- Pagination: `?page=1&limit=20`
- Sorting: `?sort_by=created_at`
- Search: `?query=keyword`

### Response Format

**Success Response:**
```json
{
  "success": true,
  "data": { /* resource */ },
  "message": "Operation successful",
  "pagination": { /* if applicable */ }
}
```

**Error Response:**
```json
{
  "error": "Error message",
  "details": "Detailed error (dev only)",
  "timestamp": "2024-01-10T10:00:00Z"
}
```

### Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200  | OK | GET /api/chats |
| 201  | Created | POST /api/chats |
| 400  | Bad Request | Invalid input |
| 401  | Unauthorized | Missing token |
| 403  | Forbidden | No permission |
| 404  | Not Found | Chat doesn't exist |
| 409  | Conflict | Resource exists |
| 500  | Server Error | Bug in code |

---

## Real-time Communication

### Socket.IO Architecture

```
Client ←→ Socket.IO ←→ Namespace ←→ Room ←→ Event
         Connection    /chat        chat_123  message_sent
```

### Event Flow

**Sending Message:**
1. Frontend emits `message_sent` event
2. Server receives and saves to DB
3. Server broadcasts to room members
4. All connected clients receive update
5. UI updates in real-time

```javascript
// Client
socket.emit('message_sent', messageData)

// Server
socket.on('message_sent', (data) => {
  // Save to DB
  // Broadcast to room
  socket.to(`chat_${data.chatId}`).emit('message_sent', data)
})

// Client listening
socket.on('message_sent', (data) => {
  // Update UI
})
```

### Namespaces & Rooms

```javascript
// Namespace for chat features
const chatNamespace = io.of('/chat')

// Rooms for chat groups
socket.join(`chat_${chatId}`)      // All messages for this chat
socket.join(`user_${userId}`)      // Notifications for this user

// Emit to specific room
io.to(`chat_${chatId}`).emit('message_sent', data)

// Broadcast to all except sender
socket.to(`chat_${chatId}`).emit('message_sent', data)
```

### Connection Management

```javascript
// Track user-socket associations
const userSockets = new Map()

socket.on('user_identified', (userId) => {
  userSockets.set(userId, socket.id)
  socket.join(`user_${userId}`)
})

// Presence updates
socket.on('user_online', (userId) => {
  io.emit('user_online', { userId, socketId: socket.id })
})
```

---

## Caching Strategy

### Cache Hierarchy

```
Request
  ↓
Redis (Fast)
  ↓ (Miss)
MongoDB (Authoritative)
  ↓
Update Redis (Async)
  ↓
Response
```

### Cache Keys

```
chat:{chatId}                                    → Chat detail
user_chats:{userId}:{page}:{limit}:{filters}   → User's chat list
messages:{chatId}:{page}:{limit}               → Paginated messages
user:{userId}                                   → User profile
```

### TTL (Time To Live)

```javascript
CACHE_TTL = {
  CHAT: 600,           // 10 minutes
  USER_CHATS: 300,     // 5 minutes  
  MESSAGES: 300,       // 5 minutes
  USER: 3600           // 1 hour
}
```

### Cache Invalidation

```javascript
// On new message
await redis.del(`user_chats:${senderId}:*`)
await redis.del(`messages:${chatId}:*`)

// On chat update
await redis.del(`chat:${chatId}`)
await redis.invalidateUserChatsCache(chat.participants)

// On user update
await redis.del(`user:${userId}`)
```

---

## Error Handling

### Error Hierarchy

```
ValidationError
├─ Schema validation failed
├─ Missing required fields
└─ Invalid data format

AuthenticationError
├─ Invalid token
├─ Token expired
└─ No credentials

AuthorizationError
├─ Insufficient permissions
└─ Resource access denied

DatabaseError
├─ Connection failed
├─ Query error
└─ Duplicate key

ConcurrencyError
├─ Race condition
└─ Conflict
```

### Error Recovery

```javascript
// Graceful degradation
try {
  const cached = await redis.get(key)
  if (cached) return cached
} catch (error) {
  // Continue without cache
}

const fresh = await db.find(query)
return fresh
```

### Logging

```javascript
// Error levels
console.log()    // Info
console.warn()   // Warning
console.error()  // Error
console.debug()  // Debug

// Format
${timestamp} [${level}] ${service}: ${message}
2024-01-10 10:00:00 [ERROR] ChatService: Failed to create chat
```

---

## Performance Optimization

### Database Optimization

**Indexing Strategy:**
```javascript
// Frequently queried fields
db.chats.createIndex({ participants: 1 })
db.chats.createIndex({ created_by: 1 })
db.messages.createIndex({ chat_id: 1, created_at: -1 })

// Full-text search
db.chats.createIndex({ title: 'text', description: 'text' })
db.messages.createIndex({ content: 'text' })

// Unique indexes
db.users.createIndex({ email: 1 }, { unique: true })
```

**Query Optimization:**
```javascript
// Use projection to select only needed fields
Chat.find(query, 'title participants created_at')

// Use .lean() for read-only operations
Message.find(query).lean()

// Use pagination to limit results
.skip((page - 1) * limit).limit(limit)

// Avoid N+1 queries with populate
Chat.find().populate('participants', 'name avatar_url')
```

### Application Optimization

**Connection Pooling:**
```javascript
// MongoDB pool size
maxPoolSize: 10
minPoolSize: 5

// Redis connection reuse
```

**Compression:**
```javascript
app.use(compression())  // gzip compression
```

**Rate Limiting:**
```javascript
100 requests per 15 minutes per IP
```

**Caching Strategy:**
```javascript
- Redis for session data
- HTTP caching headers
- Client-side caching
```

---

## Security Implementation

### Authentication Flow

```
User Credentials
       ↓
Verify Password (bcryptjs)
       ↓
Generate JWT Token
       ↓
Return Token to Client
       ↓
Client stores & includes in requests
       ↓
Middleware verifies JWT
       ↓
Request continues if valid
```

### JWT Implementation

```javascript
// Generate token
const token = jwt.sign(
  { id: user._id },
  process.env.JWT_SECRET,
  { expiresIn: '7d' }
)

// Verify token
const decoded = jwt.verify(token, process.env.JWT_SECRET)
```

### Authorization Model

```javascript
// Role-based
if (user.role !== 'admin') return 403

// Resource-based
if (!chat.participants.includes(userId)) return 403

// Attribute-based
if (message.sender_id !== userId && !chat.admin_ids.includes(userId)) return 403
```

### Security Headers

```javascript
// Helmet middleware provides:
Strict-Transport-Security
X-Content-Type-Options
X-Frame-Options
X-XSS-Protection
Content-Security-Policy
```

### Password Security

```javascript
// Bcryptjs hashing with salt rounds
const hashed = await bcryptjs.hash(password, 10)

// Verification
const valid = await bcryptjs.compare(password, hashed)

// Minimum requirements
- 6 characters minimum
- No plaintext storage
- Hash on every password field
```

---

## Scaling Considerations

### Horizontal Scaling

```
Load Balancer (Nginx)
    ↓
┌───┴────────────────┬──────────────┐
│    │               │              │
Backend-1        Backend-2    Backend-3

Shared Resources:
├─ MongoDB (Single cluster)
├─ Redis (Cluster mode)
└─ Session store (Redis)
```

### Database Sharding

```javascript
// Shard by userId for better distribution
shard_key: userId

// Collections sharded:
- Messages (by chat_id → userId)
- ActivityLog (by actor_id)
```

### Caching at Scale

```
Distributed Cache (Redis Cluster)
- Replication for failover
- Cluster mode for horizontal scaling
- Consistent hashing for key distribution
```

---

## Future Enhancements

1. **GraphQL API** - Alternative to REST
2. **Microservices** - Separate services for auth, chat, notifications
3. **Message Queue** - Kafka/RabbitMQ for async processing
4. **Database Sharding** - Horizontal database scaling
5. **CDN Integration** - For file/image serving
6. **Full-text Search** - Elasticsearch for advanced search
7. **Analytics** - Event tracking and dashboards
8. **Encryption** - End-to-end message encryption

---

## References

- [Express.js Documentation](https://expressjs.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Socket.IO Documentation](https://socket.io/docs/)
- [REST API Best Practices](https://restfulapi.net/)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)
