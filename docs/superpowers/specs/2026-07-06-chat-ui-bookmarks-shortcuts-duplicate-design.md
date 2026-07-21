# Chat UI Feature Batch 2: Bookmarks, Keyboard Shortcuts, Duplicate Chat

**Status:** Approved
**Scope:** First of four sub-projects in the "add more features" initiative (order: Chat UI → Agent → Backend → RAG). This document covers Chat UI only.

## Goal

Add three independent, frontend-only features to the Pragna chat UI:
1. Message bookmarks (star/unstar any message).
2. Keyboard shortcuts (focus search, new chat, shortcuts help overlay).
3. Duplicate/branch an existing chat (full copy of title + message history).

## Architecture

All three features are frontend-only additions to `chatbot-ui-vite/`, following the exact conventions established in the prior chat-sidebar-features batch (see `2026-07-05-chat-sidebar-features-design.md`):
- State lives in `ChatContext.jsx`, persisted to `localStorage` via the existing `chats`/`folders` effect pattern.
- Plain inline-style JSX, matching `Sidebar.jsx` / `RecentItem.jsx` / `MessageBubble.jsx` conventions.
- `lucide-react` for icons where an existing icon fits; hand-rolled inline SVG (matching `MessageBubble.jsx`'s existing icon components) where it doesn't.
- No backend changes, no new network calls.
- One commit per feature, in order: bookmarks → keyboard shortcuts → duplicate chat.

## Feature A: Message bookmarks

**Data model:** add an optional `bookmarked: boolean` field to message objects (`{ sender, text, attachments?, bookmarked? }`). Old messages without the field are simply falsy/unbookmarked — no migration needed. Persists automatically via the existing `chats` → `localStorage` effect in `ChatContext.jsx`.

**Files:**
- `chatbot-ui-vite/src/components/chat/ChatWindow.jsx` — add `toggleBookmark(idx)`, same shape as the existing `editMessage`/`retryMessage` callbacks (around line 200): flips `messages[idx].bookmarked` via `setChats`, scoped to `activeChatId`. Wire `onToggleBookmark={() => toggleBookmark(idx)}` into every `MessageBubble` (both user and bot messages — no restriction on `idx` like the retry/edit props have).
- `chatbot-ui-vite/src/components/chat/MessageBubble.jsx`:
  - New `StarIcon` component (outline/filled variants via a `filled` prop, matching the existing `ThumbsUpIcon`/`ThumbsDownIcon` pattern at lines 10-18).
  - Accept new props `onToggleBookmark`, derive `bookmarked = !!message.bookmarked`.
  - User-message branch (line ~458): add a star button in the same hover-revealed row as the pencil icon. Unlike the pencil, the star stays visible (not `opacity-0 group-hover:opacity-100`) when `bookmarked` is true, so a starred message stays visibly marked while scrolling.
  - Bot-message branch (line ~613): add the star button into the existing action-icon row (copy/like/dislike/retry/voice), same `actionBtnBase` styling, filled gold (`text-accent-400`-equivalent) when bookmarked.

**Testing:** `npm run build && npm run lint` clean. Manual: star a user message and a bot message, reload the page, confirm both remain starred (localStorage persistence); unstar and confirm it clears.

## Feature B: Keyboard shortcuts

**Shortcuts:**
| Combo | Action |
|---|---|
| `Ctrl/Cmd+K` | Focus the sidebar search input (opens the sidebar first if closed, e.g. on mobile) |
| `Ctrl/Cmd+Shift+O` | Start a new chat |
| `Ctrl/Cmd+/` | Toggle a shortcuts help overlay |

**Why Shift+O instead of plain Ctrl+N:** Ctrl+N is intercepted by the browser chrome itself (opens a new browser window) and cannot be reliably `preventDefault()`-ed from page JS in Chrome/Firefox. Ctrl+Shift+O avoids that conflict and matches the convention other chat apps (e.g. ChatGPT) use for "new chat."

**Files:**
- `chatbot-ui-vite/src/context/ChatContext.jsx` — add `sidebarSearchInputRef` (a `useRef(null)`, same pattern as the existing `inputRef` at line 49), exposed on the context value.
- `chatbot-ui-vite/src/pragna/components/Sidebar.jsx` — attach `ref={sidebarSearchInputRef}` (pulled from `ChatContext`) to the existing search `<input>` (currently around line 330 per the search-filter feature).
- `chatbot-ui-vite/src/pragna/App.jsx` — add a `useEffect` with a single `document.addEventListener('keydown', ...)`:
  - Matches `(e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'k'` → `preventDefault()`, ensure `sidebarOpen` (call `toggleSidebar()` if closed), then `sidebarSearchInputRef.current?.focus()`.
  - Matches `(e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'o'` → `preventDefault()`, call the existing `handleNewChat()`.
  - Matches `(e.ctrlKey || e.metaKey) && e.key === '/'` → `preventDefault()`, toggle new `shortcutsHelpOpen` state.
  - Skip all three while `settingsOpen` is true (avoid double-modal weirdness).
- New file `chatbot-ui-vite/src/pragna/components/ShortcutsHelpModal.jsx` — a small overlay modal reusing `SettingsModal.jsx`'s chrome (`position:fixed, inset:0` backdrop with blur, centered panel: `background:#141414`, `border:1px solid rgba(212,175,55,0.2)`, `borderRadius:20px`), listing the three shortcuts above in a simple two-column list. Closes on `Escape`, backdrop click, or `Ctrl/Cmd+/` again.
- `pragna/App.jsx` renders `<ShortcutsHelpModal isOpen={shortcutsHelpOpen} onClose={() => setShortcutsHelpOpen(false)} />` alongside the existing `SettingsModal`.

**Testing:** `npm run build && npm run lint` clean. Manual: from various focus states (message input focused, nothing focused), confirm Ctrl+K focuses search (opening the sidebar on a narrow viewport first), Ctrl+Shift+O starts a new chat, Ctrl+/ opens and closes the help overlay, and Escape/backdrop-click also closes it.

## Feature C: Duplicate/branch chat

**Behavior:** clones a chat's title and full message history into a new, independent chat, and navigates to the copy so the user can branch off and continue differently from that point.

**Files:**
- `chatbot-ui-vite/src/context/ChatContext.jsx` — add `duplicateChat(chatId)`:
  ```js
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
  Exposed on the context value alongside `deleteChat`/`createFolder`/etc.
- `chatbot-ui-vite/src/pragna/components/RecentItem.jsx` — import `Copy` from `lucide-react`, accept a new `onDuplicate` prop, add a "Duplicate" menu button next to the existing "Export" button (same styling).
- `chatbot-ui-vite/src/pragna/components/Sidebar.jsx` — pull `duplicateChat` from `ChatContext`, add `handleDuplicate(chatId)` that calls `duplicateChat(chatId)` then `handleChangeView('chats')` (so the user lands on the chat view showing the new copy). Wire `onDuplicate={() => handleDuplicate(chat.id)}` into **both** `RecentItem` call sites (the folder-section loop and the unfiled/Recents loop — the folders feature introduced two render sites).

**Testing:** `npm run build && npm run lint` clean. Manual: duplicate a multi-message chat, confirm a new "<title> (copy)" chat appears with identical message history, is now the active/displayed chat, and editing/sending in the copy does not affect the original. Duplicate a chat that's inside a folder and confirm the copy lands in the same folder.

## Out of scope

- A dedicated "Bookmarks" panel/view (deferred per user's choice — bookmarks are visual-only for now).
- Additional shortcuts beyond the three above (send-message, escape-to-cancel-edit, etc.) — deferred per user's choice of the smaller shortcut set.
- Server-side duplication/sync — chats remain client-generated and `localStorage`-only, consistent with the rest of this app's chat storage model.
