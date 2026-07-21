# Pragna Chat UI Reskin — Design Spec

Source design: `Pragna Chat.dc.html` from the claude.ai/design project "Etherx Pragna Chatbot UI" (`17f8a746-a6d4-4fcc-9bfe-ca317ceb6522`). The source is a self-contained mockup (custom `x-dc`/`sc-for`/`sc-if` binding DSL with a demo-only `Component` class) — it is a visual/structural reference only, not code to run directly. Its stub logic (fake `demoReply`, in-memory `messages` state) is not adopted; real functionality in the current app is preserved throughout.

## Goal

Reskin the existing Pragna React frontend (`chatbot-ui-vite/`) to visually and structurally match the mockup, across all 7 sidebar views (Chats, Explore, Images, Projects, GPTs, Intelligence, Agent), while preserving all existing real functionality (streaming chat, RAG, image generation, dashboards, the agent tool-loop). This is a styling/structural reskin, not a feature change.

## Current state (baseline, confirmed by codebase survey)

- `src/pragna/App.jsx` + `src/pragna/layouts/MainLayout.jsx` + `src/pragna/components/Sidebar.jsx` already implement the same 7 nav items in the same order as the mock, with a dark/gold theme already partially in place via `tailwind.config.js` (`accent` gold scale, `500: '#d4af37'`) and `src/pragna/styles/globals.css` (`--pragna-gold`, `--pragna-bg`, `--pragna-surface`, `--pragna-text` CSS vars, plus a `.pragna-shell` override layer remapping stray light-theme Tailwind classes).
- Chat (`src/components/chat/ChatWindow.jsx`, `MessageBubble.jsx`, `CodeBlock.jsx`) and Input (`src/components/input/InputBar.jsx`, `LanguageSelector.jsx`) are styled via a separate legacy plain-CSS system (`src/styles/chat.css`, `input.css`, ~2,676 lines total across `src/styles/`), independent of the Tailwind/CSS-var theme.
- `src/components/agent/AgentPanel.jsx` (479 lines) is styled entirely with hardcoded inline styles in an unrelated blue-black palette (`#0b0f1a`), completely disconnected from the rest of the app's theme.
- Images and GPTs views are inline JSX blocks inside `App.jsx` (not dedicated component files).
- `src/components/dashboard/GlobalDashboard.jsx` (Projects) and `WorldMonitorDashboard.jsx` (Intelligence) are dedicated components already, styled inline/Tailwind-ish but not matched to the mock's exact card layout.
- A separate, apparently unused parallel component tree exists at `src/components/layout/` (`Sidebar.jsx`, `MainLayout.jsx`, `Header.jsx`). Confirm it is not wired into `main.jsx` before starting; leave untouched either way unless investigation shows it IS live, in which case flag before proceeding.

## Theme tokens

Single source of truth: `src/pragna/styles/globals.css` CSS variables, consumed via Tailwind config where components use Tailwind classes, and directly via `var(--pragna-*)` where components use inline/plain CSS.

Values, taken from the mock:
- `--pragna-bg: #0a0a0a`
- `--pragna-gold: #d4af37` (primary accent)
- Gold gradient stops: `#e5c76b` → `#b8860b` (used for primary buttons, avatars, active-state backgrounds)
- `--pragna-text: #f0e6d3` (primary text)
- `--pragna-text-muted: #a89878` (secondary text, placeholders)
- `--pragna-border: #2d2a24`
- `--pragna-surface: rgba(20,20,20,0.82)` with `backdrop-filter: blur(8px)` on cards/panels
- Card shadow: `0 2px 8px rgba(0,0,0,0.28)`; elevated/hover shadow: `0 20px 32px rgba(0,0,0,0.50)` (hover-lift `translateY(-3px)`)
- Border radius scale: pills `999px`, buttons/inputs `10-12px`, cards `14-20px`
- Font: `'Segoe UI', system-ui, -apple-system, sans-serif`

Work: audit existing `--pragna-*` vars against these values, correct any drift, add missing ones (gradient stops, surface-blur, the two shadow levels), extend `tailwind.config.js` `accent`/`surface`/`border` scales to match exactly.

## Per-view changes

### 1. Sidebar / Shell / Home (smallest gap)
- `Sidebar.jsx`, `NavItem.jsx`, `RecentItem.jsx`: align active/hover/border states, spacing (22px/20px/18px paddings per mock), and the "New chat" button gradient/hover states to the mock exactly.
- `HomePage.jsx`: hero heading + gradient-text span ("where should we start?"), mode-chip row, starter-card grid (border-radius 16px, hover-lift + shadow, icon chip with gold-tinted background).

