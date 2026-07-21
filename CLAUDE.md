# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Pragna (also called Pragna-1 A / Chat_Assistant_EtherX) is a multilingual AI chat assistant with a Flask backend and a Vite+React frontend, plus two agentic coding-assistant surfaces: a web-embedded agent panel and a standalone terminal CLI (`pragna_code.py`).

## Commands

**Backend** (from `backend/`):
```bash
python app.py                    # start Flask server (reads backend/.env, default port 5001)
python test_agent_sandbox.py     # run a single backend test script directly
```
There is no pytest suite despite pytest being installed — this repo's test convention is standalone `test_*.py` scripts at `backend/` root, run individually with `python test_x.py`, using plain `assert` statements and printed progress (see `test_vision.py`, `test_agent_*.py`). Write new backend tests the same way, not as pytest-discovered files.

**Frontend** (from `chatbot-ui-vite/`):
```bash
npm run dev      # Vite dev server; proxies /api/* to http://localhost:5001 (see vite.config.js)
npm run build
npm run lint
```
No frontend test runner is configured in this repo (no `test` script, no Jest/Vitest). Frontend changes are verified by build + lint + manual exercise, not automated tests.

**CLI agent** (from repo root):
```bash
python pragna_code.py [directory]   # standalone terminal coding agent, independent of the Flask backend
```

## Configuration

Both `backend/app.py` and `pragna_code.py` read `backend/.env` (the CLI loads it via `python-dotenv` from `backend/.env` relative to its own location). Key variables:
- `LLM_PROVIDER`: `ollama_only` | `standard` | `deepseek_local` — selects the model backend globally.
- `OLLAMA_API_URL` / `OLLAMA_MODEL`: local Ollama endpoint and default model.
- `GROQ_API_KEY` / `OPENAI_API_KEY`: cloud fallback providers (used when `LLM_PROVIDER=standard`).
- `DEFAULT_MODEL_KEY` / `DEFAULT_MODEL_FALLBACKS` (and the `MODEL_PROFILE_LIGHT_*` / `MODEL_PROFILE_HEAVY_*` pairs): comma-separated `provider:model` keys (e.g. `ollama:qwen3:8b,groq:llama-3.1-8b-instant`) resolved against `config.MODEL_REGISTRY`.
- `DEVELOPMENT_MODE=True` enables mock/demo responses when no real API key is configured — never leave this on in anything resembling production.
- `JWT_SECRET` — signs the auth tokens `require_auth` (in `backend/auth.py`) checks on protected routes.

## Backend architecture

`backend/app.py` is a single large Flask app (2000+ lines, ~50 routes) rather than split blueprints, except for `chat_management_api.py` which is registered as a blueprint. Route groups: chat/orchestrator, RAG management, memory/conversations, images, speech (STT/TTS), auth, and the agent subsystem (`/api/agent/*`).

**Request flow for chat**: `classify_query` (`services/classifier.py`) → `route_query` (`services/router.py`) → `create_plan` (`services/planner.py`) → `AIOrchestrator.handle_query` (`services/orchestrator.py`), which calls `LLMService` (`backend/llm_service.py`, top-level, not in `services/`). `LLMService` and `services/llm.py` are the layer that actually dispatches to a provider based on a `provider:model` key — `services/llm.py` holds the low-level per-provider completion helpers (`_call_ollama_direct`, etc.) and `list_available_models`.

**Memory/history**: `services/memory_management.py` does token-budget-aware history pruning (`smart_prune_history`, importance scoring in `config.MESSAGE_IMPORTANCE_WEIGHTS`) before a conversation is sent to the model; `services/memory_db.py` and `database.py` (`Database` class, SQLite at `backend/data/chatbot.db`) persist it.

**RAG**: `services/rag_service.py` (FAISS + embeddings) with `services/rag_scheduler.py` running scheduled web-content refreshes (topics/domains configured in `config.py`, India-current-affairs-biased by default) via `services/web_scraper.py`.

**Auth**: `backend/auth.py`'s `AuthService` issues/verifies JWTs; `require_auth` is the decorator every protected route uses. `/api/auth/register` and `/api/auth/login` are the only unauthenticated auth-adjacent routes.

**Agent subsystem** (`backend/services/code_agent.py` + `/api/agent/*` routes + `pragna_code.py`): a think→tool→observe loop over a model, giving it `read_file`/`write_file`/`create_file`/`append_file`/`list_dir`/`search_code`/`run_command` tools. Two hardening properties are load-bearing and must be preserved in any change here:
- **Sandboxing**: every file-tool path is resolved via `_resolve_in_root(root, path)` against a working-directory root and rejected if it escapes — but `run_command` is *not* sandboxed (it's an arbitrary shell command); its only protection is the approval gate below.
- **Confirm-before-act**: `write_file`/`create_file`/`append_file`/`run_command` (`MUTATING_TOOLS`) never execute immediately. The web agent's loop (`run_agent_stream` / `_agent_loop` / `resume_agent_stream`, session-tracked in the in-memory `AGENT_SESSIONS` dict) pauses and emits a `confirm_required` SSE event with a diff/command preview; the CLI blocks synchronously on a `y/N` prompt (`_confirm_action`) before dispatching. `read_file`/`list_dir`/`search_code` (`AUTO_TOOLS`) run immediately with no approval. The CLI and the web agent maintain **separate copies** of this tool logic — they are not shared modules, so a fix in one does not apply to the other.

## Frontend architecture

Entry point: `main.jsx` → `src/App.jsx` (auth gate: renders `Login` or the main app based on `localStorage.authToken`, wraps everything in `ChatProvider`) → `src/pragna/App.jsx` (the actual app shell: sidebar navigation, view switching between chat/dashboard/agent/etc.).

- `src/pragna/` — the main shell (layouts, sidebar, pages) for the primary UI.
- `src/components/` — feature components grouped by domain (`chat/`, `auth/`, `agent/`, `dashboard/`, `input/`, `ui/`, `layout/`).
- `src/api/` — two different client styles coexist: `chatManagement.js` uses an axios instance with a request interceptor that auto-attaches `Authorization: Bearer <authToken>`; `api.js` uses raw `fetch` and must attach that header manually per-call (see `_authHeaders()` there) — new fetch-based endpoints in `api.js` need this by hand, axios-based ones get it for free via the interceptor.
- SSE streaming (used by the agent panel) is consumed via a shared `_consumeSSE(response, onEvent)` helper in `api.js`, not duplicated per streaming function.

## Cross-cutting notes

- The backend and the CLI (`pragna_code.py`) are independent programs that both talk to Ollama directly — there is no shared Python package between them, so agent/tool behavior is duplicated by design, not by omission.
- `backend/temp/conversation_memory.db` is a tracked binary despite `*.db` being in `.gitignore` (it was committed before the ignore rule took effect) — don't be surprised it shows as modified after simply importing `app.py` locally.
