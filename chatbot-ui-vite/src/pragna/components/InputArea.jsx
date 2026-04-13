import { useState } from 'react'
import { Send, Hash, Search, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'

const InputArea = () => {
  const [message, setMessage] = useState('')
  const [deepThink, setDeepThink] = useState(false)
  const [searchEnabled, setSearchEnabled] = useState(false)

  return (
    <div className="w-full max-w-3xl mx-auto mt-8">
      <div className="relative">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask anything or describe what you need..."
          rows={2}
          className="w-full px-5 py-4 bg-white border border-border rounded-2xl shadow-premium-sm focus:shadow-premium-md focus:ring-2 focus:ring-accent-500/20 focus:border-accent-300 transition-all duration-200 resize-none text-gray-700 placeholder:text-gray-400"
        />
        
        <div className="absolute bottom-3 right-3 flex items-center gap-2">
          <button
            onClick={() => setDeepThink(!deepThink)}
            className={`
              p-1.5 rounded-lg transition-all duration-200
              ${deepThink 
                ? 'bg-accent-100 text-accent-700' 
                : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
              }
            `}
          >
            <Hash size={16} />
          </button>
          <button
            onClick={() => setSearchEnabled(!searchEnabled)}
            className={`
              p-1.5 rounded-lg transition-all duration-200
              ${searchEnabled 
                ? 'bg-accent-100 text-accent-700' 
                : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
              }
            `}
          >
            <Search size={16} />
          </button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="p-1.5 bg-accent-600 text-white rounded-lg shadow-sm hover:bg-accent-700 transition-colors"
          >
            <Send size={16} />
          </motion.button>
        </div>
      </div>
      
      <div className="flex items-center justify-between mt-2 text-xs text-gray-400 px-1">
        <div className="flex gap-3">
          {deepThink && <span className="flex items-center gap-1"><Hash size={10} /> DeepThink active</span>}
          {searchEnabled && <span className="flex items-center gap-1"><Search size={10} /> Web search</span>}
        </div>
        <span className="flex items-center gap-1"><Sparkles size={10} /> 0 credits</span>
      </div>
    </div>
  )
}

export default InputArea
