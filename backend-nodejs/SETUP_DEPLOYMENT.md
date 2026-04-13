# Setup & Deployment Guide

Complete guide for setting up and deploying the EtherX Chat Backend.

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Docker Setup](#docker-setup)
3. [Production Deployment](#production-deployment)
4. [Database Management](#database-management)
5. [Monitoring & Logging](#monitoring--logging)
6. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites
- Node.js 18+ ([download](https://nodejs.org/))
- MongoDB Community Edition 4.4+ ([download](https://www.mongodb.com/try/download/community))
- Redis 6.0+ ([download](https://redis.io/download))
- npm or yarn

### Step 1: Install MongoDB

**Windows:**
```bash
# Download and run the installer
# https://www.mongodb.com/try/download/community

# Verify installation
mongod --version
```

**macOS (using Homebrew):**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Linux (Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y mongodb
sudo systemctl start mongod
```

### Step 2: Install Redis

**Windows:**
```bash
# Using WSL (Windows Subsystem for Linux)
# Or use Redis container with Docker
```

**macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu):**
```bash
sudo apt-get install -y redis-server
sudo systemctl start redis-server
```

### Step 3: Setup Backend

```bash
# Navigate to backend directory
cd backend-nodejs

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Edit .env with your configuration
# Important: Set JWT_SECRET to a strong random value
```

### Step 4: Verify Connections

```bash
# Check MongoDB
mongosh --eval "db.runCommand({ping: 1})"

# Check Redis
redis-cli ping
# Output: PONG

# Check Node.js
node --version
npm --version
```

### Step 5: Start Development Server

```bash
# Terminal 1: Start backend
npm run dev

# Output should show:
# ✅ Connected to MongoDB
# 🚀 Server running on port 5000
# 📡 Socket.IO listening on ws://localhost:5000
```

### Step 6: Test API

```bash
# Health check
curl http://localhost:5000/health

# Response: {"status":"OK","timestamp":"..."}
```

---

## Docker Setup

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Quick Start with Docker Compose

```bash
# Navigate to backend directory
cd backend-nodejs

# Start all services
docker-compose up -d

# Output:
# ✓ Creating etherx-mongodb
# ✓ Creating etherx-redis
# ✓ Creating etherx-backend

# Check logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Remove volumes (clean database)
docker-compose down -v
```

### Build Custom Docker Image

```bash
# Build image
docker build -t etherx-backend:latest .

# Run container
docker run -d \
  --name etherx-backend \
  -p 5000:5000 \
  -e MONGODB_URI=mongodb://host.docker.internal:27017/etherx-chat \
  -e REDIS_HOST=host.docker.internal \
  etherx-backend:latest

# View logs
docker logs -f etherx-backend

# Stop container
docker stop etherx-backend
docker rm etherx-backend
```

### Docker Network

```bash
# Create network
docker network create etherx-network

# Run MongoDB
docker run -d \
  --name mongodb \
  --network etherx-network \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  mongo:6.0-alpine

# Run Redis
docker run -d \
  --name redis \
  --network etherx-network \
  redis:7-alpine

# Run Backend
docker run -d \
  --name backend \
  --network etherx-network \
  -p 5000:5000 \
  -e MONGODB_URI=mongodb://admin:password@mongodb:27017/etherx-chat \
  -e REDIS_HOST=redis \
  etherx-backend:latest
```

---

## Production Deployment

### Pre-deployment Checklist

- [ ] Update `NODE_ENV=production` in `.env`
- [ ] Set strong JWT_SECRET
- [ ] Configure MongoDB connection string
- [ ] Setup Redis with authentication
- [ ] Enable SSL/TLS for HTTPS
- [ ] Setup error monitoring (e.g., Sentry)
- [ ] Configure logging
- [ ] Setup backups
- [ ] Configure rate limiting
- [ ] Setup CORS for production frontend URL

### Environment Variables for Production

```env
# Production settings
NODE_ENV=production
PORT=5000

# Database (use cloud instance)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/etherx-chat?retryWrites=true&w=majority

# Redis (use cloud instance)
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=your_strong_password

# Security
JWT_SECRET=use_a_very_strong_random_string_at_least_32_chars
JWT_EXPIRE=7d

# Client
CLIENT_URL=https://app.example.com
SERVER_URL=https://api.example.com

# Logging
LOG_LEVEL=info
```

### Deployment to Heroku

```bash
# Install Heroku CLI
brew tap heroku/brew && brew install heroku

# Login
heroku login

# Create app
heroku create etherx-backend

# Add-ons
heroku addons:create mongolab:sandbox -a etherx-backend
heroku addons:create heroku-redis:premium-0 -a etherx-backend

# Set environment variables
heroku config:set JWT_SECRET=your_strong_secret -a etherx-backend
heroku config:set NODE_ENV=production -a etherx-backend

# Deploy
git push heroku main

# View logs
heroku logs --tail -a etherx-backend

# Scale dyno
heroku ps:scale web=2 -a etherx-backend
```

### Deployment to AWS EC2

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install MongoDB
sudo apt-get install -y mongodb-org

# Install Redis
sudo apt-get install -y redis-server

# Clone repository
git clone your-repo-url
cd backend-nodejs

# Install dependencies
npm install

# Setup PM2 for process management
sudo npm install -g pm2

# Start app with PM2
pm2 start server.js --name "etherx-backend"
pm2 startup
pm2 save

# Setup Nginx as reverse proxy
sudo apt-get install -y nginx

# Create Nginx config
sudo tee /etc/nginx/sites-available/etherx << EOF
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/etherx /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL with Let's Encrypt
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
```

### Deployment to DigitalOcean

```bash
# Via App Platform (recommended)
1. Connect GitHub repository
2. Select backend-nodejs directory
3. Configure environment variables
4. Set run command: npm start
5. Deploy

# Access at: https://etherx-backend-xxxx.ondigitalocean.app
```

---

## Database Management

### MongoDB Backup & Restore

```bash
# Backup
mongodump --uri="mongodb://localhost:27017/etherx-chat" --out ./backup

# Restore
mongorestore --uri="mongodb://localhost:27017/etherx-chat" ./backup/etherx-chat

# Cloud backup (MongoDB Atlas)
# Automated backups available in Atlas dashboard
```

### Create Indexes

```bash
# Connect to MongoDB
mongosh

# Select database
use etherx-chat

# Create indexes
db.chats.createIndex({ participants: 1 })
db.chats.createIndex({ created_by: 1 })
db.chats.createIndex({ created_at: -1 })
db.messages.createIndex({ chat_id: 1, created_at: -1 })
db.messages.createIndex({ sender_id: 1 })
db.users.createIndex({ email: 1 }, { unique: true })

# View indexes
db.chats.getIndexes()
```

---

## Monitoring & Logging

### Application Monitoring

```bash
# Monitor with PM2
pm2 monit

# View real-time logs
pm2 logs etherx-backend

# Save logs
pm2 logs > app.log 2>&1
```

### Database Monitoring

```bash
# MongoDB stats
mongosh
db.stats()
db.chats.stats()

# Connection statistics
db.serverStatus().connections
```

### Redis Monitoring

```bash
# Connect to Redis CLI
redis-cli

# Monitor commands
MONITOR

# Get stats
INFO

# Memory usage
INFO memory
```

### Application Performance Monitoring (APM)

**With New Relic:**
```bash
npm install newrelic

# Add to server.js
require('newrelic');
```

**With Datadog:**
```bash
npm install dd-trace

# Add to server.js
require('dd-trace').init();
```

---

## Troubleshooting

### Common Issues

#### MongoDB Connection Fails
```bash
# Check if MongoDB is running
ps aux | grep mongod

# Start MongoDB
sudo systemctl start mongod

# Check connection string
mongosh "mongodb://user:pass@host:port/db"
```

#### Redis Connection Fails
```bash
# Check if Redis is running
ps aux | grep redis

# Start Redis
sudo systemctl start redis-server

# Test connection
redis-cli ping
```

#### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>

# Or use different port
PORT=5001 npm start
```

#### JWT Token Invalid
- Check JWT_SECRET matches between server and client
- Verify token hasn't expired
- Check token format (Bearer token)

#### Memory Leak Issues
```bash
# Monitor memory usage
pm2 monit

# Create heap dump
node --inspect server.js

# Use Chrome DevTools to analyze
```

#### Rate Limiting Too Strict
Edit `.env`:
```env
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX=1000
```

### Debug Mode

```bash
# Enable debug logging
DEBUG=* npm start

# Or specific modules
DEBUG=express:* npm start
```

### Performance Issues

1. **Check database indexes:**
   ```bash
   db.chats.getIndexes()
   ```

2. **Monitor slow queries:**
   ```bash
   db.setProfilingLevel(1, { slowms: 100 })
   ```

3. **Check Redis memory:**
   ```bash
   redis-cli INFO memory
   ```

4. **Profile Node.js:**
   ```bash
   node --prof server.js
   node --prof-process isolate-*.log > profile.txt
   ```

---

## Scaling Considerations

### Horizontal Scaling
- Use load balancer (Nginx, HAProxy)
- Deploy multiple backend instances
- Use Redis for session store
- Share database across instances

### Vertical Scaling
- Increase server resources (CPU, RAM)
- Optimize database queries
- Implement caching strategies
- Use CDN for static assets

### Performance Optimization
- Enable compression
- Implement rate limiting
- Use database indexes
- Optimize API responses
- Cache frequently accessed data

---

## Security Hardening

1. **Enable HTTPS/SSL:**
   ```nginx
   listen 443 ssl http2;
   ssl_certificate /path/to/cert.pem;
   ssl_certificate_key /path/to/key.pem;
   ```

2. **Set Security Headers:**
   Already configured with Helmet middleware

3. **Enable CORS properly:**
   ```env
   CLIENT_URL=https://app.example.com
   ```

4. **Use strong JWT secret:**
   ```bash
   node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
   ```

5. **Enable MongoDB authentication:**
   ```bash
   mongod --auth
   ```

6. **Setup firewall rules:**
   ```bash
   sudo ufw allow 5000/tcp
   sudo ufw enable
   ```

---

## Support & Resources

- **Documentation**: [README.md](./README.md)
- **API Testing**: [API_TESTING.md](./API_TESTING.md)
- **MongoDB Docs**: https://docs.mongodb.com/
- **Express Docs**: https://expressjs.com/
- **Socket.IO Docs**: https://socket.io/docs/
- **Node.js Docs**: https://nodejs.org/docs/
