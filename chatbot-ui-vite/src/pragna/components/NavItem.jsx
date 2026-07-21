const NavItem = ({ icon: Icon, label, active = false, onClick }) => {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '13px',
        width: '100%',
        padding: '11px 14px',
        borderRadius: '11px',
        border: active ? '1px solid rgba(212,175,55,0.30)' : '1px solid transparent',
        background: active ? 'linear-gradient(135deg, rgba(212,175,55,0.14), rgba(184,134,11,0.07))' : 'transparent',
        color: active ? 'var(--pragna-gold-soft)' : 'var(--pragna-text-soft)',
        fontSize: '14.5px',
        fontWeight: active ? 650 : 500,
        letterSpacing: '0.2px',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'all 0.15s ease',
      }}
      className="hover:bg-[var(--pragna-surface-2)] hover:text-[var(--pragna-gold-soft)]"
    >
      <span style={{ display: 'flex', width: '20px', height: '20px', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon size={17} />
      </span>
      {label}
    </button>
  )
}

export default NavItem
