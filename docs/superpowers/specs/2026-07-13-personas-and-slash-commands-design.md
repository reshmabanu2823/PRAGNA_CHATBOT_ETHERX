# Custom Personas + Slash Commands

**Status:** Approved

## Goal

Two independent features:
1. Let a user create named, backend-persisted personas (custom system prompts) and switch between them per chat session, the same way the existing chat-mode picker works.
2. Let a user type `/`-prefixed slash commands directly into the chat input as shortcuts for capabilities that already exist in the app (summarize, mode switch, language switch, new chat, image generation, document generation, persona switch).

## Context (existing patterns this builds on)

- `chatMode`/`setChatMode` in `chatbot-ui-vite/src/context/ChatContext.jsx:49` is a single global "currently selected mode" state, persisted to `localStorage` (`pragna_chat_mode`) and shown as a badge in `ChatWindow.jsx`'s header — not bound to individual past conversations. The persona picker follows this exact same state shape (`activePersonaId`, persisted as `pragna_active_persona_id`), not a per-conversation-forever binding.
- `backend/database.py`'s `Database` class (SQLite, `data/chatbot.db`) already has `users`, `conversations`, `messages`, `api_usage` tables with a consistent `CREATE TABLE IF NOT EXISTS` + `user_id TEXT NOT NULL FOREIGN KEY` pattern. The new `personas` table follows this exactly.
- `backend/auth.py`'s `require_auth` decorator sets `request.user_id` from the JWT and is already used by routes like `/api/conversations` (`backend/app.py:1970-1971`) — the new persona routes are gated the same way.
- The full chat-completion call chain is: `POST /api/chat_stream` (`backend/app.py:1649`) reads `model_override`/`fallback_models`/`chat_mode` from the request body and passes them straight through to `orchestrator.handle_query(...)` (`backend/services/orchestrator.py:19-27`), which calls `self.llm.get_response(...)` (`backend/llm_service.py:185-193`). `chat_stream` calls the plain, non-streaming `handle_query` and artificially chunks the final text for SSE — there is only this one call chain to extend, not a separate streaming code path.
- Inside `get_response` (`backend/llm_service.py:310-321`), the system message is currently *always* built from the auto-inferred style profile: `style = style_profile.get_style_profile(...)`, then `style_msg = style_profile.style_system_message(style, language, chat_mode)`, then `prompt_messages.insert(0, {"role": "system", "content": style_msg})`. This is the exact point personas hook into.
- `chatbot-ui-vite/src/api/api.js`'s `_authHeaders()` helper (already used by the agent-panel routes) is the existing pattern for attaching `Authorization: Bearer <token>` to `fetch` calls — the new persona API functions reuse it.
- The existing natural-language detection for image/document generation (`IMAGE_REQUEST_RE`/`extractImagePrompt` and `DOCUMENT_VERB_RE`/`DOCUMENT_FORMAT_PATTERNS`/`extractDocumentRequest`) is duplicated across `ChatWindow.jsx`, `InputBar.jsx`, and `pragna/App.jsx` because any of those three send paths can receive natural-language text. Slash commands are different: only `InputBar.jsx` is free-typed user input (`ChatWindow.jsx`'s suggestion sends and `pragna/App.jsx`'s quick prompts are pre-built strings a user doesn't type `/` into), so slash-command parsing lives only in `InputBar.jsx`.
- `SettingsModal.jsx` already has a "Model" tab (from an earlier round) — the persona management UI adds a "Personas" tab to this same modal, not a new modal.

## Architecture

**Personas** are backend-persisted per-user records (`{id, name, system_prompt}`), managed via 4 new authenticated CRUD routes and a "Personas" tab in the existing Settings modal. The currently-active persona is a single global selection (mirroring `chatMode`), switchable via a picker next to the mode badge in the chat header. When a persona is active, its `system_prompt` is sent with each chat request and **replaces** the auto-inferred style message for that turn on the backend — no persona selected means today's behavior is completely unchanged.

**Slash commands** are a client-side-only input parser added to `InputBar.jsx`. Typing `/` as the first character shows an autocomplete list of matching commands; submitting a recognized command dispatches directly to the corresponding existing function (skipping the normal chat-send / natural-language-detection flow entirely) instead of being sent to the LLM as a literal message.

## Backend: Personas

### Database

Add to `backend/database.py`'s `init_db()`, alongside the existing tables:
```sql
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
```
New `Database` methods, following the existing `create_user`/`get_user`-style patterns: `create_persona(user_id, name, system_prompt) -> persona_id`, `list_personas(user_id) -> list[dict]`, `get_persona(persona_id, user_id) -> dict | None` (used internally to verify ownership before update/delete), `update_persona(persona_id, user_id, name, system_prompt) -> bool`, `delete_persona(persona_id, user_id) -> bool`. Update/delete return `False` (not an exception) when the persona doesn't exist or doesn't belong to `user_id`, so routes can return 404 without leaking whether a persona ID exists for another user.

### Routes

All four gated by `@require_auth`, using `request.user_id`:
- `GET /api/personas` → `200 {"personas": [{"id", "name", "system_prompt", "created_at", "updated_at"}, ...]}`
- `POST /api/personas` → body `{"name": str, "system_prompt": str}`, both required non-empty → `201 {"id", "name", "system_prompt", "created_at", "updated_at"}` or `400 {"error"}` if either field is blank
- `PUT /api/personas/<id>` → body `{"name": str, "system_prompt": str}` → `200` with the updated record, or `404 {"error": "Persona not found"}` if it doesn't exist or belongs to another user
- `DELETE /api/personas/<id>` → `200 {"success": true}` or `404 {"error": "Persona not found"}`

### Wiring into chat completion

`POST /api/chat_stream` reads one new optional field from the request body: `persona_system_prompt` (a plain string, sent by the frontend — not a persona ID, since the backend has no need to re-look-up the persona by ID). Threaded unchanged through `orchestrator.handle_query(..., persona_system_prompt=persona_system_prompt)` → `llm.get_response(..., persona_system_prompt=persona_system_prompt)`.

Inside `get_response`, replace the unconditional style-message construction with:
```python
if persona_system_prompt:
    system_msg = persona_system_prompt
else:
    style = style_profile.get_style_profile(user_id, max_messages=self.max_history)
    current_tone = tone_detector.detect_tone(message)
    if current_tone != "neutral":
        style["tone"] = current_tone
    system_msg = style_profile.style_system_message(style, language, chat_mode)
prompt_messages.insert(0, {"role": "system", "content": system_msg})
```
When `persona_system_prompt` is falsy (not provided, or an empty string), behavior is byte-for-byte identical to today.

## Frontend: Personas

### API client

New functions in `chatbot-ui-vite/src/api/api.js`, using the existing `_authHeaders()` helper and throwing on non-ok responses (matching `generateDocument`'s error-handling shape): `listPersonas()`, `createPersona({name, system_prompt})`, `updatePersona(id, {name, system_prompt})`, `deletePersona(id)`.

### Management UI

A new "Personas" tab in `SettingsModal.jsx` (alongside the existing "Model" tab): a list of the user's personas (name + truncated prompt preview), an "Add persona" form (name input + system-prompt textarea), and per-persona Edit/Delete controls. Fetches via `listPersonas()` on tab open; create/update/delete call the corresponding API function and refresh the list.

### Switching UI

`ChatContext.jsx` gets new state: `personas` (fetched list, refreshed on login/app load), `activePersonaId` (persisted to `localStorage` as `pragna_active_persona_id`, mirroring `chatMode`'s pattern exactly), and `setActivePersonaId`. `ChatWindow.jsx`'s header gets a small picker next to the existing mode badge: "No persona" plus each persona's name; selecting one calls `setActivePersonaId`.

### Sending with a persona

All three send paths that build the outgoing request body (`ChatWindow.jsx`'s `sendSuggestionMessage`, `InputBar.jsx`'s `handleSendMessage`, `pragna/App.jsx`'s `sendQuickPrompt`) look up the active persona's `system_prompt` from `ChatContext`'s `personas` list by `activePersonaId` and, if found, include `persona_system_prompt: <that prompt>` in the body passed to `sendOrchestratedMessageStream`. `sendOrchestratedMessageStream` (`api.js`) forwards this field unchanged in its POST body to `/api/chat_stream`, alongside the existing `model_override`/`fallback_models`. When no persona is active, the field is omitted entirely (not sent as an empty string), preserving today's default behavior with zero ambiguity.

## Slash Commands

### Detection and dispatch

In `InputBar.jsx`'s `handleSendMessage`, before any existing detection logic (image/document/attachment), check whether the trimmed message starts with `/`. If so, parse the command name (first whitespace-delimited token after the `/`) and the remainder as its argument string, and dispatch — the message is never sent to the LLM as chat text, regardless of whether the command is recognized.

| Command | Argument | Behavior |
|---|---|---|
| `/summarize` | none | Same effect as clicking the existing "Summarize" button: calls `summarizeChat(messages, language)` and inserts the result as a message in the current chat. |
| `/mode <name>` | one of `general\|explain\|ideas\|write\|code\|questions\|story`, matched case-insensitively | Calls `setChatMode` with the mapped internal value (reusing the same label→value mapping already defined in `ChatWindow.jsx`). Unknown name → inline error. |
| `/lang <code>` | one of the codes already in `LanguageSelector` (`en`, `hi`, `ta`, `te`, `kn`, `ml`, `mr`, `gu`, `pa`, `bn`, `ur`), matched case-insensitively | Calls the language setter already in scope in `InputBar.jsx`. Unknown code → inline error. |
| `/clear` | none | Calls the existing `newChat()` from `ChatContext` (same as the sidebar's "New chat" button). |
| `/image <prompt>` | required, non-empty | Calls `generateAIImage({ prompt, style: "cinematic", quality: "hd", size: "1024x1024" })` directly and renders the result exactly like the natural-language image path does. Empty prompt → inline error. |
| `/doc <format> <prompt>` | format required (`docx\|xlsx\|pdf\|pptx`, matched case-insensitively), prompt required non-empty | Calls `generateDocument({ format, prompt, language })` directly and renders the result exactly like the natural-language document path does. Missing/invalid format or empty prompt → inline error explaining the expected syntax. |
| `/persona <name>` | required, matched case-insensitively against `personas` in `ChatContext` | Calls `setActivePersonaId` with the matched persona's ID. No match → inline error listing available persona names. |

An inline error is rendered as a bot message with `error: true` (the same mechanism `MessageBubble.jsx` already uses for network/server failures — see its `isError` rendering), so it visually matches existing error states rather than introducing a new UI pattern.

### Autocomplete

While the input's current value starts with `/` and contains no space yet (i.e., the user is still typing the command name), a small dropdown renders above the input listing every command whose name starts with the typed prefix, each with a one-line description (the argument syntax, e.g. `/mode <general|explain|ideas|write|code|questions|story>`). Clicking an entry replaces the input's value with `/<command-name> ` (trailing space, cursor implicitly at the end) so the user can complete the argument and press Enter/Send. The dropdown closes once a space is typed (argument-entry mode) or the input no longer starts with `/`.

## Testing

- **Backend:** `backend/test_personas.py` (standalone script, this repo's convention — plain `assert`s, no pytest) exercises `Database`'s persona CRUD methods directly, including that `update_persona`/`delete_persona` correctly return `False` for another user's persona ID. Live curl pass against the 4 routes with a real registered/logged-in test user: 401 without a token, correct create/list/update/delete, and a second test user cannot see or modify the first user's personas. A live curl request to `/api/chat_stream` with a distinctive `persona_system_prompt` (e.g. "Respond only in the form of a haiku, no matter what is asked") confirms the actual model output reflects it — the same behavioral-verification approach already used for document generation's LLM-dependent paths.
- **Frontend:** `npm run build && npm run lint` (no test runner in this repo). Manual exercise: create a persona in Settings, select it via the header picker, send a message, confirm the response reflects the custom system prompt; switch back to "No persona" and confirm the response returns to the normal adaptive-style behavior. For slash commands: exercise `/summarize`, `/mode code`, `/lang hi`, `/clear`, `/image a sunset`, `/doc pdf a report on rivers`, `/persona <name>`, an unrecognized command, and a recognized command with a missing/invalid argument — confirming each does the right thing and that `/image`/`/doc` produce real, downloadable/clickable attachments identical to the natural-language paths.

## Out of scope

- Sharing personas between users, or any "public persona library."
- Persona-specific model overrides (a persona only sets the system prompt, not which model/fallbacks are used).
- Slash commands with sub-autocomplete for arguments (e.g. suggesting persona names as you type `/persona `) — the initial autocomplete only suggests command names, not argument values.
- Keyboard-only navigation of the slash-command autocomplete dropdown (arrow keys/Enter-to-select) — v1 is click-to-select only, consistent with keeping this round's scope bounded.
- Editing a message after sending it to retroactively change which persona produced it.
