# Chat UI Feature Batch 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add message bookmarks, keyboard shortcuts (search focus, new chat, shortcuts help), and duplicate/branch-chat to the Pragna chat UI.

**Architecture:** All three features are frontend-only additions to the existing React/Vite app (`chatbot-ui-vite/`), persisted via the same `localStorage`-backed `ChatContext` pattern already used for chats/folders/theme/language. No backend routes, no new `ChatManagementAPI` calls.

**Tech Stack:** React (function components + hooks), plain inline-style JSX (existing convention in `Sidebar.jsx`/`RecentItem.jsx`/`MessageBubble.jsx`), `lucide-react` for icons where an existing icon fits, hand-rolled inline SVG (matching `MessageBubble.jsx`'s existing icon components) otherwise.

## Global Constraints

- No automated frontend test runner exists in this repo (per `CLAUDE.md`) — verification is `npm run build` + `npm run lint` clean, plus manual exercise via `npm run dev`, not a failing-test-first cycle.
- All new features are frontend-only, `localStorage`-persisted (bookmarks/duplicates ride on the existing `chats` persistence; shortcuts have no persisted state). No backend changes, no new network calls.
- The **live** sidebar is `chatbot-ui-vite/src/pragna/components/Sidebar.jsx`. Do not touch `chatbot-ui-vite/src/components/layout/Sidebar.jsx` (confirmed unused).
- One commit per task, in this exact order: bookmarks → keyboard shortcuts → duplicate chat.
- Run all commands from `chatbot-ui-vite/` (the frontend package root), e.g. `cd chatbot-ui-vite && npm run build`.
- Spec reference: `docs/superpowers/specs/2026-07-06-chat-ui-bookmarks-shortcuts-duplicate-design.md`.

---

### Task 1: Message bookmarks

**Files:**
- Modify: `chatbot-ui-vite/src/components/chat/MessageBubble.jsx:26-30` (add `StarIcon`), `:319` (props), `:450-455` (derive `bookmarked`), `:517-544` (user-message render), `:613-658` (bot-message action row)
- Modify: `chatbot-ui-vite/src/components/chat/ChatWindow.jsx:199-211` (add `toggleBookmark`), `:441-449` (wire `onToggleBookmark` prop)

**Interfaces:**
- Consumes: existing `message` shape `{ sender, text, attachments?, bookmarked? }` (new optional field); existing `chat.messages` array from `ChatWindow.jsx`.
- Produces: `toggleBookmark(idx)` in `ChatWindow.jsx` (flips `messages[idx].bookmarked` via `setChats`, scoped to `activeChatId`); `MessageBubble` gains an `onToggleBookmark?: () => void` prop.

- [ ] **Step 1: Add `StarIcon` to `MessageBubble.jsx`**

Find this block (currently lines 26-30):

```jsx
const PencilIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z" />
  </svg>
);
```

Add immediately after it:

```jsx
const StarIcon = ({ filled }) => (
  <svg viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
);
```

- [ ] **Step 2: Accept `onToggleBookmark` prop and derive `bookmarked`**

Find this line (currently line 319):

```jsx
export default function MessageBubble({ message, language = "en", onRetry, onEdit, isLoading }) {
```

Replace it with:

```jsx
export default function MessageBubble({ message, language = "en", onRetry, onEdit, isLoading, onToggleBookmark }) {
```

Find this block (currently lines 450-455):

```jsx
  const isBot = message.sender === "bot";
  const isError = isBot && !!message.error;
  const isStreaming = message.isStreaming;
  const hasText = (message.text || "").trim().length > 0;
  const showTypingDots = isBot && isStreaming && !hasText && !isError;
  const hasAttachments = message.attachments && message.attachments.length > 0;
```

Replace it with:

```jsx
  const isBot = message.sender === "bot";
  const isError = isBot && !!message.error;
  const isStreaming = message.isStreaming;
  const hasText = (message.text || "").trim().length > 0;
  const showTypingDots = isBot && isStreaming && !hasText && !isError;
  const hasAttachments = message.attachments && message.attachments.length > 0;
  const bookmarked = !!message.bookmarked;
```

- [ ] **Step 3: Render the star button on user messages**

Find this block (currently lines 517-544):

```jsx
        ) : (
          <>
            <div
              className="max-w-[78%] rounded-[18px_18px_4px_18px] px-[18px] py-3 text-[15px] leading-[1.5] shadow-premium-md whitespace-pre-wrap break-words"
              style={{
                background: "linear-gradient(135deg, var(--pragna-gold-soft), var(--pragna-gold))",
                color: "var(--pragna-on-gold)",
                fontWeight: 550,
              }}
            >
              {hasAttachments && renderAttachments(message.attachments)}
              {message.text}
            </div>
            {onEdit && !isLoading && (
              <button
                type="button"
                onClick={() => {
                  setDraftText(message.text || "");
                  setIsEditing(true);
                }}
                title="Edit message"
                className={`${actionBtnBase} opacity-0 group-hover:opacity-100 text-[color:var(--pragna-text-muted)]`}
              >
                <PencilIcon />
              </button>
            )}
          </>
        )}
```

Replace it with:

```jsx
        ) : (
          <>
            <div
              className="max-w-[78%] rounded-[18px_18px_4px_18px] px-[18px] py-3 text-[15px] leading-[1.5] shadow-premium-md whitespace-pre-wrap break-words"
              style={{
                background: "linear-gradient(135deg, var(--pragna-gold-soft), var(--pragna-gold))",
                color: "var(--pragna-on-gold)",
                fontWeight: 550,
              }}
            >
              {hasAttachments && renderAttachments(message.attachments)}
              {message.text}
            </div>
            <div className={`flex gap-1 ${bookmarked ? "" : "opacity-0 group-hover:opacity-100"}`}>
              {onToggleBookmark && (
                <button
                  type="button"
                  onClick={onToggleBookmark}
                  title={bookmarked ? "Remove bookmark" : "Bookmark message"}
                  className={`${actionBtnBase} ${bookmarked ? "text-accent-400" : "text-[color:var(--pragna-text-muted)]"}`}
                >
                  <StarIcon filled={bookmarked} />
                </button>
              )}
              {onEdit && !isLoading && (
                <button
                  type="button"
                  onClick={() => {
                    setDraftText(message.text || "");
                    setIsEditing(true);
                  }}
                  title="Edit message"
                  className={`${actionBtnBase} opacity-0 group-hover:opacity-100 text-[color:var(--pragna-text-muted)]`}
                >
                  <PencilIcon />
                </button>
              )}
            </div>
          </>
        )}
```

(Note: the pencil button's own `opacity-0 group-hover:opacity-100` classes stay — only the star's visibility is gated separately by `bookmarked`, via the wrapping div.)

- [ ] **Step 4: Render the star button in the bot-message action row**

Find this block (currently lines 613-622):

```jsx
          {isBot && !isStreaming && !isError && (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={copyToClipboard}
                title="Copy"
                className={`${actionBtnBase} text-[color:var(--pragna-text-muted)]`}
              >
                <CopyIcon />
              </button>
```

Replace it with:

```jsx
          {isBot && !isStreaming && !isError && (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={copyToClipboard}
                title="Copy"
                className={`${actionBtnBase} text-[color:var(--pragna-text-muted)]`}
              >
                <CopyIcon />
              </button>
              {onToggleBookmark && (
                <button
                  type="button"
                  onClick={onToggleBookmark}
                  title={bookmarked ? "Remove bookmark" : "Bookmark message"}
                  className={`${actionBtnBase} ${bookmarked ? "text-accent-400" : "text-[color:var(--pragna-text-muted)]"}`}
                >
                  <StarIcon filled={bookmarked} />
                </button>
              )}
```

- [ ] **Step 5: Add `toggleBookmark` to `ChatWindow.jsx`**

Find this block (currently lines 199-211):

```jsx
  // Edit a previously sent user message: drop it and everything after it, then resend the new text
  const editMessage = useCallback((idx, newText) => {
    if (isLoading) return;
    const trimmed = (newText || "").trim();
    if (!trimmed) return;
    const targetChatId = activeChatId;
    setChats((prev) =>
      prev.map((c) =>
        c.id === targetChatId ? { ...c, messages: c.messages.slice(0, idx) } : c
      )
    );
    sendSuggestionMessage(trimmed);
  }, [activeChatId, isLoading, setChats, sendSuggestionMessage]);
```

Add immediately after it:

```jsx

  // Toggle the bookmarked flag on a single message, leaving everything else untouched
  const toggleBookmark = useCallback((idx) => {
    const targetChatId = activeChatId;
    setChats((prev) =>
      prev.map((c) =>
        c.id === targetChatId
          ? {
              ...c,
              messages: c.messages.map((m, i) =>
                i === idx ? { ...m, bookmarked: !m.bookmarked } : m
              ),
            }
          : c
      )
    );
  }, [activeChatId, setChats]);
```

- [ ] **Step 6: Wire `onToggleBookmark` into the message list**

Find this block (currently lines 441-449):

```jsx
          {chat.messages.map((m, idx) => (
            <MessageBubble
              key={idx}
              message={m}
              language={language}
              onRetry={idx === chat.messages.length - 1 ? () => retryMessage(idx) : undefined}
              onEdit={m.sender !== "bot" ? (newText) => editMessage(idx, newText) : undefined}
              isLoading={isLoading}
            />
```

Replace it with:

```jsx
          {chat.messages.map((m, idx) => (
            <MessageBubble
              key={idx}
              message={m}
              language={language}
              onRetry={idx === chat.messages.length - 1 ? () => retryMessage(idx) : undefined}
              onEdit={m.sender !== "bot" ? (newText) => editMessage(idx, newText) : undefined}
              isLoading={isLoading}
              onToggleBookmark={() => toggleBookmark(idx)}
            />
```

- [ ] **Step 7: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both commands exit cleanly with no errors.

- [ ] **Step 8: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`, open a chat with at least one user message and one bot response. Hover the user message and click the star icon (next to the pencil) — confirm it turns filled gold and stays visible even after the mouse moves away. Click it again to unstar — confirm it fades back to hover-only visibility. Do the same on the bot message's action row (star appears after the copy icon). Reload the page and confirm bookmarked state survives (persisted via `localStorage`).

- [ ] **Step 9: Commit**

```bash
git add chatbot-ui-vite/src/components/chat/ChatWindow.jsx chatbot-ui-vite/src/components/chat/MessageBubble.jsx
git commit -m "feat: add message bookmarks"
```

---

### Task 2: Keyboard shortcuts

**Files:**
- Modify: `chatbot-ui-vite/src/context/ChatContext.jsx:48-49` (add `sidebarSearchInputRef`), `:186-188` (expose on provider value)
- Modify: `chatbot-ui-vite/src/pragna/components/Sidebar.jsx:22` (consume ref), `:384-401` (attach ref to search input)
- Create: `chatbot-ui-vite/src/pragna/components/ShortcutsHelpModal.jsx`
- Modify: `chatbot-ui-vite/src/pragna/App.jsx:14` (import), `:35` (state), `:173-176` (add keydown effect after `handleNewChat`), `:278-283` (render modal)

**Interfaces:**
- Consumes: existing `handleNewChat()` and `sidebarOpen`/`toggleSidebar` from `ChatContext`.
- Produces: `sidebarSearchInputRef` (a `useRef(null)`) on the `ChatContext` value, attached to the sidebar's search `<input>`; a new `ShortcutsHelpModal` component taking `{ isOpen: boolean, onClose: () => void }`.

- [ ] **Step 1: Add `sidebarSearchInputRef` to `ChatContext.jsx`**

Find this block (currently lines 48-49):

```jsx
  // Ref to input field for focusing when mode is selected
  const inputRef = useRef(null);
```

Replace it with:

```jsx
  // Ref to input field for focusing when mode is selected
  const inputRef = useRef(null);

  // Ref to the sidebar's search input, focused via the Ctrl/Cmd+K shortcut
  const sidebarSearchInputRef = useRef(null);
```

- [ ] **Step 2: Expose the ref on the provider value**

Find this line (currently line 187, inside the `<ChatContext.Provider value={{ ... }}>` block):

```jsx
        inputRef,
```

Replace it with:

```jsx
        inputRef,
        sidebarSearchInputRef,
```

- [ ] **Step 3: Consume the ref and attach it to the search input in `Sidebar.jsx`**

Find this line (currently line 22):

```jsx
  const { language, setLanguage, folders, createFolder, renameFolder, deleteFolder, moveChatToFolder } = useContext(ChatContext)
```

Replace it with:

```jsx
  const { language, setLanguage, folders, createFolder, renameFolder, deleteFolder, moveChatToFolder, sidebarSearchInputRef } = useContext(ChatContext)
```

Find this block (currently lines 384-401):

```jsx
        <div style={{ padding: '0 10px 10px 10px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            style={{
              width: '100%',
              padding: '7px 12px',
              borderRadius: '8px',
              border: '1px solid #2d2a24',
              background: '#1a1a1a',
              color: '#f0e6d3',
              fontSize: '13px',
            }}
            className="focus-ring"
          />
        </div>
```

Replace it with:

```jsx
        <div style={{ padding: '0 10px 10px 10px' }}>
          <input
            ref={sidebarSearchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            style={{
              width: '100%',
              padding: '7px 12px',
              borderRadius: '8px',
              border: '1px solid #2d2a24',
              background: '#1a1a1a',
              color: '#f0e6d3',
              fontSize: '13px',
            }}
            className="focus-ring"
          />
        </div>
```

- [ ] **Step 4: Create `ShortcutsHelpModal.jsx`**

Create `chatbot-ui-vite/src/pragna/components/ShortcutsHelpModal.jsx`:

```jsx
import { useEffect } from 'react'

const SHORTCUTS = [
  { keys: 'Ctrl/Cmd + K', action: 'Focus chat search' },
  { keys: 'Ctrl/Cmd + Shift + O', action: 'Start a new chat' },
  { keys: 'Ctrl/Cmd + /', action: 'Show this shortcuts panel' },
]

const ShortcutsHelpModal = ({ isOpen, onClose }) => {
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
      <div onClick={onClose} style={{ position: 'absolute', inset: 0 }}></div>
      <div style={{ position: 'relative', width: 'min(420px, 90vw)', padding: '24px', borderRadius: '20px', background: '#141414', border: '1px solid rgba(212,175,55,0.2)', boxShadow: '0 20px 60px rgba(0,0,0,0.6)' }}>
        <div style={{ fontSize: '16px', fontWeight: 700, color: '#f0e6d3', marginBottom: '16px' }}>Keyboard shortcuts</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {SHORTCUTS.map((s) => (
            <div key={s.keys} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
              <span style={{ fontSize: '13px', color: '#d8cbb0' }}>{s.action}</span>
              <span style={{ fontSize: '12px', fontFamily: 'monospace', color: '#e5c76b', background: 'rgba(212,175,55,0.10)', border: '1px solid rgba(212,175,55,0.22)', borderRadius: '6px', padding: '3px 8px', whiteSpace: 'nowrap' }}>{s.keys}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ShortcutsHelpModal
```

- [ ] **Step 5: Wire the global keydown listener, state, and modal into `App.jsx`**

Find this line (currently line 14):

```jsx
import SettingsModal from './components/SettingsModal'
```

Replace it with:

```jsx
import SettingsModal from './components/SettingsModal'
import ShortcutsHelpModal from './components/ShortcutsHelpModal'
```

Find this line (currently line 35):

```jsx
  const [settingsOpen, setSettingsOpen] = useState(false)
```

Replace it with:

```jsx
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [shortcutsHelpOpen, setShortcutsHelpOpen] = useState(false)
```

Find this line (currently line 49, inside the `useContext(ChatContext)` destructure):

```jsx
    setChatMode,
  } = useContext(ChatContext)
```

Replace it with:

```jsx
    setChatMode,
    sidebarOpen,
    toggleSidebar,
    sidebarSearchInputRef,
  } = useContext(ChatContext)
```

Find this block (currently lines 173-176):

```jsx
  const handleNewChat = () => {
    newChat()
    setActiveView('chats')
  }
```

Add immediately after it:

```jsx

  // Global keyboard shortcuts: Ctrl/Cmd+K focus search, Ctrl/Cmd+Shift+O new chat, Ctrl/Cmd+/ toggle help
  useEffect(() => {
    const handleGlobalKeydown = (e) => {
      const mod = e.ctrlKey || e.metaKey
      if (!mod) return

      const key = e.key.toLowerCase()

      if (key === 'k' && !e.shiftKey) {
        if (settingsOpen || shortcutsHelpOpen) return
        e.preventDefault()
        if (!sidebarOpen) toggleSidebar()
        setTimeout(() => sidebarSearchInputRef.current?.focus(), 0)
      } else if (key === 'o' && e.shiftKey) {
        if (settingsOpen || shortcutsHelpOpen) return
        e.preventDefault()
        handleNewChat()
      } else if (e.key === '/') {
        if (settingsOpen) return
        e.preventDefault()
        setShortcutsHelpOpen((prev) => !prev)
      }
    }
    document.addEventListener('keydown', handleGlobalKeydown)
    return () => document.removeEventListener('keydown', handleGlobalKeydown)
  }, [settingsOpen, shortcutsHelpOpen, sidebarOpen, toggleSidebar, sidebarSearchInputRef])
```

Find this block (currently lines 278-283):

```jsx
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onLogout={onLogout}
        userProfile={userProfile}
      />
```

Replace it with:

```jsx
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onLogout={onLogout}
        userProfile={userProfile}
      />

      <ShortcutsHelpModal
        isOpen={shortcutsHelpOpen}
        onClose={() => setShortcutsHelpOpen(false)}
      />
```

- [ ] **Step 6: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both commands exit cleanly with no errors.

- [ ] **Step 7: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`. With nothing focused, press Ctrl+K (Cmd+K on Mac) — confirm the sidebar search input gets focus (and the sidebar opens first if you've resized the window narrow enough to auto-close it). Click into the message input, press Ctrl+Shift+O — confirm a new chat starts. Press Ctrl+/ — confirm the shortcuts overlay appears listing all three shortcuts; press Escape, confirm it closes; reopen with Ctrl+/, click the backdrop, confirm it closes; reopen and press Ctrl+/ again, confirm it toggles closed. Open Settings (via the sidebar) and confirm Ctrl+K/Ctrl+Shift+O do nothing while it's open.

- [ ] **Step 8: Commit**

```bash
git add chatbot-ui-vite/src/context/ChatContext.jsx chatbot-ui-vite/src/pragna/components/Sidebar.jsx chatbot-ui-vite/src/pragna/components/ShortcutsHelpModal.jsx chatbot-ui-vite/src/pragna/App.jsx
git commit -m "feat: add keyboard shortcuts for search, new chat, and a shortcuts help overlay"
```

---

### Task 3: Duplicate/branch chat

**Files:**
- Modify: `chatbot-ui-vite/src/context/ChatContext.jsx:154-158` (add `duplicateChat`), `:184` (expose on provider value)
- Modify: `chatbot-ui-vite/src/pragna/components/RecentItem.jsx:2` (import), `:4-19` (props), `:174-190` (menu button)
- Modify: `chatbot-ui-vite/src/pragna/components/Sidebar.jsx:22` (consume `duplicateChat`), `:121-148` (add `handleDuplicate` after `handleExport`), `:574-594` and `:650-669` (wire `onDuplicate` prop into both `RecentItem` call sites)

**Interfaces:**
- Consumes: `chats`/`setChats`/`setActiveChatId` already in `ChatContext.jsx`; existing `recentChats` prop shape `{ id, title, messages, folderId? }` in `Sidebar.jsx`.
- Produces: `duplicateChat(chatId)` in `ChatContext.jsx` (clones title+messages+folderId into a new chat, prepends it, and makes it active); `RecentItem` gains an `onDuplicate?: () => void` prop.

- [ ] **Step 1: Add `duplicateChat` to `ChatContext.jsx`**

Find this block (currently lines 154-158):

```jsx
  const moveChatToFolder = (chatId, folderId) => {
    setChats((prev) =>
      prev.map((c) => (c.id === chatId ? { ...c, folderId } : c))
    );
  };
```

Add immediately after it:

```jsx

  const duplicateChat = (chatId) => {
    const source = chats.find((c) => c.id === chatId);
    if (!source) return;
    const copy = {
      id: Date.now().toString(),
      title: `${source.title || "New chat"} (copy)`,
      messages: JSON.parse(JSON.stringify(source.messages || [])),
      folderId: source.folderId || null,
    };
    setChats((prev) => [copy, ...prev]);
    setActiveChatId(copy.id);
  };
```

- [ ] **Step 2: Expose `duplicateChat` on the provider value**

Find this line (currently line 184, inside the `<ChatContext.Provider value={{ ... }}>` block):

```jsx
        moveChatToFolder,
```

Replace it with:

```jsx
        moveChatToFolder,
        duplicateChat,
```

- [ ] **Step 3: Add the `Copy` icon import and `onDuplicate` prop in `RecentItem.jsx`**

Find this line (currently line 2):

```jsx
import { MoreVertical, Share, Users, Edit2, Pin, Archive, Trash2, Download, Folder } from 'lucide-react'
```

Replace it with:

```jsx
import { MoreVertical, Share, Users, Edit2, Pin, Archive, Trash2, Download, Folder, Copy } from 'lucide-react'
```

Find this block (currently lines 4-19):

```jsx
const RecentItem = ({
  id,
  title,
  onClick,
  onDelete,
  onRename,
  onShare,
  onExport,
  onPinChat,
  onArchive,
  onStartGroupChat,
  onMoveToFolder,
  folders = [],
  currentFolderId = null,
  active = false,
  isPinned = false
}) => {
```

Replace it with:

```jsx
const RecentItem = ({
  id,
  title,
  onClick,
  onDelete,
  onRename,
  onShare,
  onExport,
  onDuplicate,
  onPinChat,
  onArchive,
  onStartGroupChat,
  onMoveToFolder,
  folders = [],
  currentFolderId = null,
  active = false,
  isPinned = false
}) => {
```

- [ ] **Step 4: Add the Duplicate menu button**

Find this block (currently lines 174-190, the Export button):

```jsx
          <button
            onClick={(e) => handleMenuClick(e, onExport)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 10px',
              borderRadius: '7px',
              border: 'none',
              background: 'transparent',
              color: '#d8cbb0',
              fontSize: '13px',
              cursor: 'pointer',
              textAlign: 'left',
            }}
            className="hover:bg-[#1e1a10] hover:text-[#e5c76b]"
          >
            <Download size={14} />
            <span>Export</span>
          </button>
```

Add immediately after it:

```jsx

          <button
            onClick={(e) => handleMenuClick(e, onDuplicate)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 10px',
              borderRadius: '7px',
              border: 'none',
              background: 'transparent',
              color: '#d8cbb0',
              fontSize: '13px',
              cursor: 'pointer',
              textAlign: 'left',
            }}
            className="hover:bg-[#1e1a10] hover:text-[#e5c76b]"
          >
            <Copy size={14} />
            <span>Duplicate</span>
          </button>
```

- [ ] **Step 5: Add `handleDuplicate` to `Sidebar.jsx`**

Find this line (currently line 22, already updated by Task 2 to include `sidebarSearchInputRef`):

```jsx
  const { language, setLanguage, folders, createFolder, renameFolder, deleteFolder, moveChatToFolder, sidebarSearchInputRef } = useContext(ChatContext)
```

Replace it with:

```jsx
  const { language, setLanguage, folders, createFolder, renameFolder, deleteFolder, moveChatToFolder, sidebarSearchInputRef, duplicateChat } = useContext(ChatContext)
```

Find this block (currently lines 121-148, `handleExport`):

```jsx
  const handleExport = (chatId) => {
    const targetChat = recentChats.find((c) => c.id === chatId)
    if (!targetChat) return

    const title = targetChat.title || 'New chat'
    const lines = [`# ${title}`, '', `_Exported ${new Date().toISOString()}_`, '', '---', '']

    for (const msg of targetChat.messages || []) {
      const speaker = msg.sender === 'bot' ? 'Pragna' : 'You'
      lines.push(`**${speaker}:** ${msg.text || ''}`)
      if (msg.attachments?.length) {
        for (const att of msg.attachments) {
          lines.push(`_[attached: ${att.name}]_`)
        }
      }
      lines.push('')
    }

    const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.replace(/[^a-z0-9]+/gi, '-').toLowerCase() || 'chat'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
```

Add immediately after it:

```jsx

  const handleDuplicate = (chatId) => {
    duplicateChat(chatId)
    handleChangeView('chats')
  }
```

- [ ] **Step 6: Wire `onDuplicate` into both `RecentItem` call sites**

Find this block (currently lines 574-594, inside the folder-section loop):

```jsx
                    <RecentItem
                      key={chat.id}
                      id={chat.id}
                      title={chat.title || 'New chat'}
                      active={chat.id === activeChatId}
                      isPinned={pinnedChats.has(chat.id)}
                      folders={folders}
                      currentFolderId={chat.folderId || null}
                      onMoveToFolder={(folderId) => moveChatToFolder(chat.id, folderId)}
                      onClick={() => {
                        onSelectRecent(chat.id)
                        handleChangeView('chats')
                      }}
                      onDelete={() => handleDelete(chat.id)}
                      onRename={() => handleRename(chat.id, chat.title || 'New chat')}
                      onShare={() => handleShare(chat.id)}
                      onExport={() => handleExport(chat.id)}
                      onPinChat={() => handlePinChat(chat.id)}
                      onArchive={() => handleArchive(chat.id)}
                      onStartGroupChat={() => handleStartGroupChat(chat.id)}
                    />
```

Replace it with:

```jsx
                    <RecentItem
                      key={chat.id}
                      id={chat.id}
                      title={chat.title || 'New chat'}
                      active={chat.id === activeChatId}
                      isPinned={pinnedChats.has(chat.id)}
                      folders={folders}
                      currentFolderId={chat.folderId || null}
                      onMoveToFolder={(folderId) => moveChatToFolder(chat.id, folderId)}
                      onClick={() => {
                        onSelectRecent(chat.id)
                        handleChangeView('chats')
                      }}
                      onDelete={() => handleDelete(chat.id)}
                      onRename={() => handleRename(chat.id, chat.title || 'New chat')}
                      onShare={() => handleShare(chat.id)}
                      onExport={() => handleExport(chat.id)}
                      onDuplicate={() => handleDuplicate(chat.id)}
                      onPinChat={() => handlePinChat(chat.id)}
                      onArchive={() => handleArchive(chat.id)}
                      onStartGroupChat={() => handleStartGroupChat(chat.id)}
                    />
```

Then find this block (currently lines 650-669, inside the unfiled-chats loop):

```jsx
                <RecentItem
                  key={chat.id}
                  id={chat.id}
                  title={chat.title || 'New chat'}
                  active={chat.id === activeChatId}
                  isPinned={pinnedChats.has(chat.id)}
                  folders={folders}
                  currentFolderId={null}
                  onMoveToFolder={(folderId) => moveChatToFolder(chat.id, folderId)}
                  onClick={() => {
                    onSelectRecent(chat.id)
                    handleChangeView('chats')
                  }}
                  onDelete={() => handleDelete(chat.id)}
                  onRename={() => handleRename(chat.id, chat.title || 'New chat')}
                  onShare={() => handleShare(chat.id)}
                  onExport={() => handleExport(chat.id)}
                  onPinChat={() => handlePinChat(chat.id)}
                  onArchive={() => handleArchive(chat.id)}
                  onStartGroupChat={() => handleStartGroupChat(chat.id)}
```

Replace it with:

```jsx
                <RecentItem
                  key={chat.id}
                  id={chat.id}
                  title={chat.title || 'New chat'}
                  active={chat.id === activeChatId}
                  isPinned={pinnedChats.has(chat.id)}
                  folders={folders}
                  currentFolderId={null}
                  onMoveToFolder={(folderId) => moveChatToFolder(chat.id, folderId)}
                  onClick={() => {
                    onSelectRecent(chat.id)
                    handleChangeView('chats')
                  }}
                  onDelete={() => handleDelete(chat.id)}
                  onRename={() => handleRename(chat.id, chat.title || 'New chat')}
                  onShare={() => handleShare(chat.id)}
                  onExport={() => handleExport(chat.id)}
                  onDuplicate={() => handleDuplicate(chat.id)}
                  onPinChat={() => handlePinChat(chat.id)}
                  onArchive={() => handleArchive(chat.id)}
                  onStartGroupChat={() => handleStartGroupChat(chat.id)}
```

(Leave the rest of that call site, including its closing `/>` a few lines further down, untouched.)

- [ ] **Step 7: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both commands exit cleanly with no errors.

- [ ] **Step 8: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`, open a chat with 2+ messages, open its row menu, click "Duplicate" — confirm a new "<title> (copy)" chat appears at the top of Recents, is now the active chat, and shows the identical message history. Send a new message in the copy and confirm the original chat's history is unaffected. Repeat with a chat that's inside a folder and confirm the copy lands in the same folder.

- [ ] **Step 9: Commit**

```bash
git add chatbot-ui-vite/src/context/ChatContext.jsx chatbot-ui-vite/src/pragna/components/RecentItem.jsx chatbot-ui-vite/src/pragna/components/Sidebar.jsx
git commit -m "feat: add duplicate/branch chat"
```
