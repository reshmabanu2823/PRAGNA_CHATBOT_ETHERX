# Chunked Streaming, Chat Summarization, Prompt Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make chat responses stream in visibly as they arrive, add a real "summarize this conversation" action, and let users save and reuse their own prompt templates.

**Architecture:** Chunked streaming fixes the existing (currently malformed, currently unused) `/api/chat_stream` SSE endpoint and wires all three frontend message-send call sites to consume it. Summarization is a new backend endpoint reusing the app's standard `generate_completion` LLM call path, surfaced as a chat-header button that appends the result as a message. Templates are a frontend-only `localStorage`-backed collection, following the exact `folders` CRUD pattern already in `ChatContext.jsx`.

**Tech Stack:** Flask (Python) backend, React (Vite) frontend, no new dependencies on either side.

## Global Constraints

- No automated frontend test runner in this repo — verification is `npm run build` + `npm run lint` clean (no new errors/warnings versus this repo's pre-existing baseline: 27 errors / 3 warnings), plus manual exercise via `npm run dev`.
- No automated backend test suite (pytest) — this repo's convention is standalone verification of new/changed endpoints via direct HTTP requests (e.g. `curl`), with the Flask backend and Ollama both running locally.
- No new npm or pip dependencies for any task in this plan.
- Real token-by-token streaming (rewriting the Ollama call path) is explicitly out of scope — this plan only fixes and wires up the existing chunk-based `/api/chat_stream` endpoint.
- Run frontend npm commands from `chatbot-ui-vite/`. Run the backend from `backend/` (`python app.py`).
- Spec reference: `docs/superpowers/specs/2026-07-10-streaming-summary-templates-design.md`.

---

### Task 1: Streaming transport — backend SSE fix + frontend helper

**Files:**
- Modify: `backend/app.py:1655-1682` (fix SSE framing in `/api/chat_stream`)
- Modify: `chatbot-ui-vite/src/api/api.js:100` (add `sendOrchestratedMessageStream` after `sendOrchestratedMessage`)

**Interfaces:**
- Produces: `sendOrchestratedMessageStream({ text, language, user_id, chatMode, onChunk, onSources, onDone })` — an async function. `onChunk(text: string)` fires once per received text piece (call sites append it to a message's running `text`, not replace it). `onSources(sources: array)` fires once if the response used RAG/web-search. `onDone()` fires exactly once when the stream completes successfully. Actions (`{action, url}` entries) are handled internally via the existing `runResponseActions` — callers don't need to handle them. Rejects (throws) on a non-OK HTTP response or a `{"type": "error"}` event from the stream.

- [ ] **Step 1: Fix the SSE framing in `/api/chat_stream`**

Find this block (currently lines 1655-1682 in `backend/app.py`):

```python
        def stream_orchestrated_chunks():
            """Stream orchestrated response in JSON lines for frontend compatibility."""
            result = orchestrator.handle_query(
                user_message,
                language=language,
                user_id=user_id,
                chat_mode=chat_mode,
                model_override=model_override,
                fallback_models=fallback_models,
            )

            actions = result.get('actions', [])
            sources = result.get('web_search_sources', [])
            if actions:
                yield json.dumps({'actions': actions}) + "\n"
            if sources:
                yield json.dumps({'sources': sources}) + "\n"

            response_text = result.get('response', '')
            if not response_text:
                return

            chunk_size = 200
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield json.dumps({'content': chunk}) + "\n"

        return Response(stream_orchestrated_chunks(), mimetype='text/event-stream')
```

Replace it with:

```python
        def stream_orchestrated_chunks():
            """Stream orchestrated response as real SSE (data: <json>\\n\\n lines)."""
            result = orchestrator.handle_query(
                user_message,
                language=language,
                user_id=user_id,
                chat_mode=chat_mode,
                model_override=model_override,
                fallback_models=fallback_models,
            )

            actions = result.get('actions', [])
            sources = result.get('web_search_sources', [])
            if actions:
                yield f"data: {json.dumps({'actions': actions})}\n\n"
            if sources:
                yield f"data: {json.dumps({'sources': sources})}\n\n"

            response_text = result.get('response', '')
            chunk_size = 200
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return Response(stream_orchestrated_chunks(), mimetype='text/event-stream')
```

(Note: the `if not response_text: return` early-exit is removed so that the `done` event is always sent, even for an empty response — the frontend needs `done` to know when to stop showing the streaming indicator.)

- [ ] **Step 2: Add `sendOrchestratedMessageStream` to `api.js`**

Find this block (currently lines 93-100 in `chatbot-ui-vite/src/api/api.js`, the end of `sendOrchestratedMessage`):

```jsx
  if (!response.ok) {
    throw new Error("Server error. Please try again.");
  }

  const data = await response.json();
  runResponseActions(data);
  return data;
};

export const sendOrchestratedUploadMessage = async (
```

Replace it with:

```jsx
  if (!response.ok) {
    throw new Error("Server error. Please try again.");
  }

  const data = await response.json();
  runResponseActions(data);
  return data;
};

export const sendOrchestratedMessageStream = async ({
  text,
  language,
  user_id,
  chatMode = "general",
  onChunk,
  onSources,
  onDone,
}) => {
  const normalizedLanguage = normalizeLanguageCode(language);
  const modelRouting = _resolveModelProfileRouting();

  const response = await fetch("/api/chat_stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: text,
      language: normalizedLanguage,
      user_id,
      chat_mode: chatMode,
      model_override: modelRouting.model_override,
      fallback_models: modelRouting.fallback_models,
    }),
  });

  if (!response.ok) {
    throw new Error("Server error. Please try again.");
  }

  await _consumeSSE(response, (event) => {
    if (event.content) {
      onChunk?.(event.content);
    } else if (event.sources) {
      onSources?.(event.sources);
    } else if (event.actions) {
      runResponseActions({ actions: event.actions });
    } else if (event.type === "done") {
      onDone?.();
    } else if (event.type === "error") {
      throw new Error(event.content || "Stream error");
    }
  });
};

export const sendOrchestratedUploadMessage = async (
```

(`_consumeSSE` is defined later in this same file as a hoisted `async function` declaration, so calling it here before its point of definition in the file is valid JavaScript.)

- [ ] **Step 3: Verify the backend fix directly**

With the Flask backend and Ollama both running (`python app.py` in `backend/`, `ollama serve` separately), run:

```bash
curl -N -X POST http://localhost:5001/api/chat_stream -H "Content-Type: application/json" -d '{"message":"Say hello in exactly one short sentence.","language":"en","chat_mode":"general","user_id":"test"}'
```

Expected: output consists of one or more lines matching `data: {"content": "..."}` followed by a final `data: {"type": "done"}` line — each line prefixed with `data: ` and followed by a blank line (the `\n\n` terminator).

- [ ] **Step 4: Build and lint the frontend change**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: build succeeds; lint shows no new errors/warnings versus the 27-error/3-warning baseline (none in `api.js`).

- [ ] **Step 5: Commit**

```bash
git add backend/app.py chatbot-ui-vite/src/api/api.js
git commit -m "feat: fix SSE framing on /api/chat_stream and add streaming client helper"
```

---

### Task 2: Wire streaming into `ChatWindow.jsx`

**Files:**
- Modify: `chatbot-ui-vite/src/components/chat/ChatWindow.jsx:3` (import), `:127-155` (streaming call)

**Interfaces:**
- Consumes: `sendOrchestratedMessageStream({ text, language, user_id, chatMode, onChunk, onSources, onDone })` from Task 1.

- [ ] **Step 1: Import the streaming helper**

Find this line (currently line 3):

```jsx
import { generateAIImage, sendOrchestratedMessage } from "../../api/api";
```

Replace it with:

```jsx
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedMessageStream } from "../../api/api";
```

- [ ] **Step 2: Replace the blocking response handling with streaming**

Find this block (currently lines 127-155, inside `sendSuggestionMessage`'s `try`, right after the image-request early-return):

```jsx
      const data = await sendOrchestratedMessage(
        suggestion,
        normalizeLanguageCode(language),
        targetChatId,
        chatMode
      );
      setIsLoading(false);

      if (data && data.response) {
        const responseText = data.response;
        const sources = data.web_search_sources || [];

        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? { ...m, text: responseText, isStreaming: false, sources }
                      : m
                  ),
                }
              : c
          )
        );
      } else {
        throw new Error("Invalid response from server");
      }
```

Replace it with:

```jsx
      let sawResponse = false;
      await sendOrchestratedMessageStream({
        text: suggestion,
        language: normalizeLanguageCode(language),
        user_id: targetChatId,
        chatMode,
        onChunk: (chunk) => {
          sawResponse = true;
          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1 ? { ...m, text: (m.text || "") + chunk } : m
                    ),
                  }
                : c
            )
          );
        },
        onSources: (sources) => {
          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1 ? { ...m, sources } : m
                    ),
                  }
                : c
            )
          );
        },
        onDone: () => {
          setIsLoading(false);
          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1 ? { ...m, isStreaming: false } : m
                    ),
                  }
                : c
            )
          );
        },
      });

      if (!sawResponse) {
        throw new Error("Invalid response from server");
      }
```

- [ ] **Step 3: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: no new errors/warnings versus baseline.

- [ ] **Step 4: Manually verify**

Run `npm run dev` with the backend and Ollama running. From the "Explore" home view or an empty chat, click a starter card. Confirm the bot's reply text appears progressively (in a few visible pieces) rather than all at once, and that the streaming cursor/typing indicator clears once the reply finishes.

- [ ] **Step 5: Commit**

```bash
git add chatbot-ui-vite/src/components/chat/ChatWindow.jsx
git commit -m "feat: stream chat responses in ChatWindow's suggestion/retry/edit flow"
```

---

### Task 3: Wire streaming into `InputBar.jsx`

**Files:**
- Modify: `chatbot-ui-vite/src/components/input/InputBar.jsx:3` (import), `:218-258` (streaming call for the no-attachment path)

**Interfaces:**
- Consumes: `sendOrchestratedMessageStream(...)` from Task 1, same contract as Task 2.

- [ ] **Step 1: Import the streaming helper**

Find this line (currently line 3):

```jsx
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedUploadMessage } from "../../api/api";
```

Replace it with:

```jsx
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedMessageStream, sendOrchestratedUploadMessage } from "../../api/api";
```

- [ ] **Step 2: Split the attachment and plain-text paths, streaming the plain-text one**

Find this block (currently lines 218-258, inside `handleSendMessage`'s `try`, right after the image-request early-return):

```jsx
      let data;
      if (msgAttachments.length > 0) {
        try {
          data = await sendOrchestratedUploadMessage(
            msgText.trim(),
            normalizedLanguage,
            targetChatId,
            chatMode,
            msgAttachments
          );
        } catch (uploadErr) {
          console.warn("Upload analysis endpoint failed, falling back to text-only orchestrator:", uploadErr);
          const fallbackText = `${fullText}\n[Note: Attachment parsing endpoint unavailable.]`;
          data = await sendOrchestratedMessage(fallbackText, normalizedLanguage, targetChatId, chatMode);
        }
      } else {
        data = await sendOrchestratedMessage(fullText, normalizedLanguage, targetChatId, chatMode);
      }
      setIsLoading(false);

      if (data && data.response) {
        const responseText = data.response;
        const sources = data.web_search_sources || [];

        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? { ...m, text: responseText, isStreaming: false, sources }
                      : m
                  ),
                }
              : c
          )
        );
      } else {
        throw new Error("Invalid response from server");
      }
```

Replace it with:

```jsx
      if (msgAttachments.length > 0) {
        let data;
        try {
          data = await sendOrchestratedUploadMessage(
            msgText.trim(),
            normalizedLanguage,
            targetChatId,
            chatMode,
            msgAttachments
          );
        } catch (uploadErr) {
          console.warn("Upload analysis endpoint failed, falling back to text-only orchestrator:", uploadErr);
          const fallbackText = `${fullText}\n[Note: Attachment parsing endpoint unavailable.]`;
          data = await sendOrchestratedMessage(fallbackText, normalizedLanguage, targetChatId, chatMode);
        }
        setIsLoading(false);

        if (data && data.response) {
          const responseText = data.response;
          const sources = data.web_search_sources || [];

          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1
                        ? { ...m, text: responseText, isStreaming: false, sources }
                        : m
                    ),
                  }
                : c
            )
          );
        } else {
          throw new Error("Invalid response from server");
        }
      } else {
        let sawResponse = false;
        await sendOrchestratedMessageStream({
          text: fullText,
          language: normalizedLanguage,
          user_id: targetChatId,
          chatMode,
          onChunk: (chunk) => {
            sawResponse = true;
            setChats((prev) =>
              prev.map((c) =>
                c.id === targetChatId
                  ? {
                      ...c,
                      messages: c.messages.map((m, idx) =>
                        idx === c.messages.length - 1 ? { ...m, text: (m.text || "") + chunk } : m
                      ),
                    }
                  : c
              )
            );
          },
          onSources: (sources) => {
            setChats((prev) =>
              prev.map((c) =>
                c.id === targetChatId
                  ? {
                      ...c,
                      messages: c.messages.map((m, idx) =>
                        idx === c.messages.length - 1 ? { ...m, sources } : m
                      ),
                    }
                  : c
              )
            );
          },
          onDone: () => {
            setIsLoading(false);
            setChats((prev) =>
              prev.map((c) =>
                c.id === targetChatId
                  ? {
                      ...c,
                      messages: c.messages.map((m, idx) =>
                        idx === c.messages.length - 1 ? { ...m, isStreaming: false } : m
                      ),
                    }
                  : c
              )
            );
          },
        });

        if (!sawResponse) {
          throw new Error("Invalid response from server");
        }
      }
```

(The attachment path is unchanged in behavior — `/api/chat_stream` doesn't accept file uploads, so only the plain-text path streams.)

- [ ] **Step 3: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: no new errors/warnings versus baseline.

- [ ] **Step 4: Manually verify**

Run `npm run dev`. Type a plain-text message (no attachment) into the input bar and send it — confirm the reply streams in progressively. Then attach a file and send a message — confirm that path still works exactly as before (single response, no streaming), since it's untouched.

- [ ] **Step 5: Commit**

```bash
git add chatbot-ui-vite/src/components/input/InputBar.jsx
git commit -m "feat: stream chat responses in InputBar's plain-text send path"
```

---

### Task 4: Wire streaming into `App.jsx`'s `sendQuickPrompt`

**Files:**
- Modify: `chatbot-ui-vite/src/pragna/App.jsx:3` (import), `:130-158` (streaming call)

**Interfaces:**
- Consumes: `sendOrchestratedMessageStream(...)` from Task 1, same contract as Tasks 2-3.

- [ ] **Step 1: Import the streaming helper**

Find this line (currently line 3):

```jsx
import { generateAIImage, sendOrchestratedMessage } from '../api/api'
```

Replace it with:

```jsx
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedMessageStream } from '../api/api'
```

- [ ] **Step 2: Replace the blocking response handling with streaming**

Find this block (currently lines 130-158, inside `sendQuickPrompt`'s `try`, right after the image-request early-return):

```jsx
      const data = await sendOrchestratedMessage(
        prompt,
        normalizeLanguageCode(language),
        targetChatId,
        chatMode
      )
      setIsLoading(false)

      if (data && data.response) {
        const responseText = data.response
        const sources = data.web_search_sources || []

        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? { ...m, text: responseText, isStreaming: false, sources }
                      : m
                  ),
                }
              : c
          )
        )
      } else {
        throw new Error('Invalid response from server')
      }
```

Replace it with:

```jsx
      let sawResponse = false
      await sendOrchestratedMessageStream({
        text: prompt,
        language: normalizeLanguageCode(language),
        user_id: targetChatId,
        chatMode,
        onChunk: (chunk) => {
          sawResponse = true
          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1 ? { ...m, text: (m.text || '') + chunk } : m
                    ),
                  }
                : c
            )
          )
        },
        onSources: (sources) => {
          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1 ? { ...m, sources } : m
                    ),
                  }
                : c
            )
          )
        },
        onDone: () => {
          setIsLoading(false)
          setChats((prev) =>
            prev.map((c) =>
              c.id === targetChatId
                ? {
                    ...c,
                    messages: c.messages.map((m, idx) =>
                      idx === c.messages.length - 1 ? { ...m, isStreaming: false } : m
                    ),
                  }
                : c
            )
          )
        },
      })

      if (!sawResponse) {
        throw new Error('Invalid response from server')
      }
```

- [ ] **Step 3: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: no new errors/warnings versus baseline.

- [ ] **Step 4: Manually verify**

Run `npm run dev`. From the Image Studio page, use "Send to chat" (which calls `sendQuickPrompt`) — confirm the reply streams in progressively, same as Tasks 2-3's flows.

- [ ] **Step 5: Commit**

```bash
git add chatbot-ui-vite/src/pragna/App.jsx
git commit -m "feat: stream chat responses in App.jsx's sendQuickPrompt"
```

---

### Task 5: Backend `/api/summarize_chat` endpoint

**Files:**
- Modify: `backend/app.py:2018-2020` (add new route after the existing `/api/summarize`)

**Interfaces:**
- Produces: `POST /api/summarize_chat`, request body `{"messages": [{"sender": "user"|"bot", "text": "..."}, ...], "language": "en"}`, response `{"summary": "<text>"}` (200) or `{"error": "<message>"}` (400/500).

- [ ] **Step 1: Add the new route**

Find this block (currently lines 2016-2020, the end of `/api/summarize` and the start of the next section):

```python
    except Exception as e:
        logger.error(f"Summarize error: {e}", exc_info=True)
        return jsonify({'summary': 'New Chat', 'error': str(e)}), 200

# Register blueprints
```

Replace it with:

```python
    except Exception as e:
        logger.error(f"Summarize error: {e}", exc_info=True)
        return jsonify({'summary': 'New Chat', 'error': str(e)}), 200


@app.route('/api/summarize_chat', methods=['POST'])
def summarize_chat():
    """Generate a real, multi-sentence summary of a full conversation."""
    try:
        data = request.json or {}
        messages_in = data.get('messages', [])
        language = _normalize_language_code(data.get('language', 'en'))

        if not messages_in:
            return jsonify({'error': 'messages is required'}), 400

        transcript_lines = []
        for msg in messages_in:
            speaker = 'Pragna' if msg.get('sender') == 'bot' else 'You'
            text = (msg.get('text') or '').strip()
            if text:
                transcript_lines.append(f"{speaker}: {text}")
        transcript = "\n".join(transcript_lines)

        if not transcript:
            return jsonify({'error': 'No message content to summarize'}), 400

        from services.llm import generate_completion
        prompt_messages = [
            {
                'role': 'system',
                'content': (
                    'Summarize the following conversation in 3-5 sentences, covering '
                    'the main topics discussed and any conclusions reached. Write the '
                    'summary as plain prose, not a list.'
                ),
            },
            {'role': 'user', 'content': transcript},
        ]
        summary = generate_completion(prompt_messages, language=language)

        if not summary or not summary.strip():
            return jsonify({'error': 'Failed to generate summary'}), 500

        return jsonify({'summary': summary.strip()}), 200

    except Exception as e:
        logger.error(f"Summarize chat error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate summary'}), 500

# Register blueprints
```

- [ ] **Step 2: Verify directly**

With the Flask backend and Ollama both running, run:

```bash
curl -s -X POST http://localhost:5001/api/summarize_chat -H "Content-Type: application/json" -d '{"messages":[{"sender":"user","text":"What is the capital of France?"},{"sender":"bot","text":"The capital of France is Paris."}],"language":"en"}'
```

Expected: `{"summary": "<a 3-5 sentence summary mentioning Paris/France>"}` with HTTP 200.

Also verify the empty-input case:

```bash
curl -s -X POST http://localhost:5001/api/summarize_chat -H "Content-Type: application/json" -d '{"messages":[],"language":"en"}'
```

Expected: `{"error": "messages is required"}` with HTTP 400.

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: add /api/summarize_chat endpoint for real conversation summaries"
```

---

### Task 6: Frontend `summarizeChat` + "Summarize" button

**Files:**
- Modify: `chatbot-ui-vite/src/api/api.js` (add `summarizeChat` after `getModelsCatalog`)
- Modify: `chatbot-ui-vite/src/components/chat/ChatWindow.jsx:1,3` (imports), `:228` (add `summarizing` state and `handleSummarize`, near `toggleBookmark`), `:447-453` (header button)

**Interfaces:**
- Consumes: none new.
- Produces: `summarizeChat(messages, language) -> Promise<{ summary: string }>` in `api.js`.

- [ ] **Step 1: Add `summarizeChat` to `api.js`**

Find this block (currently lines 233-239, the end of `getModelsCatalog`):

```jsx
export const getModelsCatalog = async () => {
  const response = await fetch("/api/models/catalog");
  if (!response.ok) {
    throw new Error("Failed to fetch models catalog.");
  }
  return response.json();
};
```

Replace it with:

```jsx
export const getModelsCatalog = async () => {
  const response = await fetch("/api/models/catalog");
  if (!response.ok) {
    throw new Error("Failed to fetch models catalog.");
  }
  return response.json();
};

export const summarizeChat = async (messages, language) => {
  const response = await fetch("/api/summarize_chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ messages, language: normalizeLanguageCode(language) }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data?.error || "Failed to summarize chat.");
  }
  return data;
};
```

- [ ] **Step 2: Import `summarizeChat` and `useState` (already imported) in `ChatWindow.jsx`**

Find this line (currently line 1):

```jsx
import { useContext, useCallback, useState, useEffect } from "react";
```

This already includes `useState`; leave it unchanged. Find this line (currently line 3, already updated by Task 2 to include `sendOrchestratedMessageStream`):

```jsx
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedMessageStream } from "../../api/api";
```

Replace it with:

```jsx
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedMessageStream, summarizeChat } from "../../api/api";
```

- [ ] **Step 3: Add `summarizing` state and `handleSummarize`**

Find this block (currently lines 213-228, the `toggleBookmark` callback):

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

Add immediately after it:

```jsx

  // Summarize the active chat and append the result as a new message
  const [summarizing, setSummarizing] = useState(false);
  const handleSummarize = useCallback(async () => {
    if (!chat || summarizing) return;
    setSummarizing(true);
    try {
      const { summary } = await summarizeChat(chat.messages, language);
      setChats((prev) =>
        prev.map((c) =>
          c.id === activeChatId
            ? { ...c, messages: [...c.messages, { sender: "bot", text: summary }] }
            : c
        )
      );
    } catch (err) {
      console.error("Summarize error:", err);
    } finally {
      setSummarizing(false);
    }
  }, [chat, activeChatId, language, setChats, summarizing]);
```

- [ ] **Step 4: Add the "Summarize" button to the chat header**

Find this block (currently lines 447-453):

```jsx
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '14px 28px', borderBottom: '1px solid #2d2a24', background: 'rgba(10,10,10,0.5)', backdropFilter: 'blur(8px)', flexShrink: 0 }}>
        <div style={{ fontSize: '15px', fontWeight: 650, color: '#f0e6d3' }}>{chatTitle}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '5px 13px', borderRadius: '999px', background: 'rgba(212,175,55,0.10)', border: '1px solid rgba(212,175,55,0.22)', fontSize: '12px', fontWeight: 600, color: '#d4af37', letterSpacing: '0.4px' }}>
          <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#d4af37', boxShadow: '0 0 8px rgba(212,175,55,0.8)' }}></span>
          {modeLabel} mode
        </div>
      </div>
