# Desktop Sidebar Close/Collapse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user hide the always-on desktop sidebar via a close button, reopen it via a floating button, with the open/closed state persisted across reloads.

**Architecture:** Wire the existing (currently dead-on-desktop) `sidebarOpen`/`toggleSidebar` state in `ChatContext.jsx` into `MainLayout.jsx`'s desktop sidebar rendering, add a close button to `Sidebar.jsx`'s header, and persist `sidebarOpen` to `localStorage` in place of the current no-op resize effect.

**Tech Stack:** React (function components + hooks), plain inline-style JSX (`Sidebar.jsx` convention) / Tailwind utility classes (`MainLayout.jsx` convention — follow whichever a given file already uses), `lucide-react` icons (`PanelLeft`, `PanelLeftClose`, already a dependency).

## Global Constraints

- No automated frontend test runner exists in this repo — verification is `npm run build` + `npm run lint` clean (checked against the current baseline — this repo has 27 pre-existing lint errors / 3 warnings unrelated to this work; the bar is "no new errors," not a fully clean run), plus manual exercise via `npm run dev`.
- Desktop only (`≥1024px`, the existing `isDesktop` breakpoint in `MainLayout.jsx`). Do not touch the mobile drawer (`mobileMenuOpen` local state) — it already works and is unaffected by this change.
- Run all commands from `chatbot-ui-vite/` (the frontend package root).
- Spec reference: `docs/superpowers/specs/2026-07-06-desktop-sidebar-close-design.md`.

---

### Task 1: Wire up persisted desktop sidebar close/reopen

**Files:**
- Modify: `chatbot-ui-vite/src/context/ChatContext.jsx:1-7` (remove unused `isMobile` helper), `:39-40` (persisted initializer), `:51-62` (replace resize effect with persistence effect)
- Modify: `chatbot-ui-vite/src/pragna/layouts/MainLayout.jsx:1-5` (imports), `:20-21` (consume context), `:25-41` (gate desktop sidebar on `sidebarOpen`), `:79-82` (add floating reopen button)
- Modify: `chatbot-ui-vite/src/pragna/components/Sidebar.jsx:2` (import), `:22` (consume `toggleSidebar`), `:300-303` (add close button to header)

**Interfaces:**
- Consumes: existing `sidebarOpen` (boolean) / `toggleSidebar()` already exposed on `ChatContext`'s provider value (unchanged names/shape — only the initializer and the effect that drives them change).
- Produces: no new exports — `sidebarOpen`/`toggleSidebar` keep their existing names and are now actually wired to visible behavior on desktop.

- [ ] **Step 1: Remove the unused `isMobile` helper from `ChatContext.jsx`**

Find this block (currently lines 1-7):

```jsx
import { createContext, useState, useEffect, useRef } from "react";
import { normalizeLanguageCode } from "../utils/language";

export const ChatContext = createContext();

const isMobile = () =>
  typeof window !== "undefined" && window.innerWidth <= 768;

export function ChatProvider({ children }) {
```

Replace it with:

```jsx
import { createContext, useState, useEffect, useRef } from "react";
import { normalizeLanguageCode } from "../utils/language";

export const ChatContext = createContext();

export function ChatProvider({ children }) {
```

- [ ] **Step 2: Make `sidebarOpen` read from `localStorage`**

Find this block (currently lines 39-40):

```jsx
  // Sidebar: closed by default on mobile, open on desktop
  const [sidebarOpen, setSidebarOpen] = useState(() => !isMobile());
```

Replace it with:

```jsx
  // Sidebar: open by default, persisted across reloads (desktop only — mobile uses its own drawer state)
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem("pragna_sidebar_open");
    return saved === null ? true : JSON.parse(saved);
  });
```

- [ ] **Step 3: Replace the resize effect with a persistence effect**

Find this block (currently lines 51-64, ending right before the chats-persistence effect):

```jsx
  // Close sidebar when window resizes to mobile, open when it grows to desktop
  useEffect(() => {
    const handleResize = () => {
      if (isMobile()) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem("pragna_chats", JSON.stringify(chats));
  }, [chats]);
```

Replace it with:

```jsx
  // Persist sidebar open/closed state
  useEffect(() => {
    localStorage.setItem("pragna_sidebar_open", JSON.stringify(sidebarOpen));
  }, [sidebarOpen]);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem("pragna_chats", JSON.stringify(chats));
  }, [chats]);
```

- [ ] **Step 4: Consume `sidebarOpen`/`toggleSidebar` in `MainLayout.jsx`**

Find this block (currently lines 1-5):

```jsx
import { useState } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { motion, AnimatePresence } from 'framer-motion'
```

Replace it with:

```jsx
import { useContext, useState } from 'react'
import { Menu, PanelLeft } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { ChatContext } from '../../context/ChatContext'
import { motion, AnimatePresence } from 'framer-motion'
```

