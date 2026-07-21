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
    <div className="inline-flex gap-2 p-[5px] rounded-full bg-[var(--pragna-surface)] border border-border">
      <button
        onClick={() => setMode('basic')}
        title="Slightly powerful model"
        className={`
          flex items-center gap-1.5 px-5 py-[9px] rounded-full text-[13.5px] font-[650] transition-all duration-150
          ${mode === 'basic'
            ? 'bg-gradient-to-br from-accent-400 to-accent-500 text-[var(--pragna-on-gold)] shadow-premium-sm'
            : 'text-[var(--pragna-text-muted)] hover:text-accent-400'
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
          flex items-center gap-1.5 px-5 py-[9px] rounded-full text-[13.5px] font-[650] transition-all duration-150
          ${mode === 'pro'
            ? 'bg-gradient-to-br from-accent-400 to-accent-500 text-[var(--pragna-on-gold)] shadow-premium-sm'
            : 'text-[var(--pragna-text-muted)] hover:text-accent-400'
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