```

Replace it with:

```jsx
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '14px 28px', borderBottom: '1px solid #2d2a24', background: 'rgba(10,10,10,0.5)', backdropFilter: 'blur(8px)', flexShrink: 0 }}>
        <div style={{ fontSize: '15px', fontWeight: 650, color: '#f0e6d3' }}>{chatTitle}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '5px 13px', borderRadius: '999px', background: 'rgba(212,175,55,0.10)', border: '1px solid rgba(212,175,55,0.22)', fontSize: '12px', fontWeight: 600, color: '#d4af37', letterSpacing: '0.4px' }}>
          <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#d4af37', boxShadow: '0 0 8px rgba(212,175,55,0.8)' }}></span>
          {modeLabel} mode
        </div>
        <button
          onClick={handleSummarize}
          disabled={summarizing}
          title="Summarize this conversation"
          style={{
            marginLeft: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: '999px',
            border: '1px solid #2d2a24',
            background: 'transparent',
            color: '#a89878',
            fontSize: '12.5px',
            fontWeight: 600,
            cursor: summarizing ? 'default' : 'pointer',
            opacity: summarizing ? 0.6 : 1,
          }}
          className="hover:text-[#e5c76b] hover:border-accent-500/40"
        >
          {summarizing ? 'Summarizing…' : 'Summarize'}
        </button>
      </div>