### 2. Chat + Input (migrate off legacy CSS)
- `MessageBubble.jsx`: user bubble → gold-gradient background, `#1a1405` text, radius `18px 18px 4px 18px`. Assistant message → square gold-gradient avatar (32px, "P" mark) + surface-card bubble, radius `4px 18px 18px 18px`, `backdrop-filter: blur(8px)`. Error card → red-tinted surface variant with retry button, per mock's error-card treatment.
- `CodeBlock.jsx`: header bar (`#1a1a1a` bg) showing language label (gold, letter-spaced) + copy button with copied-state feedback; code area `#101010` bg, monospace, matching mock padding/line-height.
- Message actions row (copy/like/dislike/speak): keep existing icons/behavior, restyle to mock's ghost-icon-button treatment (transparent → `#1a1a1a` hover bg, muted → gold on hover).
- `InputBar.jsx`: pill-shaped container (`rgba(20,20,20,0.82)` + blur), border-color transition on focus (`rgba(212,175,55,0.18)` → `0.45`), attach/language/mic/send buttons restyled to mock spec (send button gold-gradient, others ghost). Existing attach-menu, language selector, and speech-recognition behavior unchanged.
- Delete/stop using `src/styles/chat.css` and `src/styles/input.css` once migration is complete for these components; confirm no other component still depends on those files before deleting (grep first).

### 3. Agent panel (full reskin, biggest gap)
- Replace all hardcoded `#0b0f1a`-palette inline styles in `AgentPanel.jsx` with the shared theme (Tailwind classes + `--pragna-*` vars).
- Header: lightning-bolt icon + "Pragna Code" title + gold "AGENT" pill badge, subtitle text.
- Mode selector: pill row (General/Code Review/App Builder/Debug/Explain/Refactor), active state gold-gradient-tinted per mock.
- Idle state: bolt icon, "Ready to work" heading, example-prompt bullet list, matching mock's centered empty-state layout.
- Task input area: surface card with textarea + "Ctrl+Enter to run" hint + gold Run button; Stop/Clear controls preserved from current implementation, restyled to match.
- Live event stream (thought/tool_call/tool_result/confirm_required/done/error cards) and the confirm/reject approval UI: **keep current structure, icons, and behavior**; only restyle colors/borders/backgrounds from the current blue-dark scheme to the gold/dark palette (surface-card background, gold accents for active/highlighted states, existing semantic colors — e.g. error red, success green — adapted to sit on the dark-gold surface rather than removed).

### 4. Images & GPTs (extract to components)
- New `src/pragna/pages/ImageStudioPage.jsx` (or equivalent location matching existing page conventions): prompt textarea, style/quality/size `<select>` row, Generate/Send-to-Chat buttons — move existing logic out of `App.jsx` inline JSX, restyle to mock's card layout.
- New `src/pragna/pages/GptModesPage.jsx`: mode-card grid (name + tagline per card), reusing the existing mode list/selection logic, restyled to mock's card treatment (active-state border/title-color change).

### 5. Projects (World Monitor) & Intelligence dashboards
- `GlobalDashboard.jsx`: stat-tile row, geo-activity-map placeholder card, live-event-feed card, "World Monitor Integration" external-link card — restyle to mock's grid/card layout. Geo-map visual and any "Syncing…" badge are included as visual-only elements (no backend tie-in required) per product decision.
- `WorldMonitorDashboard.jsx` (Intelligence): tab row (Global/Military/Infrastructure/Markets/Cyber), threat-level/escalation-index/stability-score cards, critical-alerts panel, refresh button — restyle to mock spec. Existing data-fetching/error states preserved; the mock's "Failed to fetch" banner styling is adopted for the existing error state.

## Explicitly out of scope
- No backend route changes, no SSE event-shape changes, no changes to agent tool logic, RAG behavior, auth, or any business logic.
- No changes to `src/components/layout/` unless discovered to be live (see baseline note above).
- No new real functionality beyond what's needed to visually include mock elements that lack a backing feature today (tier toggle, geo-map placeholder, syncing badge) — these are added as inert/local-state-only UI.

## Testing / verification approach

No automated frontend test runner exists in this repo (per `CLAUDE.md`). Verification is: `npm run build` + `npm run lint` clean, plus manual exercise of each of the 7 views in a running dev server (`npm run dev`) — confirm existing functionality (send/stream a chat message, generate an image, run an agent task end-to-end including a mutating-tool confirm/reject, view both dashboards) still works after the restyle, and visually compare each view against the corresponding section of `Pragna Chat.dc.html`.
