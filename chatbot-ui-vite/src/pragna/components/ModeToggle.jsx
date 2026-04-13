import { useEffect, useState } from 'react'
import { Zap, Brain } from 'lucide-react'

const ModeToggle = () => {
  const [mode, setMode] = useState(() => {
    const saved = localStorage.getItem('pragna_model_profile') || 'basic'
    if (saved === 'instant') return 'basic'
    if (saved === 'expert') return 'pro'
    return saved
  })

  useEffect(() => {
    localStorage.setItem('pragna_model_profile', mode)
  }, [mode])

  return (
    <div className="inline-flex gap-1 p-1 bg-gray-100/80 rounded-xl">
      <button
        onClick={() => setMode('basic')}
        title="Slightly powerful model"
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200
          ${mode === 'basic' 
            ? 'bg-white shadow-sm text-accent-700' 
            : 'text-gray-500 hover:text-gray-700'
          }
        `}
      >
        <Zap size={14} />
        <span>Pragna Basic</span>
      </button>
      <button
        onClick={() => setMode('pro')}
        title="Heavily powerful model"
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200
          ${mode === 'pro' 
            ? 'bg-white shadow-sm text-accent-700' 
            : 'text-gray-500 hover:text-gray-700'
          }
        `}
      >
        <Brain size={14} />
        <span>Pragna Pro</span>
      </button>
    </div>
  )
}

export default ModeToggle
