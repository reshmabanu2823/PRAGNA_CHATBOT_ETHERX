import mongoose from 'mongoose'

const connectDB = async () => {
  try {
    const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/etherx-chat'

    await mongoose.connect(uri, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
      retryWrites: true,
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      connectTimeoutMS: 10000,
    })

    console.log('✅ Connected to MongoDB')
    return true
  } catch (error) {
    console.error('❌ MongoDB connection error:', error.message)
    throw error
  }
}

export const disconnectDB = async () => {
  try {
    await mongoose.disconnect()
    console.log('✅ Disconnected from MongoDB')
  } catch (error) {
    console.error('❌ Disconnect error:', error)
  }
}

export default connectDB
