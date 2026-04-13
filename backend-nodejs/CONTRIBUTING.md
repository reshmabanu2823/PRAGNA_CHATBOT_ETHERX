# Contributing to EtherX Chat Backend

Thank you for your interest in contributing! This guide will help you get started.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

- Be respectful and inclusive
- No harassment or discrimination
- Welcome diverse perspectives
- Focus on constructive feedback

## Getting Started

### 1. Fork the Repository

```bash
# Click "Fork" on GitHub
git clone https://github.com/YOUR-USERNAME/EtherXChatBot.git
cd EtherXChatBot
```

### 2. Create a Branch

```bash
# Update main branch first
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# Or bugfix branch
git checkout -b bugfix/issue-description
```

### 3. Setup Development Environment

```bash
cd backend-nodejs
npm install
cp .env.example .env

# Configure .env with local MongoDB/Redis
npm run dev
```

### 4. Make Changes

```bash
# Edit files
# Test locally
# Commit changes
```

## Development Workflow

### File Structure Rules

```
backend-nodejs/
├── controllers/
│   └── [featureName]Controller.js
├── models/
│   └── [EntityName].js
├── routes/
│   └── [featureName]Routes.js
├── middleware/
│   └── [middlewareName].js
├── utils/
│   └── [utilityName].js
└── [feature files...]
```

### Naming Conventions

**Files:**
```javascript
// Controllers
messageController.js
chatController.js

// Models
Message.js
Chat.js

// Routes
messageRoutes.js
chatRoutes.js

// Middleware
auth.js
validation.js

// Utils
redis.js
helpers.js
```

**Variables:**
```javascript
// Constants (UPPER_CASE)
const MAX_MESSAGE_LENGTH = 5000
const CACHE_TTL = 3600

// Classes (PascalCase)
class ChatService {}

// Functions (camelCase)
function getUserChats() {}
const getUserChats = () => {}

// Variables (camelCase)
const userName = "John"
let messageCount = 0
```

**Functions:**
```javascript
// Handlers (async)
export const sendMessage = async (req, res) => {}
export const getMessages = async (req, res) => {}

// Services (business logic)
function formatChatResponse(chat) {}

// Utilities
function validateObjectId(id) {}
```

## Code Standards

### ESLint Rules

```javascript
// Use semicolons
const x = 1;

// Use const/let, never var
const name = 'John';
let counter = 0;

// Avoid console.log in production
// Use proper logging instead

// Proper spacing
const obj = { key: 'value' };
if (condition) {
  // code
}

// Arrow functions for callbacks
array.map((item) => item.value);

// Async/await over promises
const data = await fetchData();
```

### Error Handling

```javascript
// Always handle errors in async functions
try {
  const result = await operation();
  res.json({ success: true, result });
} catch (error) {
  handleError(res, error, 'Operation failed');
}

// Use custom error handler
import { handleError } from '../utils/helpers.js'
```

### Comments & Documentation

```javascript
/**
 * Send message to chat
 * @param {String} chatId - The chat ID
 * @param {String} content - Message content
 * @returns {Promise<Message>} Created message
 */
export const sendMessage = async (req, res) => {
  // Implementation
}

// Explain WHY, not WHAT
// Good:
// Cache result for 5 minutes to reduce DB load during peak hours
const cached = await redis.get(key)

// Bad:
// Get from redis
const cached = await redis.get(key)
```

### Security Practices

```javascript
// ❌ Don't
const user = await User.findById(req.params.id);
res.json(user);  // Sends password hash!

// ✅ Do
const user = await User.findById(req.params.id).select('-password');
res.json(user);

// ❌ Don't
app.get('/api/data', (req, res) => { /* no auth */ })

// ✅ Do
app.get('/api/data', authenticate, (req, res) => { /* ... */ })

// Input validation
const { error, value } = schema.validate(req.body);
if (error) return res.status(400).json({ error: error.message });
```

## Commit Guidelines

### Format

```
<type>: <subject>

<body>

<footer>
```

### Types

```
feat:     New feature
fix:      Bug fix
docs:     Documentation
style:    Code style (formatting, missing semicolons, etc)
refactor: Code refactoring
perf:     Performance improvement
test:     Testing changes
chore:    Build, dependencies, tooling
```

### Examples

```bash
# Feature
git commit -m "feat: add message search functionality"

# Bug fix
git commit -m "fix: resolve socket.io connection timeout issue"

# Documentation
git commit -m "docs: update API endpoints documentation"

# With body
git commit -m "feat: add reaction support to messages

- Add emoji reaction model
- Implement add/remove reaction endpoints
- Emit socket events for real-time updates

Closes #123"
```

### Commit Best Practices

```bash
# Small, focused commits
git commit -m "feat: add handleClick validation"

# NOT
git commit -m "feat: add validation, styling, and docs"

# Frequent commits
git push origin feature/name  # Push at logical checkpoints

# Clear messages
git commit -m "fix: handle null values in user query"  # Good
git commit -m "fix stuff"  # Bad
```

