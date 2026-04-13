import { createClient } from 'redis'

let redisClient
let isConnected = false

const getClient = async () => {
  if (isConnected) {
    return redisClient
  }

  if (!redisClient) {
    redisClient = createClient({
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
      password: process.env.REDIS_PASSWORD,
      retry_strategy: () => 10000,
    })

    redisClient.on('error', (err) => console.error('Redis error:', err))
    redisClient.on('connect', () => {
      console.log('Connected to Redis')
      isConnected = true
    })
  }

  return redisClient
}

export const connect = async () => {
  const client = await getClient()
  return new Promise((resolve, reject) => {
    if (isConnected) {
      resolve()
    } else {
      // Add timeout of 5 seconds
      const timeout = setTimeout(() => {
        console.warn('⚠️ Redis connection timeout - continuing without cache')
        resolve() // Resolve anyway to allow server to start
      }, 5000)

      const handleConnect = () => {
        clearTimeout(timeout)
        resolve()
      }

      const handleError = (err) => {
        clearTimeout(timeout)
        console.warn('⚠️ Redis connection failed - continuing without cache:', err.message)
        resolve() // Resolve anyway to allow server to start
      }

      client.once('connect', handleConnect)
      client.once('error', handleError)
    }
  })
}

export const disconnect = async () => {
  if (redisClient && isConnected) {
    return new Promise((resolve, reject) => {
      redisClient.quit((err) => {
        if (err) reject(err)
        else {
          isConnected = false
          resolve()
        }
      })
    })
  }
}

export const get = async (key) => {
  try {
    const client = await getClient()
    return new Promise((resolve, reject) => {
      client.get(key, (err, data) => {
        if (err) reject(err)
        else resolve(data ? JSON.parse(data) : null)
      })
    })
  } catch (error) {
    console.error('Redis get error:', error)
    return null
  }
}

export const set = async (key, value, expirySeconds = 3600) => {
  try {
    const client = await getClient()
    return new Promise((resolve, reject) => {
      client.setex(key, expirySeconds, JSON.stringify(value), (err) => {
        if (err) reject(err)
        else resolve()
      })
    })
  } catch (error) {
    console.error('Redis set error:', error)
  }
}

export const del = async (key) => {
  try {
    const client = await getClient()
    return new Promise((resolve, reject) => {
      client.del(key, (err) => {
        if (err) reject(err)
        else resolve()
      })
    })
  } catch (error) {
    console.error('Redis delete error:', error)
  }
}

export const invalidateUserChatsCache = async (userIds) => {
  const users = Array.isArray(userIds) ? userIds : [userIds]
  const promises = users.map(async (userId) => {
    try {
      const client = await getClient()
      return new Promise((resolve, reject) => {
        client.keys(`user_chats:${userId}:*`, (err, keys) => {
          if (err) reject(err)
          if (keys.length === 0) {
            resolve()
          } else {
            client.del(...keys, (err) => {
              if (err) reject(err)
              else resolve()
            })
          }
        })
      })
    } catch (error) {
      console.error('Cache invalidation error:', error)
    }
  })

  return Promise.all(promises)
}

export const getChat = async (chatId) => {
  return get(`chat:${chatId}`)
}

export const setChat = async (chat, expirySeconds = 600) => {
  const chatId = chat._id || chat.id
  return set(`chat:${chatId}`, chat, expirySeconds)
}
