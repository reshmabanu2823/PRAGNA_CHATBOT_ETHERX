import { useContext, useState } from "react";
import { ChatContext } from "../../context/ChatContext";
import pragnaLogo from "../../assets/pragna-logo-full.png";

const isMobile = () =>
  typeof window !== "undefined" && window.innerWidth <= 768;

export default function Sidebar() {
  const {
    chats,
    setChats,
    activeChatId,
    setActiveChatId,
    newChat,
    sidebarOpen,
    toggleSidebar,
    deleteChat,
  } = useContext(ChatContext);

  const [editingId, setEditingId] = useState(null);
  const [tempTitle, setTempTitle] = useState("");

  const startEdit = (chat) => {
    setEditingId(chat.id);
    setTempTitle(chat.title);
  };

  const saveEdit = (chatId) => {
    if (!tempTitle.trim()) return;
    setChats((prev) =>
      prev.map((c) => (c.id === chatId ? { ...c, title: tempTitle } : c))
    );
    setEditingId(null);
  };

  const handleDelete = (e, chatId) => {
    e.stopPropagation();
    if (window.confirm("Delete this chat?")) {
      deleteChat(chatId);
    }
  };

  // Select a chat and close sidebar on mobile
  const handleSelectChat = (chatId) => {
    setActiveChatId(chatId);
    if (isMobile()) toggleSidebar();
  };

  // New chat and close sidebar on mobile
  const handleNewChat = () => {
    newChat();
    if (isMobile()) toggleSidebar();
  };

  if (!sidebarOpen) return null;

  return (
    <>
      {/* Dimming backdrop — only shown on mobile (CSS hides it on desktop) */}
      <div className="sidebar-overlay" onClick={toggleSidebar} />

      <div className="sidebar">
        <div className="sidebar-logo">
          <img src={pragnaLogo} alt="Pragna-1 A" className="sidebar-logo-full" />
        </div>

        <button className="new-chat-btn" onClick={handleNewChat}>
          + New Chat
        </button>

        <div className="chat-history">
          {chats.map((chat) => (
            <div
              key={chat.id}
              className={`chat-item ${chat.id === activeChatId ? "active" : ""}`}
              onClick={() => handleSelectChat(chat.id)}
            >
              {editingId === chat.id ? (
                <input
                  autoFocus
                  value={tempTitle}
                  onChange={(e) => setTempTitle(e.target.value)}
                  onBlur={() => saveEdit(chat.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveEdit(chat.id);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                />
              ) : (
                <>
                  <span onDoubleClick={() => startEdit(chat)}>
                    {chat.title}
                  </span>
                  <button
                    className="delete-chat-btn"
                    onClick={(e) => handleDelete(e, chat.id)}
                    title="Delete chat"
                  >
                    <svg
                      width="0.875em"
                      height="0.875em"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </>
              )}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <span className="sidebar-footer-made">Made in India</span>
          <span className="sidebar-footer-copy">© 2026 EtherX Innovations</span>
          <span className="sidebar-footer-copy">All rights reserved</span>
        </div>
      </div>
    </>
  );
}