```

- [ ] **Step 5: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: no new errors/warnings versus baseline.

- [ ] **Step 6: Manually verify**

With the backend and Ollama running, run `npm run dev`, open a chat with a few exchanged messages, click "Summarize" in the header. Confirm the button shows "Summarizing…" while in flight, then a new bot message containing a multi-sentence summary appears at the end of the conversation.

- [ ] **Step 7: Commit**

```bash
git add chatbot-ui-vite/src/api/api.js chatbot-ui-vite/src/components/chat/ChatWindow.jsx
git commit -m "feat: add chat summarization button"
```

---

### Task 7: `ChatContext.jsx` templates CRUD

**Files:**
- Modify: `chatbot-ui-vite/src/context/ChatContext.jsx:12-15` (add `templates` state), `:64-66` (add persistence effect), `:155-166` (add CRUD functions), `:193` (expose on provider value)

**Interfaces:**
- Produces: `templates: Array<{id, title, prompt}>`, `createTemplate(title: string, prompt: string): void`, `deleteTemplate(templateId: string): void`, all exposed on `ChatContext`.

- [ ] **Step 1: Add `templates` state**

Find this block (currently lines 12-15):

```jsx
  const [folders, setFolders] = useState(() => {
    const saved = localStorage.getItem("pragna_folders");
    return saved ? JSON.parse(saved) : [];
  });
