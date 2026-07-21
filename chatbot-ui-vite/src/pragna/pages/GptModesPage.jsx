const CHAT_MODE_ITEMS = [
  { id: 'general', label: 'General', description: 'Standard helpful assistant' },
  { id: 'explain_concepts', label: 'Explain', description: 'Break down complex ideas' },
  { id: 'generate_ideas', label: 'Ideas', description: 'Creative brainstorming' },
  { id: 'write_content', label: 'Write', description: 'Professional writing' },
  { id: 'code_assistance', label: 'Code', description: 'Programming help' },
  { id: 'ask_questions', label: 'Questions', description: 'Curious inquiry' },
  { id: 'creative_writing', label: 'Story', description: 'Storytelling and narrative' },
]

const GptModesPage = ({ chatMode, onSelectMode }) => {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '48px', animation: 'fadeUp 0.4s ease', height: '100%' }}>
      <h1 style={{ margin: '0 0 8px 0', fontSize: '28px', fontWeight: 700, color: 'var(--pragna-text)' }}>
        Pragna GPT Modes
      </h1>
      <p style={{ margin: '0 0 30px 0', fontSize: '14.5px', color: 'var(--pragna-text-muted)' }}>
        Choose a specialized behavior profile for your assistant.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 260px))', gap: '16px', maxWidth: '900px' }}>
        {CHAT_MODE_ITEMS.map((mode) => {
          const active = chatMode === mode.id
          
          const cardBg = active
            ? 'linear-gradient(135deg, rgba(212,175,55,0.1), #000000)'
            : '#000000'
          const cardBorder = active
            ? 'rgba(212,175,55,0.5)'
            : 'rgba(212,175,55,0.15)'
          const cardTitleColor = active ? 'var(--pragna-gold-soft)' : 'var(--pragna-text)'

          return (
            <button
              key={mode.id}
              onClick={() => onSelectMode(mode.id)}
              style={{
                padding: '22px',
                borderRadius: '16px',
                textAlign: 'left',
                cursor: 'pointer',
                background: cardBg,
                border: `1px solid ${cardBorder}`,
                boxShadow: '0 2px 8px rgba(0,0,0,0.28)',
                transition: 'all 0.15s ease',
              }}
              className="hover:border-accent-500/50"
            >
              <div style={{ fontSize: '16.5px', fontWeight: 700, color: cardTitleColor, marginBottom: '6px' }}>
                {mode.label}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--pragna-text-muted)' }}>
                {mode.description}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default GptModesPage
