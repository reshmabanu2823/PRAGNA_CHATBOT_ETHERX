const NavItem = ({ icon: Icon, label, active = false, onClick }) => {
  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200
        ${active 
          ? 'bg-accent-50 text-accent-700' 
          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
        }
      `}
    >
      <Icon size={18} className={active ? 'text-accent-600' : 'text-gray-500'} />
      <span className="text-sm font-medium">{label}</span>
    </button>
  )
}

export default NavItem