```

Add immediately after it:

```jsx

  const [templates, setTemplates] = useState(() => {
    const saved = localStorage.getItem("pragna_templates");
    return saved ? JSON.parse(saved) : [];
  });
```

- [ ] **Step 2: Persist `templates` to localStorage**

Find this block (currently lines 64-66):

```jsx
  useEffect(() => {
    localStorage.setItem("pragna_folders", JSON.stringify(folders));
  }, [folders]);
```

Add immediately after it:

```jsx

  useEffect(() => {
    localStorage.setItem("pragna_templates", JSON.stringify(templates));
  }, [templates]);
```

- [ ] **Step 3: Add `createTemplate`/`deleteTemplate`**

Find this block (currently lines 155-166, the `duplicateChat` function):

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

Add immediately after it:

```jsx

  const createTemplate = (title, prompt) => {
    const trimmedTitle = (title || "").trim();
    const trimmedPrompt = (prompt || "").trim();
    if (!trimmedTitle || !trimmedPrompt) return;
    setTemplates((prev) => [...prev, { id: Date.now().toString(), title: trimmedTitle, prompt: trimmedPrompt }]);
  };

  const deleteTemplate = (templateId) => {
    setTemplates((prev) => prev.filter((t) => t.id !== templateId));
  };
```

- [ ] **Step 4: Expose on the provider value**

Find this line (currently line 193):

```jsx
        duplicateChat,