Find this block (currently lines 20-21):

```jsx
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
```

Replace it with:

```jsx
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const { sidebarOpen, toggleSidebar } = useContext(ChatContext)
```

- [ ] **Step 5: Gate the desktop sidebar on `sidebarOpen`**

Find this block (currently lines 25-41):

```jsx
      {/* Desktop Sidebar */}
      {isDesktop && (
        <div style={{ width: '340px' }} className="flex-shrink-0">
          <Sidebar
            activeView={activeView}
            onViewChange={onViewChange}
            recentChats={recentChats}
            activeChatId={activeChatId}
            onSelectRecent={onSelectRecent}
            onDeleteRecent={onDeleteRecent}
            onNewChat={onNewChat}
            onLogout={onLogout}
            userProfile={userProfile}
            onOpenSettings={onOpenSettings}
          />
        </div>
      )}
```

Replace it with:

```jsx
      {/* Desktop Sidebar */}
      {isDesktop && sidebarOpen && (
        <div style={{ width: '340px' }} className="flex-shrink-0">
          <Sidebar
            activeView={activeView}
            onViewChange={onViewChange}
            recentChats={recentChats}
            activeChatId={activeChatId}
            onSelectRecent={onSelectRecent}
            onDeleteRecent={onDeleteRecent}
            onNewChat={onNewChat}
            onLogout={onLogout}
            userProfile={userProfile}
            onOpenSettings={onOpenSettings}
          />
        </div>
      )}
```

- [ ] **Step 6: Add the floating reopen button**

Find this block (currently lines 79-82):

```jsx
      {/* Main Content */}
      <div className="relative flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile Header */}
        {!isDesktop && (
```

Replace it with:

```jsx
      {/* Main Content */}
      <div className="relative flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Reopen sidebar button (desktop only, shown when sidebar is closed) */}
        {isDesktop && !sidebarOpen && (
          <button
            onClick={toggleSidebar}
            title="Open sidebar"
            className="fixed top-4 left-4 z-30 p-2 rounded-lg bg-surface/80 backdrop-blur-sm border border-border hover:bg-surface-subtle transition-colors"
          >
            <PanelLeft size={18} className="text-[var(--pragna-text-muted)]" />
          </button>
        )}

        {/* Mobile Header */}
        {!isDesktop && (
```

- [ ] **Step 7: Add the close button to `Sidebar.jsx`'s header**

Find this line (currently line 2):

```jsx
import { Folder, FolderPlus, MoreVertical, Edit2, Trash2 } from 'lucide-react'
```

Replace it with:

```jsx
import { Folder, FolderPlus, MoreVertical, Edit2, Trash2, PanelLeftClose } from 'lucide-react'
```

Find this line (currently line 22):

```jsx
  const { language, setLanguage, folders, createFolder, renameFolder, deleteFolder, moveChatToFolder } = useContext(ChatContext)
```

Replace it with:

```jsx
  const { language, setLanguage, folders, createFolder, renameFolder, deleteFolder, moveChatToFolder, toggleSidebar } = useContext(ChatContext)
```

Find this block (currently lines 300-303):

```jsx
      {/* Wordmark logo */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '20px 20px 16px 20px' }}>
        <img src={pragnaLogo} alt="Pragna I-A" style={{ height: '150px', width: '300px', objectFit: 'cover' }} />
      </div>
```

Replace it with:

```jsx
      {/* Wordmark logo */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 20px 16px 20px' }}>
        <img src={pragnaLogo} alt="Pragna I-A" style={{ height: '150px', width: '300px', objectFit: 'cover' }} />
        <button
          type="button"
          onClick={toggleSidebar}
          title="Close sidebar"
          style={{ padding: '6px', borderRadius: '8px', border: 'none', background: 'transparent', color: '#a89878', cursor: 'pointer', display: 'flex', flexShrink: 0 }}
          className="hover:bg-[#1a1a1a] hover:text-[#e5c76b]"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>
```

- [ ] **Step 8: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings beyond the pre-existing baseline (27 errors / 3 warnings, none in the three files touched here).

- [ ] **Step 9: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`, open the app in a desktop-width window (≥1024px). Click the close icon next to the logo — confirm the sidebar disappears and a small floating button appears at the top-left of the content area. Click that floating button — confirm the sidebar reappears and the floating button disappears. Close the sidebar again, reload the page — confirm it stays closed. Reopen it, reload again — confirm it stays open. Resize the window to mobile width and confirm the existing hamburger + slide-in drawer behavior is unaffected.

- [ ] **Step 10: Commit**

```bash
git add chatbot-ui-vite/src/context/ChatContext.jsx chatbot-ui-vite/src/pragna/layouts/MainLayout.jsx chatbot-ui-vite/src/pragna/components/Sidebar.jsx
git commit -m "feat: add close/reopen toggle for the desktop sidebar"
```
