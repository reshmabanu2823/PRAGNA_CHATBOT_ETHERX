# API Testing Guide

This guide provides examples for testing the EtherX Chat Backend API endpoints.

## Prerequisites

- Backend server running on `http://localhost:5000`
- MongoDB running and connected
- Redis running and connected
- Valid JWT tokens for authenticated endpoints

## Base URL
```
http://localhost:5000/api
```

## Authentication

All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <JWT_TOKEN>
```

## Health Check

### Check API Status
```bash
curl -X GET http://localhost:5000/health
```

Response:
```json
{
  "status": "OK",
  "timestamp": "2024-01-10T10:00:00.000Z"
}
```

---

## Chat Endpoints

### 1. Create Chat

```bash
curl -X POST http://localhost:5000/api/chats \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Tech Discussion",
    "description": "A chat for tech discussions",
    "is_group": true,
    "participants": ["user_id_1", "user_id_2"],
    "avatar_url": "https://example.com/avatar.jpg"
  }'
```

**Response (201):**
```json
{
  "success": true,
  "chat": {
    "id": "chat_id",
    "title": "Tech Discussion",
    "description": "A chat for tech discussions",
    "is_group": true,
    "participants": ["user_id_1", "user_id_2", "current_user_id"],
    "created_by": "current_user_id",
    "created_at": "2024-01-10T10:00:00Z",
    "updated_at": "2024-01-10T10:00:00Z"
  },
  "message": "Chat created successfully"
}
```

### 2. Get User's Chats

```bash
# Get first page
curl -X GET "http://localhost:5000/api/chats?page=1&limit=20" \
  -H "Authorization: Bearer <TOKEN>"

# Get with search
curl -X GET "http://localhost:5000/api/chats?search=tech&is_archived=false" \
  -H "Authorization: Bearer <TOKEN>"
```

**Response (200):**
```json
{
  "success": true,
  "chats": [
    {
      "id": "chat_id",
      "title": "Tech Discussion",
      "is_group": true,
      "participants": ["user_id_1", "user_id_2"],
      "is_pinned": false,
      "is_archived": false,
      "unread_count": 0,
      "created_at": "2024-01-10T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  }
}
```

### 3. Get Chat by ID

```bash
curl -X GET "http://localhost:5000/api/chats/{chatId}" \
  -H "Authorization: Bearer <TOKEN>"
```

### 4. Update Chat

```bash
curl -X PUT "http://localhost:5000/api/chats/{chatId}" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "description": "Updated description"
  }'
```

### 5. Pin Chat

```bash
curl -X PUT "http://localhost:5000/api/chats/{chatId}/pin" \
  -H "Authorization: Bearer <TOKEN>"
```

### 6. Archive Chat

```bash
curl -X PUT "http://localhost:5000/api/chats/{chatId}/archive" \
  -H "Authorization: Bearer <TOKEN>"
```

### 7. Add User to Chat

```bash
curl -X POST "http://localhost:5000/api/chats/{chatId}/add-user" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "new_user_id"
  }'
```

### 8. Remove User from Chat

```bash
curl -X DELETE "http://localhost:5000/api/chats/{chatId}/remove-user" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user_id_to_remove"
  }'
```

### 9. Share Chat

```bash
curl -X POST "http://localhost:5000/api/chats/{chatId}/share" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "expiryDays": 7
  }'
```

**Response:**
```json
{
  "success": true,
  "share_token": "uuid-token",
  "share_url": "http://localhost:5000/api/chats/share/uuid-token",
  "expires_at": "2024-01-17T10:00:00Z",
  "message": "Chat shared successfully"
}
```

### 10. Get Shared Chat (Read-only)

```bash
curl -X GET "http://localhost:5000/api/chats/share/{shareToken}"
```

### 11. Delete Chat

```bash
curl -X DELETE "http://localhost:5000/api/chats/{chatId}" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Message Endpoints

### 1. Send Message

```bash
curl -X POST "http://localhost:5000/api/messages/{chatId}/messages" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, everyone!",
    "message_type": "text",
    "reply_to": "message_id_optional",
    "mentions": ["user_id_1"]
  }'
```

**Response (201):**
```json
{
  "success": true,
  "message": {
    "id": "message_id",
    "chat_id": "chat_id",
    "sender_id": "current_user_id",
    "content": "Hello, everyone!",
    "message_type": "text",
    "reactions": [],
    "read_by": [],
    "created_at": "2024-01-10T10:05:00Z"
  }
}
```

### 2. Get Messages

```bash
# Get first page
curl -X GET "http://localhost:5000/api/messages/{chatId}/messages?page=1&limit=50" \
  -H "Authorization: Bearer <TOKEN>"
```