```

Replace it with:

```jsx
        duplicateChat,
        templates,
        createTemplate,
        deleteTemplate,
```

- [ ] **Step 5: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: no new errors/warnings versus baseline.

- [ ] **Step 6: Commit**

```bash
git add chatbot-ui-vite/src/context/ChatContext.jsx
git commit -m "feat: add prompt template CRUD to ChatContext"
```

---

### Task 8: `HomePage.jsx` templates section + inline add form

**Files:**
- Modify: `chatbot-ui-vite/src/pragna/pages/HomePage.jsx:1` (imports), `:4` (consume context + local form state), `:121-122` (insert new section)

**Interfaces:**
- Consumes: `templates`, `createTemplate`, `deleteTemplate` from `ChatContext` (Task 7).

- [ ] **Step 1: Import `useContext` and `ChatContext`**

Find this line (currently line 1):

```jsx
import { useState } from 'react'
```

Replace it with:

```jsx
import { useContext, useState } from 'react'
import { ChatContext } from '../../context/ChatContext'
```

- [ ] **Step 2: Consume the context and add local form state**

Find this line (currently line 4):

```jsx
  const [tier, setTier] = useState('Basic')
```

Replace it with:

```jsx
  const [tier, setTier] = useState('Basic')
  const { templates, createTemplate, deleteTemplate } = useContext(ChatContext)
  const [addingTemplate, setAddingTemplate] = useState(false)
  const [newTemplateTitle, setNewTemplateTitle] = useState('')
  const [newTemplatePrompt, setNewTemplatePrompt] = useState('')
