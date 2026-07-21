# Feature Batch 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add RAG scheduler status view, a model profile picker, PDF export, RAG source citations, and global message-content search to the Pragna chat UI.

**Architecture:** All five features are frontend additions that reuse existing, already-working backend endpoints (`/api/rag/scheduler/*`, `/api/models/catalog`) and existing data already present on message objects (`sources`). No new backend routes, no new dependencies.

**Tech Stack:** React (function components + hooks), Tailwind utility classes (`GlobalDashboard.jsx` convention) / plain inline-style JSX (`Sidebar.jsx`/`RecentItem.jsx`/`SettingsModal.jsx`/`MessageBubble.jsx` convention — follow whichever a given file already uses), `lucide-react` icons where a fitting one exists.

## Global Constraints

- No automated frontend test runner exists in this repo — verification is `npm run build` + `npm run lint` clean, checked against the current baseline (this repo has 27 pre-existing lint errors / 3 warnings in unrelated files — the bar is "no new errors/warnings," not a fully clean run).
- No new npm dependencies for any of these five features (PDF export uses the browser's native print dialog, not a PDF library).
- Task order is **largest to smallest**: scheduler view → model picker → PDF export → citations → message search. One commit per task.
- Run all commands from `chatbot-ui-vite/` (the frontend package root).
- Spec reference: `docs/superpowers/specs/2026-07-08-backend-surface-features-design.md`.

---

### Task 1: RAG scheduler status view

**Files:**
- Modify: `chatbot-ui-vite/src/api/api.js:1-7` (imports unaffected), `:193-199` (add 4 new exports after `getWorldMonitorConfig`)
- Modify: `chatbot-ui-vite/src/components/dashboard/GlobalDashboard.jsx:1-7` (imports), `:28-30` (state), `:49-61` (refresh + new handlers), `:171-182` (render section)

**Interfaces:**
- Consumes: existing `refresh()` cycle and `loading`/`error` state patterns already in `GlobalDashboard.jsx`.
- Produces: `getRagSchedulerStatus()`, `forceRagUpdate()`, `enableRagScheduler()`, `disableRagScheduler()` exports in `api.js`, each returning the parsed JSON body (no wrapping).

- [ ] **Step 1: Add the four API functions to `api.js`**

Find this block (currently lines 193-199):

```jsx
export const getWorldMonitorConfig = async () => {
  const response = await fetch("/api/world-monitor/config");
  if (!response.ok) {
    throw new Error("Failed to fetch World Monitor configuration.");
  }
  return response.json();
};
```

Add immediately after it:

```jsx

export const getRagSchedulerStatus = async () => {
  const response = await fetch("/api/rag/scheduler/status");
  if (!response.ok) {
    throw new Error("Failed to fetch RAG scheduler status.");
  }
  return response.json();
};

export const forceRagUpdate = async () => {
  const response = await fetch("/api/rag/scheduler/force_update", { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to force RAG update.");
  }
  return response.json();
};

export const enableRagScheduler = async () => {
  const response = await fetch("/api/rag/scheduler/enable", { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to enable RAG scheduler.");
  }
  return response.json();
};

export const disableRagScheduler = async () => {
  const response = await fetch("/api/rag/scheduler/disable", { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to disable RAG scheduler.");
  }
  return response.json();
};
```

- [ ] **Step 2: Import the new functions and add state in `GlobalDashboard.jsx`**

Find this block (currently lines 1-7):

```jsx
import { useEffect, useMemo, useState } from "react";
import {
  getDashboardGeoSummary,
  getPlatformStatus,
  getRealtimeEventsFeed,
  getWorldMonitorConfig,
} from "../../api/api";
```

Replace it with:

```jsx
import { useEffect, useMemo, useState } from "react";
import {
  getDashboardGeoSummary,
  getPlatformStatus,
  getRealtimeEventsFeed,
  getWorldMonitorConfig,
  getRagSchedulerStatus,
  forceRagUpdate,
  enableRagScheduler,
  disableRagScheduler,
} from "../../api/api";
```

Find this line (currently line 30):

```jsx
  const [search, setSearch] = useState("");
```

Replace it with:

```jsx
  const [search, setSearch] = useState("");
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [schedulerActionLoading, setSchedulerActionLoading] = useState(false);
```

- [ ] **Step 3: Fetch scheduler status in `refresh()` and add the two action handlers**

Find this block (currently lines 49-61):

```jsx
      try {
        const worldMonitorConfig = await getWorldMonitorConfig();
        setWorldMonitor(worldMonitorConfig?.world_monitor || null);
      } catch (wmErr) {
        console.warn("World Monitor config unavailable:", wmErr);
      }
    } catch (err) {
      console.error("Failed to load global dashboard:", err);
      setError("Unable to load realtime intelligence.");
    } finally {
      setLoading(false);
    }
  };
```

Replace it with:

```jsx
      try {
        const worldMonitorConfig = await getWorldMonitorConfig();
        setWorldMonitor(worldMonitorConfig?.world_monitor || null);
      } catch (wmErr) {
        console.warn("World Monitor config unavailable:", wmErr);
      }

      try {
        const schedulerData = await getRagSchedulerStatus();
        setSchedulerStatus(schedulerData?.scheduler || null);
      } catch (schedErr) {
        console.warn("RAG scheduler status unavailable:", schedErr);
      }
    } catch (err) {
      console.error("Failed to load global dashboard:", err);
      setError("Unable to load realtime intelligence.");
    } finally {
      setLoading(false);
    }
  };

  const handleForceUpdate = async () => {
    setSchedulerActionLoading(true);
    try {
      await forceRagUpdate();
      await refresh();
    } catch (err) {
      console.error("Failed to force RAG update:", err);
    } finally {
      setSchedulerActionLoading(false);
    }
  };

  const handleToggleScheduler = async () => {
    setSchedulerActionLoading(true);
    try {
      if (schedulerStatus?.enabled) {
        await disableRagScheduler();
      } else {
        await enableRagScheduler();
      }
      await refresh();
    } catch (err) {
      console.error("Failed to toggle RAG scheduler:", err);
    } finally {
      setSchedulerActionLoading(false);
    }
  };
```

- [ ] **Step 4: Render the scheduler status section**

Find this block (currently lines 171-182):

```jsx
      {platformPills.length > 0 ? (
        <div className="mb-5 flex flex-wrap gap-2.5">
          {platformPills.map((pill) => (
            <div
              key={pill}
              className="rounded-full border border-border bg-surface-subtle px-3.5 py-1.5 text-xs text-[color:var(--pragna-text-muted)]"
            >
              {pill}
            </div>
          ))}
        </div>
      ) : null}
```

Add immediately after it:

```jsx

      {schedulerStatus ? (
        <div className="glass-card mb-5 rounded-2xl px-5 py-4.5 shadow-premium-sm">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="m-0 text-sm font-bold text-[color:var(--pragna-text)]">RAG Scheduler</h2>
            <div className="flex gap-2">
              <button
                onClick={handleForceUpdate}
                disabled={schedulerActionLoading}
                className="rounded-lg border border-accent-500/35 bg-accent-500/10 px-3 py-1.5 text-xs font-semibold text-[color:var(--pragna-text)] transition-colors hover:bg-accent-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Force update now
              </button>
              <button
                onClick={handleToggleScheduler}
                disabled={schedulerActionLoading}
                className="rounded-lg border border-border bg-surface-subtle px-3 py-1.5 text-xs font-semibold text-[color:var(--pragna-text-muted)] transition-colors hover:bg-black/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {schedulerStatus.enabled ? "Disable" : "Enable"}
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs text-[color:var(--pragna-text-muted)] md:grid-cols-4">
            <div>
              <div className="mb-1 text-[color:var(--pragna-text)] font-semibold">Last update</div>
              {schedulerStatus.last_update ? new Date(schedulerStatus.last_update).toLocaleString() : "Never"}
            </div>
            <div>
              <div className="mb-1 text-[color:var(--pragna-text)] font-semibold">Update count</div>
              {schedulerStatus.update_count}
            </div>
            <div>
              <div className="mb-1 text-[color:var(--pragna-text)] font-semibold">Errors</div>
              {schedulerStatus.update_errors}
            </div>
            <div>
              <div className="mb-1 text-[color:var(--pragna-text)] font-semibold">Next update</div>
              {typeof schedulerStatus.next_update_in_hours === "number" ? `${schedulerStatus.next_update_in_hours}h` : schedulerStatus.next_update_in_hours}
            </div>
          </div>
        </div>
      ) : null}
```

- [ ] **Step 5: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings beyond the pre-existing baseline.

- [ ] **Step 6: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev` with the backend running (`python app.py` from `backend/`), navigate to the "Projects" nav item (GlobalDashboard). Confirm a "RAG Scheduler" card appears showing last update/update count/errors/next update. Click "Force update now" and confirm the card refreshes (update count changes or a network request fires without error). Click "Enable"/"Disable" and confirm the button label flips and the request succeeds (check Network tab for a 200 from `/api/rag/scheduler/enable` or `/disable`).

- [ ] **Step 7: Commit**

```bash
git add chatbot-ui-vite/src/api/api.js chatbot-ui-vite/src/components/dashboard/GlobalDashboard.jsx
git commit -m "feat: add RAG scheduler status view to the global dashboard"
```

---

### Task 2: Model picker (Settings)

**Files:**
- Modify: `chatbot-ui-vite/src/api/api.js` (add `getModelsCatalog`, right after Task 1's `disableRagScheduler`)
- Modify: `chatbot-ui-vite/src/pragna/components/SettingsModal.jsx:1-2` (imports), state block (add 3 new `useState`), Escape-key `useEffect` block (add catalog-fetch effect + handler), `tabs` array, Usage-tab-end/Capabilities-tab-start boundary (add new tab content)

**Interfaces:**
- Consumes: Task 1's `api.js` additions are unrelated; this task adds its own `getModelsCatalog()` export following the same fetch-and-return-json pattern.
- Produces: `getModelsCatalog()` in `api.js`, returning `{ status, default_model_key, fallback_models, recommendations, models }`. No other task depends on this.

- [ ] **Step 1: Add `getModelsCatalog` to `api.js`**

Find this block (added by Task 1; if Task 1 has not run yet in your working copy, find the original `getWorldMonitorConfig` block instead and add this after it):

```jsx
export const disableRagScheduler = async () => {
  const response = await fetch("/api/rag/scheduler/disable", { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to disable RAG scheduler.");
  }
  return response.json();
};
```

Add immediately after it:

```jsx

export const getModelsCatalog = async () => {
  const response = await fetch("/api/models/catalog");
  if (!response.ok) {
    throw new Error("Failed to fetch models catalog.");
  }
  return response.json();
};
```

- [ ] **Step 2: Import `getModelsCatalog` in `SettingsModal.jsx`**

Find this block (currently lines 1-2):

```jsx
import { useState, useEffect, useContext } from 'react'
import { ChatContext } from '../../context/ChatContext'
```

Replace it with:

```jsx
import { useState, useEffect, useContext } from 'react'
import { ChatContext } from '../../context/ChatContext'
import { getModelsCatalog } from '../../api/api'
```

- [ ] **Step 3: Add model-picker state**

Find this line:

```jsx
  const [toolAccessMode, setToolAccessMode] = useState('Load tools when needed')
```

Replace it with:

```jsx
  const [toolAccessMode, setToolAccessMode] = useState('Load tools when needed')
  const [modelProfile, setModelProfile] = useState(() => localStorage.getItem('pragna_model_profile') || 'basic')
  const [modelCatalog, setModelCatalog] = useState(null)
  const [modelCatalogLoading, setModelCatalogLoading] = useState(false)
```

- [ ] **Step 4: Fetch the catalog when the Model tab opens, and add the profile-change handler**

Find this block:

```jsx
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  if (!isOpen) return null
```

Replace it with:

```jsx
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  useEffect(() => {
    if (!isOpen || activeTab !== 'Model' || modelCatalog) return
    setModelCatalogLoading(true)
    getModelsCatalog()
      .then((data) => setModelCatalog(data))
      .catch((err) => console.warn('Models catalog unavailable:', err))
      .finally(() => setModelCatalogLoading(false))
  }, [isOpen, activeTab, modelCatalog])

  const handleModelProfileChange = (profile) => {
    setModelProfile(profile)
    localStorage.setItem('pragna_model_profile', profile)
  }

  if (!isOpen) return null
```

- [ ] **Step 5: Add the "Model" tab to the tab list**

Find this block:

```jsx
  const tabs = [
    { label: 'General', icon: 'gear' },
    { label: 'Account', icon: 'account' },
    { label: 'Privacy', icon: 'shield' },
    { label: 'Billing', icon: 'card' },
    { label: 'Usage', icon: 'chart' },
    { label: 'Capabilities', icon: 'puzzle' },
    { label: 'Connectors', icon: 'puzzle' },
    { label: 'Pragna Code', icon: 'code' },
  ]
```

Replace it with:

```jsx
  const tabs = [
    { label: 'General', icon: 'gear' },
    { label: 'Account', icon: 'account' },
    { label: 'Privacy', icon: 'shield' },
    { label: 'Billing', icon: 'card' },
    { label: 'Usage', icon: 'chart' },
    { label: 'Model', icon: 'puzzle' },
    { label: 'Capabilities', icon: 'puzzle' },
    { label: 'Connectors', icon: 'puzzle' },
    { label: 'Pragna Code', icon: 'code' },
  ]
```

- [ ] **Step 6: Add the Model tab content**

Find this block (the end of the Usage tab, immediately followed by the Capabilities tab):

```jsx
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '20px' }}>
                <div style={{ fontSize: '13px', color: '#a89878', maxWidth: '460px', lineHeight: 1.5 }}>Turn on usage credits to keep using Pragna if you hit a limit.</div>
                <button
                  onClick={() => setUsageCredits(!usageCredits)}
                  style={{ width: '42px', height: '24px', borderRadius: '999px', border: 'none', background: usageCredits ? '#d4af37' : '#2d2a24', cursor: 'pointer', flexShrink: 0, position: 'relative', padding: 0 }}
                >
                  <span style={{ position: 'absolute', top: '2px', left: usageCredits ? '20px' : '2px', width: '20px', height: '20px', borderRadius: '50%', background: '#fff', transition: 'left 0.15s ease' }}></span>
                </button>
              </div>
            </div>
          )}

          {/* CAPABILITIES TAB */}
          {activeTab === 'Capabilities' && (
```

Replace it with:

```jsx
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '20px' }}>
                <div style={{ fontSize: '13px', color: '#a89878', maxWidth: '460px', lineHeight: 1.5 }}>Turn on usage credits to keep using Pragna if you hit a limit.</div>
                <button
                  onClick={() => setUsageCredits(!usageCredits)}
                  style={{ width: '42px', height: '24px', borderRadius: '999px', border: 'none', background: usageCredits ? '#d4af37' : '#2d2a24', cursor: 'pointer', flexShrink: 0, position: 'relative', padding: 0 }}
                >
                  <span style={{ position: 'absolute', top: '2px', left: usageCredits ? '20px' : '2px', width: '20px', height: '20px', borderRadius: '50%', background: '#fff', transition: 'left 0.15s ease' }}></span>
                </button>
              </div>
            </div>
          )}

          {/* MODEL TAB */}
          {activeTab === 'Model' && (
            <div style={{ animation: 'fadeUp 0.15s ease' }}>
              <h2 style={{ margin: '0 0 8px 0', fontSize: '20px', fontWeight: 700, color: '#f0e6d3' }}>Model</h2>
              <p style={{ margin: '0 0 26px 0', fontSize: '13.5px', color: '#a89878', lineHeight: 1.6 }}>Choose how much model power Pragna uses for new messages.</p>

              <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '22px' }}>
                <div style={{ fontSize: '13px', color: '#a89878', width: '110px', flexShrink: 0 }}>Profile</div>
                <div style={{ display: 'flex', gap: '4px', padding: '4px', borderRadius: '11px', background: '#1a1a1a', border: '1px solid #2d2a24' }}>
                  {['basic', 'pro'].map((profile) => {
                    const active = modelProfile === profile
                    return (
                      <button
                        key={profile}
                        onClick={() => handleModelProfileChange(profile)}
                        style={{
                          padding: '8px 18px',
                          borderRadius: '8px',
                          border: 'none',
                          background: active ? 'rgba(212,175,55,0.18)' : 'transparent',
                          color: active ? '#e5c76b' : '#a89878',
                          fontSize: '13px',
                          fontWeight: active ? 650 : 500,
                          cursor: 'pointer',
                          textTransform: 'capitalize',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {profile}
                      </button>
                    )
                  })}
                </div>
              </div>

              {modelCatalogLoading && (
                <div style={{ fontSize: '13px', color: '#a89878' }}>Loading model catalog…</div>
              )}

              {modelCatalog && (
                <>
                  <div style={{ height: '1px', background: '#2d2a24', margin: '22px 0' }}></div>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 700, color: '#f0e6d3' }}>Server default</h3>
                  <div style={{ fontSize: '13px', color: '#d8cbb0', marginBottom: '18px' }}>{modelCatalog.default_model_key}</div>

                  <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 700, color: '#f0e6d3' }}>Available models</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {(modelCatalog.models || []).map((model) => (
                      <div
                        key={model.key || model.name || JSON.stringify(model)}
                        style={{ padding: '10px 14px', borderRadius: '10px', border: '1px solid #2d2a24', background: '#1a1a1a', fontSize: '13px', color: '#d8cbb0' }}
                      >
                        {model.key || model.name || JSON.stringify(model)}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* CAPABILITIES TAB */}
          {activeTab === 'Capabilities' && (
```

- [ ] **Step 7: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings beyond the pre-existing baseline.

- [ ] **Step 8: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev` with the backend running, open Settings, click the new "Model" tab. Confirm it fetches and shows "Server default" and an "Available models" list. Click "pro" — confirm it becomes highlighted and `localStorage.pragna_model_profile` is set to `"pro"` (check via DevTools). Send a chat message and confirm (via the Network tab, on the `/api/orchestrator/query` request body) that `model_override` now reflects the pro profile's model instead of basic's.

- [ ] **Step 9: Commit**

```bash
git add chatbot-ui-vite/src/api/api.js chatbot-ui-vite/src/pragna/components/SettingsModal.jsx
git commit -m "feat: add model profile picker to Settings"
```

---

### Task 3: PDF export

**Files:**
- Modify: `chatbot-ui-vite/src/pragna/components/RecentItem.jsx:2` (import), `:4-21` (props), `:175-196` (menu button, right after Export)
- Modify: `chatbot-ui-vite/src/pragna/components/Sidebar.jsx` (add `handlePdfExport` after `handleExport`), two `RecentItem` call sites (folder-section loop at 22-space indent, unfiled loop at 18-space indent)

**Interfaces:**
- Consumes: `recentChats` (array of `{ id, title, messages }`) already available in `Sidebar.jsx`, same shape `handleExport` already uses.
- Produces: `handlePdfExport(chatId)` in `Sidebar.jsx` (opens a print-styled window and triggers `window.print()`); `RecentItem` gains an `onPdfExport?: () => void` prop.

- [ ] **Step 1: Add the `Printer` icon import in `RecentItem.jsx`**

Find this line (currently line 2):

```jsx
import { MoreVertical, Share, Users, Edit2, Pin, Archive, Trash2, Download, Folder, Copy } from 'lucide-react'
```

Replace it with:

```jsx
import { MoreVertical, Share, Users, Edit2, Pin, Archive, Trash2, Download, Folder, Copy, Printer } from 'lucide-react'
```

- [ ] **Step 2: Accept an `onPdfExport` prop**

Find this block (currently lines 4-21):

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
  onPdfExport,
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

- [ ] **Step 3: Add the "Export as PDF" menu button**

Find this block (currently lines 175-198, the Export button followed by the start of the Duplicate button):

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

          <button
            onClick={(e) => handleMenuClick(e, onDuplicate)}
```

Replace it with:

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

          <button
            onClick={(e) => handleMenuClick(e, onPdfExport)}
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
            <Printer size={14} />
            <span>Export as PDF</span>
          </button>

          <button
            onClick={(e) => handleMenuClick(e, onDuplicate)}
```

- [ ] **Step 4: Add `handlePdfExport` to `Sidebar.jsx`**

Find this block (`handleExport` followed by the start of `handleDuplicate`):

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

  const handleDuplicate = (chatId) => {
```

Replace it with:

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

  const handlePdfExport = (chatId) => {
    const targetChat = recentChats.find((c) => c.id === chatId)
    if (!targetChat) return

    const title = targetChat.title || 'New chat'
    const escapeHtml = (str) =>
      (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

    const turns = (targetChat.messages || [])
      .map((msg) => {
        const speaker = msg.sender === 'bot' ? 'Pragna' : 'You'
        let html = `<p><strong>${speaker}:</strong> ${escapeHtml(msg.text)}</p>`
        if (msg.attachments?.length) {
          for (const att of msg.attachments) {
            html += `<p><em>[attached: ${escapeHtml(att.name)}]</em></p>`
          }
        }
        return html
      })
      .join('\n')

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>${escapeHtml(title)}</title>
<style>
  body { font-family: Georgia, serif; max-width: 720px; margin: 40px auto; color: #1a1a1a; }
  h1 { font-size: 22px; }
  .meta { color: #666; font-size: 13px; margin-bottom: 24px; }
  hr { border: none; border-top: 1px solid #ccc; margin: 24px 0; }
  p { line-height: 1.6; }
</style>
</head>
<body>
<h1>${escapeHtml(title)}</h1>
<div class="meta">Exported ${new Date().toISOString()}</div>
<hr>
${turns}
</body>
</html>`

    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    printWindow.document.write(html)
    printWindow.document.close()
    printWindow.onload = () => printWindow.print()
  }

  const handleDuplicate = (chatId) => {
```

- [ ] **Step 5: Wire `onPdfExport` into the folder-section `RecentItem` call site**

Find this block (22-space indent, inside the folder-section loop):

```jsx
                      onShare={() => handleShare(chat.id)}
                      onExport={() => handleExport(chat.id)}
                      onDuplicate={() => handleDuplicate(chat.id)}
```

Replace it with:

```jsx
                      onShare={() => handleShare(chat.id)}
                      onExport={() => handleExport(chat.id)}
                      onPdfExport={() => handlePdfExport(chat.id)}
                      onDuplicate={() => handleDuplicate(chat.id)}
```

- [ ] **Step 6: Wire `onPdfExport` into the unfiled-chats `RecentItem` call site**

Find this block (18-space indent, inside the unfiled-chats loop):

```jsx
                  onShare={() => handleShare(chat.id)}
                  onExport={() => handleExport(chat.id)}
                  onDuplicate={() => handleDuplicate(chat.id)}
```

Replace it with:

```jsx
                  onShare={() => handleShare(chat.id)}
                  onExport={() => handleExport(chat.id)}
                  onPdfExport={() => handlePdfExport(chat.id)}
                  onDuplicate={() => handleDuplicate(chat.id)}
```

- [ ] **Step 7: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings beyond the pre-existing baseline.

- [ ] **Step 8: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`, open a chat with a few messages, open its row menu, click "Export as PDF". Confirm a new tab/window opens showing a styled, print-ready page with the chat title, timestamp, and turns, and that the browser's print dialog appears (a `window.print()` call). Cancel the print dialog and confirm the new tab still shows the correct content (nothing crashed).

- [ ] **Step 9: Commit**

```bash
git add chatbot-ui-vite/src/pragna/components/RecentItem.jsx chatbot-ui-vite/src/pragna/components/Sidebar.jsx
git commit -m "feat: add PDF export via browser print"
```

---

### Task 4: RAG citations

**Files:**
- Modify: `chatbot-ui-vite/src/components/chat/MessageBubble.jsx:325-329` (add `sourcesExpanded` state), `:626-630` (render the Sources toggle)

**Interfaces:**
- Consumes: existing `message.sources` array (each item shaped `{ title, source, snippet }`, already populated identically across `App.jsx`/`ChatWindow.jsx`/`InputBar.jsx`'s message-send paths).
- Produces: no new props — purely a new render branch inside the existing bot-message JSX.

- [ ] **Step 1: Add `sourcesExpanded` state**

Find this block (currently lines 325-329):

```jsx
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draftText, setDraftText] = useState(message.text || "");
```

Replace it with:

```jsx
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draftText, setDraftText] = useState(message.text || "");
  const [sourcesExpanded, setSourcesExpanded] = useState(false);
```

- [ ] **Step 2: Render the "Sources" toggle below the response content**

Find this block (currently lines 626-630):

```jsx
          ) : (
            renderContentBlocks(message.text, isStreaming)
          )}

          {/* Only show action icons for finished, non-error assistant messages */}
```

Replace it with:

```jsx
          ) : (
            renderContentBlocks(message.text, isStreaming)
          )}

          {isBot && !isStreaming && !isError && message.sources?.length > 0 && (
            <div className="text-[13px]">
              <button
                type="button"
                onClick={() => setSourcesExpanded((prev) => !prev)}
                className="text-[color:var(--pragna-text-muted)] hover:text-accent-400 transition-colors duration-150"
              >
                {sourcesExpanded ? "▾" : "▸"} Sources ({message.sources.length})
              </button>
              {sourcesExpanded && (
                <ul className="mt-1.5 flex flex-col gap-1 pl-4 list-disc">
                  {message.sources.map((src, idx) => (
                    <li key={idx} className="text-[color:var(--pragna-text-muted)]">
                      {src.source ? (
                        <a href={src.source} target="_blank" rel="noopener noreferrer" className="text-accent-400 hover:underline">
                          {src.title || src.source}
                        </a>
                      ) : (
                        <span>{src.title || "Untitled source"}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Only show action icons for finished, non-error assistant messages */}
```

- [ ] **Step 3: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings beyond the pre-existing baseline.

- [ ] **Step 4: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`, seed a chat with a bot message carrying `sources` (e.g. via DevTools console: set `localStorage.pragna_chats` to a chat whose last bot message includes `"sources": [{"title": "Example", "source": "https://example.com"}]`, then reload). Confirm a "▸ Sources (1)" toggle appears below the message text and above the action-icon row; click it, confirm it expands to show a clickable "Example" link and the arrow flips to "▾"; click again to collapse. Confirm a message with no `sources` shows no toggle at all.

- [ ] **Step 5: Commit**

```bash
git add chatbot-ui-vite/src/components/chat/MessageBubble.jsx
git commit -m "feat: render RAG/web-search source citations on bot messages"
```

---

### Task 5: Global message-content search

**Files:**
- Modify: `chatbot-ui-vite/src/pragna/components/Sidebar.jsx:296-298` (widen `filteredChats`)

**Interfaces:**
- Consumes: existing `recentChats` prop (`{ id, title, messages }[]`) and `searchQuery` state already in `Sidebar.jsx`.
- Produces: no new exports — `filteredChats` keeps its existing name and shape (still an array of whole chat objects), just a broader match.

- [ ] **Step 1: Widen the filter to also match message text**

Find this block:

```jsx
  const filteredChats = recentChats.filter((chat) =>
    (chat.title || 'New chat').toLowerCase().includes(searchQuery.toLowerCase())
  )
```

Replace it with:

```jsx
  const filteredChats = recentChats.filter((chat) => {
    const query = searchQuery.toLowerCase()
    if (!query) return true
    const titleMatch = (chat.title || 'New chat').toLowerCase().includes(query)
    const messageMatch = (chat.messages || []).some((msg) => (msg.text || '').toLowerCase().includes(query))
    return titleMatch || messageMatch
  })
```

- [ ] **Step 2: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings beyond the pre-existing baseline.

- [ ] **Step 3: Manually verify**

Run: `cd chatbot-ui-vite && npm run dev`, create two chats: one titled "Recipe ideas" with no matching message text, another titled "Random" containing a message with the word "recipe" somewhere in its text. Type "recipe" into the sidebar search box. Confirm both chats now appear (title match and message-body match), and that clearing the search box restores the full list.

- [ ] **Step 4: Commit**

```bash
git add chatbot-ui-vite/src/pragna/components/Sidebar.jsx
git commit -m "feat: widen chat search to match message content, not just titles"
```
