import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Bot, Search, Hammer, Bug, BookOpen, Sparkles,
  Brain, Wrench, Upload, AlertTriangle, CheckCircle2, XCircle,
  Paperclip, Square, Trash2, ChevronUp, ChevronDown,
} from 'lucide-react'
import { runAgentStream, resumeAgentStream } from '../../api/api'

const MODES = [
  { id: 'general',     label: 'General',     icon: Bot,      desc: 'General coding assistant' },
  { id: 'code_review', label: 'Code Review',  icon: Search,   desc: 'Bugs, security, style analysis' },
  { id: 'app_builder', label: 'App Builder',  icon: Hammer,   desc: 'Build complete apps step by step' },
  { id: 'debug',       label: 'Debug',        icon: Bug,      desc: 'Find and fix bugs systematically' },
  { id: 'explain',     label: 'Explain',      icon: BookOpen, desc: 'Understand code and concepts' },
  { id: 'refactor',    label: 'Refactor',     icon: Sparkles, desc: 'Clean up and improve code' },
]

// Event stream palette: cards sit on the gold/dark surface (`var(--pragna-surface)`),
// only the border/label accent carries the semantic color (thinking = gold,
// tool activity = green, needs-attention = amber, error = red).
const EVENT_COLORS = {
  thought:     { bg: 'var(--pragna-surface)', border: 'rgba(212,175,55,0.4)',  label: 'Thinking',        labelColor: 'var(--pragna-gold-soft)', Icon: Brain },
  tool_call:   { bg: 'var(--pragna-surface)', border: 'rgba(52,211,153,0.4)',  label: 'Tool Call',       labelColor: '#34d399', Icon: Wrench },
  tool_result: { bg: 'var(--pragna-surface)', border: 'rgba(251,191,36,0.35)', label: 'Result',          labelColor: '#fbbf24', Icon: Upload },
  confirm_required: { bg: 'var(--pragna-surface)', border: 'rgba(251,191,36,0.5)', label: 'Approval needed', labelColor: '#fbbf24', Icon: AlertTriangle },
  done:        { bg: 'var(--pragna-surface)', border: 'rgba(52,211,153,0.4)',  label: 'Done',            labelColor: '#6ee7b7', Icon: CheckCircle2 },
  error:       { bg: 'var(--pragna-surface)', border: 'rgba(248,113,113,0.4)', label: 'Error',           labelColor: '#fca5a5', Icon: XCircle },
}

function LightningIcon({ size = 22, glow = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--pragna-accent)"
      strokeWidth={glow ? 1.6 : 2}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={glow ? { filter: 'drop-shadow(0 0 14px rgba(212,175,55,0.4))' } : undefined}
    >
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  )
}

function PlayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function ToolCallCard({ event }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = EVENT_COLORS.tool_call

  return (
    <div style={{
      background: cfg.bg,
      backdropFilter: 'blur(8px)',
      border: `1px solid ${cfg.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      margin: '6px 0',
      fontFamily: 'monospace',
      fontSize: 13,
      boxShadow: '0 2px 8px rgba(0,0,0,0.28)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
           onClick={() => setExpanded(e => !e)}>
        <span style={{ color: cfg.labelColor, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Wrench size={13} /> {event.tool}
        </span>
        <span style={{ color: 'var(--pragna-text-muted)', fontSize: 11, marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />} args
        </span>
      </div>
      {expanded && (
        <pre style={{ margin: '8px 0 0', color: 'var(--pragna-text-muted)', fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {JSON.stringify(event.args, null, 2)}
        </pre>
      )}
    </div>
  )
}

function ToolResultCard({ event }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = EVENT_COLORS.tool_result
  const preview = (event.content || '').slice(0, 120)
  const hasMore = (event.content || '').length > 120

  return (
    <div style={{
      background: cfg.bg,
      backdropFilter: 'blur(8px)',
      border: `1px solid ${cfg.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      margin: '6px 0',
      fontFamily: 'monospace',
      fontSize: 12,
      boxShadow: '0 2px 8px rgba(0,0,0,0.28)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: hasMore ? 'pointer' : 'default' }}
           onClick={() => hasMore && setExpanded(e => !e)}>
        <span style={{ color: cfg.labelColor, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Upload size={13} /> {event.tool} result
        </span>
        {hasMore && (
          <span style={{ color: 'var(--pragna-text-muted)', fontSize: 11, marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />} {expanded ? 'less' : 'more'}
          </span>
        )}
      </div>
      <pre style={{ margin: '6px 0 0', color: 'var(--pragna-text-muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {expanded ? event.content : (preview + (hasMore ? '...' : ''))}
      </pre>
    </div>
  )
}

function ConfirmCard({ event, onDecision }) {
  const cfg = EVENT_COLORS.confirm_required

  return (
    <div style={{
      background: cfg.bg,
      backdropFilter: 'blur(8px)',
      border: `1px solid ${cfg.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      margin: '6px 0',
      boxShadow: '0 2px 8px rgba(0,0,0,0.28)',
    }}>
      <div style={{ color: cfg.labelColor, fontWeight: 700, fontSize: 12, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
        <AlertTriangle size={13} /> {cfg.label}: {event.tool}
      </div>
      <pre style={{
        margin: '0 0 10px',
        color: 'var(--pragna-text)',
        fontSize: 12,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-all',
        fontFamily: 'monospace',
        maxHeight: 240,
        overflowY: 'auto',
      }}>
        {event.preview}
      </pre>
      {event.resolved ? (
        <div style={{
          color: event.resolved === 'approved' ? '#6ee7b7' : '#fca5a5',
          fontSize: 12,
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}>
          {event.resolved === 'approved' ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
          {event.resolved === 'approved' ? 'Approved' : 'Rejected'}
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => onDecision(event, 'approve')}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(52,211,153,0.4)',
              background: 'var(--pragna-surface)', color: '#34d399', fontWeight: 700, fontSize: 12, cursor: 'pointer',
            }}
          >
            <CheckCircle2 size={14} /> Approve
          </button>
          <button
            onClick={() => onDecision(event, 'reject')}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(248,113,113,0.4)',
              background: 'var(--pragna-surface)', color: '#fca5a5', fontWeight: 700, fontSize: 12, cursor: 'pointer',
            }}
          >
            <XCircle size={14} /> Reject
          </button>
        </div>
      )}
    </div>
  )
}

function EventBlock({ event, onDecision }) {
  if (event.type === 'tool_call') return <ToolCallCard event={event} />
  if (event.type === 'tool_result') return <ToolResultCard event={event} />
  if (event.type === 'confirm_required') return <ConfirmCard event={event} onDecision={onDecision} />

  const cfg = EVENT_COLORS[event.type] || EVENT_COLORS.thought

  return (
    <div style={{
      background: cfg.bg,
      backdropFilter: 'blur(8px)',
      border: `1px solid ${cfg.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      margin: '6px 0',
      boxShadow: '0 2px 8px rgba(0,0,0,0.28)',
    }}>
      <div style={{ color: cfg.labelColor, fontWeight: 700, fontSize: 12, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
        <cfg.Icon size={13} /> {cfg.label}
      </div>
      <div style={{
        color: event.type === 'done' ? 'var(--pragna-text)' : 'var(--pragna-text)',
        fontSize: 14,
        lineHeight: 1.65,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: 'inherit',
      }}>
        {event.content}
      </div>
    </div>
  )
}

function ThinkingDots() {
  return (
    <div style={{ display: 'flex', gap: 5, padding: '10px 0', alignItems: 'center' }}>
      <span style={{ color: 'var(--pragna-gold-soft)', fontSize: 13 }}>Agent is thinking</span>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%',
          background: 'var(--pragna-accent)',
          display: 'inline-block',
          animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
    </div>
  )
}

export default function AgentPanel() {
  const [selectedMode, setSelectedMode] = useState('general')
  const [task, setTask] = useState('')
  const [events, setEvents] = useState([])
  const [isRunning, setIsRunning] = useState(false)
  const [contextFiles, setContextFiles] = useState('')
  const controllerRef = useRef(null)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  const handleRun = useCallback(() => {
    if (!task.trim() || isRunning) return
    setEvents([])
    setIsRunning(true)

    const files = contextFiles.split('\n').map(s => s.trim()).filter(Boolean)

    controllerRef.current = runAgentStream({
      task: task.trim(),
      mode: selectedMode,
      contextFiles: files,
      onEvent: (event) => {
        setEvents(prev => [...prev, event])
        if (event.type === 'done' || event.type === 'error' || event.type === 'confirm_required') {
          setIsRunning(false)
        }
      },
    })
  }, [task, selectedMode, contextFiles, isRunning])

  const handleDecision = useCallback((event, decision) => {
    setEvents(prev => prev.map(e => (
      e === event ? { ...e, resolved: decision === 'approve' ? 'approved' : 'rejected' } : e
    )))
    setIsRunning(true)

    controllerRef.current = resumeAgentStream({
      sessionId: event.session_id,
      decision,
      onEvent: (ev) => {
        setEvents(prev => [...prev, ev])
        if (ev.type === 'done' || ev.type === 'error' || ev.type === 'confirm_required') {
          setIsRunning(false)
        }
      },
    })
  }, [])

  const handleStop = () => {
    controllerRef.current?.abort()
    setIsRunning(false)
    setEvents(prev => [...prev, { type: 'error', content: 'Stopped by user.' }])
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleRun()
    }
  }

  const handleClear = () => {
    setEvents([])
    setTask('')
  }

  const activeMode = MODES.find(m => m.id === selectedMode)

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--pragna-bg)',
      color: 'var(--pragna-text)',
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{
        padding: '18px 24px 14px',
        borderBottom: '1px solid var(--pragna-border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <LightningIcon size={22} />
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--pragna-text)' }}>Pragna Code</h2>
          <span style={{
            padding: '3px 11px',
            borderRadius: 999,
            background: 'rgba(212,175,55,0.14)',
            border: '1px solid rgba(212,175,55,0.3)',
            color: 'var(--pragna-accent)',
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: '0.6px',
          }}>AGENT</span>
        </div>
        <p style={{ margin: 0, color: 'var(--pragna-text-muted)', fontSize: 13 }}>
          Agentic AI that reads, writes, and runs code autonomously via Ollama
        </p>
      </div>

      {/* Mode selector */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--pragna-border)' }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {MODES.map(mode => (
            <button
              key={mode.id}
              onClick={() => setSelectedMode(mode.id)}
              title={mode.desc}
              style={{
                padding: '6px 12px',
                borderRadius: 999,
                border: selectedMode === mode.id ? '1px solid rgba(212,175,55,0.5)' : '1px solid var(--pragna-border)',
                background: selectedMode === mode.id
                  ? 'linear-gradient(135deg, rgba(212,175,55,0.22), rgba(184,134,11,0.12))'
                  : 'var(--pragna-surface)',
                color: selectedMode === mode.id ? 'var(--pragna-gold-soft)' : 'var(--pragna-text-muted)',
                fontSize: 12,
                fontWeight: selectedMode === mode.id ? 700 : 400,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                transition: 'all 0.15s',
              }}
            >
              <mode.icon size={13} /> {mode.label}
            </button>
          ))}
        </div>
        {activeMode && (
          <p style={{ margin: '8px 0 0', color: 'var(--pragna-text-muted)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <activeMode.icon size={13} /> <strong style={{ color: 'var(--pragna-accent)' }}>{activeMode.label}:</strong> {activeMode.desc}
          </p>
        )}
      </div>

      {/* Events stream */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
        {events.length === 0 && !isRunning && (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
              <LightningIcon size={34} glow />
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--pragna-text)', marginBottom: 8 }}>
              Ready to work
            </div>
            <div style={{ fontSize: 13, color: 'var(--pragna-text-muted)', lineHeight: 1.7 }}>
              Type a task below. The agent will think, use tools, and complete the job autonomously.<br />
              Examples:<br />
              <span style={{ opacity: 0.85 }}>• "Review the backend code for security issues"</span><br />
              <span style={{ opacity: 0.85 }}>• "Create a REST API for user authentication"</span><br />
              <span style={{ opacity: 0.85 }}>• "Debug why image generation returns empty"</span><br />
              <span style={{ opacity: 0.85 }}>• "Explain how the RAG system works"</span>
            </div>
          </div>
        )}
        {events.map((event, i) => (
          <EventBlock key={i} event={event} onDecision={handleDecision} />
        ))}
        {isRunning && <ThinkingDots />}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: '14px 16px',
        borderTop: '1px solid var(--pragna-border)',
      }}>
        {/* Context files input (collapsible) */}
        <details style={{ marginBottom: 8 }}>
          <summary style={{ color: 'var(--pragna-text-muted)', fontSize: 12, cursor: 'pointer', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Paperclip size={13} /> Context files (optional — paths to pre-load)
          </summary>
          <textarea
            value={contextFiles}
            onChange={e => setContextFiles(e.target.value)}
            placeholder="One file path per line&#10;e.g. backend/app.py"
            rows={2}
            style={{
              width: '100%',
              background: 'var(--pragna-surface)',
              border: '1px solid var(--pragna-border)',
              borderRadius: 8,
              padding: '8px 10px',
              color: 'var(--pragna-text-muted)',
              fontSize: 12,
              fontFamily: 'monospace',
              resize: 'vertical',
              boxSizing: 'border-box',
              marginTop: 4,
            }}
          />
        </details>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          padding: '14px 16px',
          borderRadius: 14,
          background: 'var(--pragna-surface)',
          border: '1px solid rgba(212,175,55,0.18)',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 12px 28px rgba(0,0,0,0.42)',
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <textarea
              ref={textareaRef}
              value={task}
              onChange={e => setTask(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Describe your task for ${activeMode?.label || 'the agent'}… (Ctrl+Enter to run)`}
              rows={3}
              disabled={isRunning}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                borderRadius: 0,
                padding: 0,
                color: 'var(--pragna-text)',
                fontSize: 14,
                fontFamily: 'inherit',
                resize: 'vertical',
                outline: 'none',
                lineHeight: 1.5,
                boxSizing: 'border-box',
                minHeight: 72,
                opacity: isRunning ? 0.6 : 1,
              }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {isRunning ? (
                <button
                  onClick={handleStop}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 7,
                    padding: '9px 18px',
                    borderRadius: 10,
                    border: '1px solid rgba(248,113,113,0.4)',
                    background: 'var(--pragna-surface)',
                    color: '#fca5a5',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <Square size={12} fill="currentColor" /> Stop
                </button>
              ) : (
                <button
                  onClick={handleRun}
                  disabled={!task.trim()}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 7,
                    padding: '9px 18px',
                    borderRadius: 10,
                    border: 'none',
                    background: task.trim() ? 'linear-gradient(135deg, var(--pragna-gold-soft), var(--pragna-gold-deep))' : 'var(--pragna-border)',
                    color: task.trim() ? 'var(--pragna-bg)' : '#6b6558',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: task.trim() ? 'pointer' : 'not-allowed',
                    whiteSpace: 'nowrap',
                    boxShadow: task.trim() ? '0 2px 8px rgba(0,0,0,0.28)' : 'none',
                    transition: 'all 0.15s',
                  }}
                >
                  <PlayIcon /> Run
                </button>
              )}
              {events.length > 0 && !isRunning && (
                <button
                  onClick={handleClear}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '6px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--pragna-border)',
                    background: 'transparent',
                    color: 'var(--pragna-text-muted)',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  <Trash2 size={12} /> Clear
                </button>
              )}
            </div>
          </div>
          <p style={{ margin: 0, color: 'var(--pragna-text-muted)', fontSize: 11.5, opacity: 0.75 }}>
            Ctrl+Enter to run • Agent uses Ollama model: <strong style={{ color: 'var(--pragna-text-muted)' }}>{'{OLLAMA_MODEL}'}</strong>
          </p>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1.2); }
        }
        details > summary { list-style: none; }
        details > summary::-webkit-details-marker { display: none; }
      `}</style>
    </div>
  )
}