## Pull Request Process

### 1. Before Creating PR

```bash
# Update with latest main branch
git fetch upstream
git rebase upstream/main

# Run tests
npm test

# Lint code
npm run lint  # if available

# Test manually
npm run dev
```

### 2. Create PR

**Title Format:**
```
[TYPE] Brief description (50 chars max)
feat: Add real-time notifications
fix: Resolve chat creation error
docs: Update API documentation
```

**Description Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## Related Issue
Closes #(issue number)

## Testing
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] No new warnings

## Screenshots (if applicable)
<!-- Add images for UI changes -->

## Checklist
- [ ] Code follows style guidelines
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No existing tests broken
- [ ] New tests added
```

### 3. Code Review

- Address review comments promptly
- Ask questions if feedback is unclear
- Update commits based on feedback
- Push changes (don't force push)

### 4. Merge

Once approved:
```bash
# Local merge option
git checkout main
git pull upstream main
git merge feature/name
git push upstream main

# GitHub "Squash and merge" for cleaner history
```

## Testing

### Unit Tests

```bash
# Run all tests
npm test

# Run specific test
npm test -- messageController.test.js

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage
```

### Test Template

```javascript
describe('messageController', () => {
  describe('sendMessage', () => {
    it('should create a new message', async () => {
      const req = {
        params: { chatId: '123' },
        body: { content: 'Hello' },
        user: { _id: 'user123' }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };

      await sendMessage(req, res);

      expect(res.status).toHaveBeenCalledWith(201);
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        message: expect.any(Object)
      });
    });

    it('should reject empty content', async () => {
      const req = {
        params: { chatId: '123' },
        body: { content: '' },
        user: { _id: 'user123' }
      };
      const res = {
        status: jest.fn().mockReturnThis(),
        json: jest.fn()
      };

      await sendMessage(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
    });
  });
});
```

### Manual Testing

```bash
# Start backend
npm run dev

# In another terminal, test with curl
curl -X POST http://localhost:5000/api/messages/chatId/messages \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"content": "test"}'

# Or use Postman/Insomnia
```

## Documentation

### Code Documentation

```javascript
/**
 * Creates a new chat
 * 
 * @async
 * @param {Object} req - Express request object
 * @param {Object} req.body - Request body
 * @param {string} req.body.title - Chat title
 * @param {boolean} req.body.is_group - Is group chat
 * @param {Array} req.body.participants - User IDs
 * @param {Object} res - Express response object
 * 
 * @returns {Promise<void>}
 * 
 * @throws {ValidationError} If input invalid
 * @throws {DatabaseError} If save fails
 * 
 * @example
 * const req = {
 *   body: {
 *     title: 'Team Chat',
 *     is_group: true,
 *     participants: ['user1', 'user2']
 *   },
 *   user: { _id: 'current_user' }
 * };
 * await createChat(req, res);
 */
export const createChat = async (req, res) => {
  // Implementation
}
```

### README Updates

When adding new features, update:

```markdown
## Features
- Add description of new feature

## API Documentation
- Add endpoint examples

## Database Models
- Add new schema if applicable
```

### CHANGELOG Entries

```markdown
## [Version X.Y.Z] - YYYY-MM-DD

### Added
- New real-time notifications
- Message search functionality

### Fixed
- Chat creation race condition
- Socket.IO memory leak

### Changed
- API response format
- Cache TTL strategy

### Removed
- Deprecated endpoints
```

## Performance Considerations

### Before Submitting

```javascript
// ❌ Avoid N+1 queries
users.forEach(user => {
  const chats = await Chat.find({ participants: user._id });
})

// ✅ Use aggregation
const chats = await Chat.aggregate([
  { $match: { participants: userId } }
])

// ❌ Avoid large data transfers
res.json(allMessages);  // Returns all with pagination

// ✅ Always paginate
const messages = await Message.find(query)
  .limit(limit)
  .skip(skip);
```

## Common Issues & Solutions

### "Test Failed"
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm test
```

### "Linting Errors"
```bash
npm run lint -- --fix
```

### "Database Connection Error"
```bash
# Ensure MongoDB is running
sudo systemctl start mongod

# Check .env MONGODB_URI
```

### "Port Already in Use"
```bash
# Find and kill process
lsof -i :5000
kill -9 <PID>

# Or use different port
PORT=5001 npm run dev
```

## Getting Help

1. **Issues**: Check existing issues first
2. **Discussions**: Ask in GitHub discussions
3. **Slack/Chat**: Join our community chat
4. **Documentation**: See README.md and ARCHITECTURE.md

## Attribution

Contributors will be recognized in CONTRIBUTORS.md

## License

By contributing, you agree this code will be under the same license as the project.

---

**Happy coding! 🚀**
