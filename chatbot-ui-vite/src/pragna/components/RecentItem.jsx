import { useState, useRef, useEffect } from 'react'
import { MessageSquare, MoreVertical, Share, Users, Edit2, Pin, Archive, Trash2 } from 'lucide-react'

const RecentItem = ({ 
  id,
  title, 
  onClick, 
  onDelete, 
  onRename,
  onShare,
  onPinChat,
  onArchive,
  onStartGroupChat,
  active = false,
  isPinned = false 
}) => {
  const [showMenu, setShowMenu] = useState(false)
  const menuRef = useRef(null)
  const buttonRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target) && !buttonRef.current?.contains(event.target)) {
        setShowMenu(false)
      }
    }

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showMenu])

  const handleMenuClick = (e, callback) => {
    e.stopPropagation()
    callback?.()
    setShowMenu(false)
  }

  return (
    <div
      className={`w-full flex items-center justify-between group px-2 py-1.5 rounded-lg transition-colors relative ${
        active ? 'bg-gray-700' : 'hover:bg-gray-700/50'
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        className="flex-1 min-w-0 flex items-center gap-2 text-left"
      >
        <MessageSquare size={14} className={`flex-shrink-0 ${active ? 'text-yellow-500' : 'text-gray-500 group-hover:text-yellow-500'}`} />
        <span className={`text-xs truncate ${active ? 'text-yellow-100' : 'text-gray-300 group-hover:text-gray-100'}`}>{title}</span>
      </button>

      <button
        ref={buttonRef}
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setShowMenu(!showMenu)
        }}
        className="ml-2 p-1 rounded text-gray-500 hover:text-white hover:bg-gray-600 transition-all flex-shrink-0"
        aria-label={`Menu for ${title}`}
      >
        <MoreVertical size={14} />
      </button>

      {showMenu && (
        <div
          ref={menuRef}
          className="absolute right-2 top-full mt-1 w-48 bg-gray-900 border border-gray-800 rounded-lg shadow-lg z-50 overflow-hidden"
        >
          <button
            onClick={(e) => handleMenuClick(e, onShare)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <Share size={16} className="text-gray-400" />
            <span>Share</span>
          </button>

          <button
            onClick={(e) => handleMenuClick(e, onStartGroupChat)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <Users size={16} className="text-gray-400" />
            <span>Start a group chat</span>
          </button>

          <button
            onClick={(e) => handleMenuClick(e, onRename)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <Edit2 size={16} className="text-gray-400" />
            <span>Rename</span>
          </button>

          <button
            onClick={(e) => handleMenuClick(e, onPinChat)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <Pin size={16} className="text-gray-400" />
            <span>{isPinned ? 'Unpin chat' : 'Pin chat'}</span>
          </button>

          <button
            onClick={(e) => handleMenuClick(e, onArchive)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
          >
            <Archive size={16} className="text-gray-400" />
            <span>Archive</span>
          </button>

          <div className="border-t border-gray-800" />

          <button
            onClick={(e) => handleMenuClick(e, onDelete)}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-gray-800 transition-colors"
          >
            <Trash2 size={16} />
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  )
}

export default RecentItem