**Response (200):**
```json
{
  "success": true,
  "messages": [
    {
      "id": "message_id",
      "chat_id": "chat_id",
      "sender_id": "user_id",
      "content": "Hello!",
      "message_type": "text",
      "reactions": [
        {
          "emoji": "👍",
          "user_ids": ["user_id_1", "user_id_2"]
        }
      ],
      "created_at": "2024-01-10T10:05:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 120,
    "pages": 3
  }
}
```

### 3. Search Messages

```bash
curl -X GET "http://localhost:5000/api/messages/{chatId}/search?query=hello&page=1&limit=20" \
  -H "Authorization: Bearer <TOKEN>"
```

### 4. Edit Message

```bash
curl -X PUT "http://localhost:5000/api/messages/{messageId}" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated message content"
  }'
```

### 5. Delete Message

```bash
curl -X DELETE "http://localhost:5000/api/messages/{messageId}" \
  -H "Authorization: Bearer <TOKEN>"
```

### 6. React to Message

```bash
curl -X POST "http://localhost:5000/api/messages/{messageId}/react" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "emoji": "👍"
  }'
```

### 7. Remove Reaction

```bash
curl -X DELETE "http://localhost:5000/api/messages/{messageId}/react" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "emoji": "👍"
  }'
```

### 8. Mark Message as Read

```bash
curl -X PUT "http://localhost:5000/api/messages/{messageId}/read" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request parameters",
  "details": "Content is required"
}
```

### 401 Unauthorized
```json
{
  "error": "No token provided"
}
```

### 403 Forbidden
```json
{
  "error": "Access denied"
}
```

### 404 Not Found
```json
{
  "error": "Chat not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "details": "Error details (development only)"
}
```

---

## Testing with Postman

1. **Create a collection** named "EtherX Chat API"

2. **Add environment variables:**
   - `baseUrl`: `http://localhost:5000/api`
   - `token`: Your JWT token
   - `chatId`: A chat ID for testing
   - `messageId`: A message ID for testing

3. **Use variables in requests:**
   ```
   {{baseUrl}}/chats
   Authorization: Bearer {{token}}
   ```

4. **Test workflows:**
   - Create chat → Send message → Get messages → React to message
   - Pin chat → Archive chat → Get chats
   - Edit message → Delete message

---

## Testing with JavaScript/Node.js

```javascript
const axios = require('axios');

const API_BASE = 'http://localhost:5000/api';
const TOKEN = 'your_jwt_token';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json'
  }
});

// Create chat
async function createChat() {
  try {
    const response = await api.post('/chats', {
      title: 'Test Chat',
      is_group: false,
      participants: ['user_id_1', 'user_id_2']
    });
    console.log('Chat created:', response.data);
    return response.data.chat.id;
  } catch (error) {
    console.error('Error:', error.response?.data);
  }
}

// Send message
async function sendMessage(chatId) {
  try {
    const response = await api.post(`/messages/${chatId}/messages`, {
      content: 'Hello, World!',
      message_type: 'text'
    });
    console.log('Message sent:', response.data);
    return response.data.message.id;
  } catch (error) {
    console.error('Error:', error.response?.data);
  }
}

// Get messages
async function getMessages(chatId) {
  try {
    const response = await api.get(`/messages/${chatId}/messages?page=1&limit=50`);
    console.log('Messages:', response.data);
  } catch (error) {
    console.error('Error:', error.response?.data);
  }
}

// Run tests
(async () => {
  const chatId = await createChat();
  if (chatId) {
    await sendMessage(chatId);
    await getMessages(chatId);
  }
})();
```

---

## Performance Testing

### Load Testing with Apache Bench
```bash
# Get 1000 requests with 10 concurrent connections
ab -n 1000 -c 10 -H "Authorization: Bearer $TOKEN" \
   http://localhost:5000/api/chats
```

### Load Testing with Artillery
```bash
npm install -g artillery

# Create load-test.yml
artillery run load-test.yml
```

---

## Debugging Tips

1. **Check server logs** for any errors
2. **Use browser DevTools** to inspect requests
3. **Test with curl/Postman** before integration
4. **Verify JWT token** validity
5. **Check database connection** with MongoDB Compass
6. **Monitor Redis** with Redis CLI
7. **Enable verbose logging** by setting `LOG_LEVEL=debug`

---

## Common Issues & Solutions

### "Invalid Token"
- Check token expiry
- Verify JWT_SECRET matches
- Include "Bearer" prefix in Authorization header

### "Chat Not Found"
- Verify chatId is correct
- Ensure user is participant
- Check if chat is deleted

### "Too Many Requests"
- Wait 15 minutes or restart server
- Reduce request frequency
- Increase rate limit in `.env` if needed

### Connection Timeout
- Check MongoDB is running
- Check Redis is running
- Verify connection strings in `.env`