```

- [ ] **Step 3: Insert the "Your templates" section**

Find this block (currently lines 121-123, right after the Explore cards grid closes and before the footer):

```jsx
      </div>

      <div style={{ marginTop: '34px', fontSize: '12.5px', color: '#a89878', opacity: 0.7 }}>
```

Replace it with:

```jsx
      </div>

      {/* Your templates */}
      <div style={{ marginTop: '34px', width: '100%', maxWidth: 'min(90vw, 820px)' }}>
        <div style={{ fontSize: '13px', fontWeight: 650, letterSpacing: '1px', color: '#a89878', textTransform: 'uppercase', marginBottom: '14px' }}>
          Your templates
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 260px))', gap: '16px' }}>
          {templates.map((tpl) => (
            <button
              key={tpl.id}
              onClick={() => onUsePrompt(tpl.prompt)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '22px',
                borderRadius: '18px',
                textAlign: 'left',
                cursor: 'pointer',
                background: 'rgba(20,20,20,0.82)',
                border: '1px solid rgba(212,175,55,0.18)',
                backdropFilter: 'blur(8px)',
                boxShadow: '0 2px 8px rgba(0,0,0,0.28)',
                transition: 'all 0.18s ease',
                position: 'relative',
              }}
              className="hover:translate-y-[-3px] hover:shadow-[0_20px_32px_rgba(0,0,0,0.50)] hover:border-accent-500/50"
            >
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  deleteTemplate(tpl.id)
                }}
                title="Delete template"
                style={{ position: 'absolute', top: '12px', right: '12px', width: '22px', height: '22px', borderRadius: '6px', border: 'none', background: 'transparent', color: '#a89878', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                className="hover:bg-[#1e1a10] hover:text-[#e5c76b]"
              >
                ✕
              </button>
              <span style={{ fontSize: '16px', fontWeight: 650, color: '#f0e6d3' }}>{tpl.title}</span>
              <span style={{ fontSize: '13px', color: '#a89878', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{tpl.prompt}</span>
            </button>
          ))}

          {addingTemplate ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                padding: '22px',
                borderRadius: '18px',
                background: 'rgba(20,20,20,0.82)',
                border: '1px solid rgba(212,175,55,0.32)',
              }}
            >
              <input
                autoFocus
                value={newTemplateTitle}
                onChange={(e) => setNewTemplateTitle(e.target.value)}
                placeholder="Template name"
                style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #2d2a24', background: '#1a1a1a', color: '#f0e6d3', fontSize: '13.5px' }}
              />
              <textarea
                value={newTemplatePrompt}
                onChange={(e) => setNewTemplatePrompt(e.target.value)}
                placeholder="Prompt text"
                rows={3}
                style={{ padding: '8px 10px', borderRadius: '8px', border: '1px solid #2d2a24', background: '#1a1a1a', color: '#f0e6d3', fontSize: '13.5px', resize: 'vertical' }}
              />
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setAddingTemplate(false)
                    setNewTemplateTitle('')
                    setNewTemplatePrompt('')
                  }}
                  style={{ padding: '7px 14px', borderRadius: '8px', border: 'none', background: 'transparent', color: '#a89878', fontSize: '13px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    createTemplate(newTemplateTitle, newTemplatePrompt)
                    setAddingTemplate(false)
                    setNewTemplateTitle('')
                    setNewTemplatePrompt('')
                  }}
                  style={{ padding: '7px 14px', borderRadius: '8px', border: 'none', background: 'linear-gradient(135deg, #e5c76b, #b8860b)', color: '#0a0a0a', fontSize: '13px', fontWeight: 650, cursor: 'pointer' }}
                >
                  Save
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setAddingTemplate(true)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '22px',
                borderRadius: '18px',
                textAlign: 'center',
                cursor: 'pointer',
                background: 'transparent',
                border: '1px dashed rgba(212,175,55,0.3)',
                color: '#a89878',
                minHeight: '110px',
              }}
              className="hover:border-accent-500/50 hover:text-[#e5c76b]"
            >
              + Add template
            </button>
          )}
        </div>
      </div>

      <div style={{ marginTop: '34px', fontSize: '12.5px', color: '#a89878', opacity: 0.7 }}>
```

- [ ] **Step 4: Build and lint**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: no new errors/warnings versus baseline.

- [ ] **Step 5: Manually verify**

Run `npm run dev`, go to the Explore/home page, click "+ Add template", fill in a name and prompt, click Save — confirm a new template card appears. Click the new card — confirm it sends that prompt as a message immediately (same as the fixed suggestion cards). Click the "✕" on a template card — confirm it's removed. Reload the page — confirm saved templates persist.

- [ ] **Step 6: Commit**

```bash
git add chatbot-ui-vite/src/pragna/pages/HomePage.jsx
git commit -m "feat: add prompt template library to the home page"
```
