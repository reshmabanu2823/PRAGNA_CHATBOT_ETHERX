import { useContext, useState, useRef, useCallback, useEffect } from "react";
import { ChatContext } from "../../context/ChatContext";
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedUploadMessage } from "../../api/api";
import LanguageSelector from "./LanguageSelector";
import { normalizeLanguageCode } from "../../utils/language";

// BCP-47 tags for SpeechRecognition
const LANG_TAG = {
  en: "en-US", hi: "hi-IN", kn: "kn-IN", te: "te-IN",
  ta: "ta-IN", ml: "ml-IN", mr: "mr-IN", bn: "bn-IN",
  gu: "gu-IN", pa: "pa-IN", ur: "ur-PK",
};

const IMAGE_REQUEST_RE = /(create|generate|make|design)\s+(an?\s+)?(ai\s+)?image|image\s+of|illustration\s+of|poster\s+of|logo\s+of/i;

const extractImagePrompt = (text) => {
  const raw = (text || "").trim();
  if (!raw) return "";
  return raw
    .replace(/^(please\s+)?(create|generate|make|design)\s+(an?\s+)?(ai\s+)?(image|picture|photo|illustration)\s+(of|for)?\s*/i, "")
    .trim() || raw;
};

// Generate smart title from user input and AI response
const generateChatTitle = (userMessage, aiResponse) => {
  if (!userMessage && !aiResponse) return "New Chat";
  
  // Combine messages
  const combined = (userMessage + " " + aiResponse).toLowerCase();
  
  // Remove punctuation and extra spaces
  let cleaned = combined.replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  
  // Stop words to remove
  const stopWords = new Set([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'and', 'or', 'but', 'in', 'on',
    'at', 'to', 'from', 'for', 'of', 'with', 'by', 'it', 'you', 'i', 'that',
    'this', 'your', 'my', 'we', 'they', 'them', 'their', 'what', 'which',
    'when', 'where', 'why', 'how', 'if', 'as', 'just', 'so', 'than'
  ]);
  
  // Extract meaningful words
  const words = cleaned
    .split(" ")
    .filter(w => w && !stopWords.has(w) && w.length > 2);
  
  // Build title from first 5 key words
  const title = words.slice(0, 5).join(" ");
  
  if (!title || title.length < 3) {
    return userMessage.slice(0, 40).replace(/[^\w\s]/g, " ").trim() || "New Chat";
  }
  
  // Capitalize first letter
  return title.charAt(0).toUpperCase() + title.slice(1);
};

export default function InputBar() {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const recognitionRef = useRef(null);
  const attachMenuRef = useRef(null);
  const imageInputRef = useRef(null);
  const videoInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const {
    chats, setChats, activeChatId, setActiveChatId,
    language, isLoading, setIsLoading, chatMode, inputRef,
  } = useContext(ChatContext);

  const activeChat = chats.find((c) => c.id === activeChatId);

  // Update chat title when it's still "New chat" (after first response)
  useEffect(() => {
    const chat = chats.find(c => c.title === "New chat" && c.messages.length > 1);
    if (chat) {
      const userMsg = chat.messages.find(m => m.sender === "user")?.text || "";
      const botMsg = chat.messages.find(m => m.sender === "bot")?.text || "";
      
      if (userMsg && botMsg) {
        const summary = generateChatTitle(userMsg, botMsg);
        if (summary !== "New chat") {
          setChats(prev => prev.map(c => 
            c.id === chat.id ? { ...c, title: summary } : c
          ));
        }
      }
    }
  }, [chats, setChats]);

  // Close attachment menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (attachMenuRef.current && !attachMenuRef.current.contains(e.target)) {
        setAttachMenuOpen(false);
      }
    };
    if (attachMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [attachMenuOpen]);

  // Handle file picked from any input
  const handleFilePick = (e, type) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    const newAttachments = files.map((file) => ({
      file,
      type, // 'image' | 'video' | 'file'
      name: type === "folder" ? (file.webkitRelativePath || file.name) : file.name,
      relativePath: file.webkitRelativePath || file.name,
      previewUrl: (type === "image" || type === "video") && !file.webkitRelativePath
        ? URL.createObjectURL(file)
        : null,
    }));
    setAttachments((prev) => [...prev, ...newAttachments]);
    setAttachMenuOpen(false);
    // Reset input so same file can be re-picked
    e.target.value = "";
  };

  const removeAttachment = (index) => {
    setAttachments((prev) => {
      const updated = [...prev];
      if (updated[index].previewUrl) {
        URL.revokeObjectURL(updated[index].previewUrl);
      }
      updated.splice(index, 1);
      return updated;
    });
  };

  // ─── Helper: send a text message via streaming ───────────────────────────
  const handleSendMessage = useCallback(async (msgText, msgAttachments = []) => {
    const hasContent = msgText.trim() || msgAttachments.length > 0;
    if (!hasContent || isLoading) return;

    // Build text with attachment context for the AI
    let fullText = msgText.trim();
    if (msgAttachments.length > 0) {
      const fileNames = msgAttachments.map((a) => a.relativePath || a.name).join(", ");
      fullText = fullText
        ? `${fullText}\n[Attached: ${fileNames}]`
        : `[Attached: ${fileNames}]`;
    }

    let targetChatId = activeChatId;
    let currentChat = activeChat;

    // Auto-create chat if none active
    if (!targetChatId || !currentChat) {
      const newId = Date.now().toString();
      const newChatObj = {
        id: newId,
        title: "New chat",
        messages: [],
      };
      setChats((prev) => [newChatObj, ...prev]);
      setActiveChatId(newId);
      targetChatId = newId;
      currentChat = newChatObj;
    }

    // Attachment metadata for display (store safe serializable data)
    const attachmentMeta = msgAttachments.map((a) => ({
      name: a.name,
      type: a.type,
      relativePath: a.relativePath,
      previewUrl: a.previewUrl, // objectURL — valid for this session
    }));

    const updatedMessages = [
      ...currentChat.messages,
      { sender: "user", text: msgText.trim(), attachments: attachmentMeta },
    ];
    const botMsg = { sender: "bot", text: "", isStreaming: true };

    setChats((prev) =>
      prev.map((c) =>
        c.id === targetChatId ? { ...c, messages: [...updatedMessages, botMsg] } : c
      )
    );
    setIsLoading(true);

    try {
      const normalizedLanguage = normalizeLanguageCode(language);
      const isImageRequest = IMAGE_REQUEST_RE.test(msgText) && msgAttachments.length === 0;

      if (isImageRequest) {
        const imagePrompt = extractImagePrompt(msgText);
        const imageResult = await generateAIImage({
          prompt: imagePrompt,
          style: "cinematic",
          quality: "hd",
          size: "1024x1024",
        });

        setIsLoading(false);
        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? {
                          ...m,
                          text: "Generated image ready.",
                          isStreaming: false,
                          attachments: [
                            {
                              name: `generated-${Date.now()}.png`,
                              type: "image",
                              previewUrl: imageResult.image,
                            },
                          ],
                        }
                      : m
                  ),
                }
              : c
          )
        );
        return;
      }

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
          const fallbackText = `${fullText}\n[Note: Attachment parsing endpoint unavailable. Analyze using filenames/context and ask for pasted file content if needed.]`;
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
    } catch (err) {
      console.error("API error:", err);
      setIsLoading(false);

      const errorMessage = "Server error. Please try again.";
      setChats((prev) =>
        prev.map((c) =>
          c.id === targetChatId
            ? {
                ...c,
                messages: c.messages.map((m, idx) =>
                  idx === c.messages.length - 1
                    ? {
                        ...m,
                        text: errorMessage,
                        isStreaming: false,
                        error: true,
                      }
                    : m
                ),
              }
            : c
        )
      );
    }
  }, [activeChatId, activeChat, chats, isLoading, language, setChats, setActiveChatId, setIsLoading]);

  // ─── Text send ───────────────────────────────────────────────────────────
  const send = () => {
    handleSendMessage(text, attachments);
    setText("");
    setAttachments([]);
  };

  // ─── Voice input via SpeechRecognition ──────────────────────────────────
  const toggleMic = () => {
    if (recording) {
      recognitionRef.current?.stop();
      setRecording(false);
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Your browser doesn't support voice input. Please use Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    const normalizedLanguage = normalizeLanguageCode(language);
    recognition.lang = LANG_TAG[normalizedLanguage] || "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    let finalTranscript = "";

    recognition.onstart = () => setRecording(true);

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += t;
        } else {
          interim += t;
        }
      }
      setText(finalTranscript + interim);
    };

    recognition.onend = () => {
      setRecording(false);
      recognitionRef.current = null;
      if (finalTranscript.trim()) {
        handleSendMessage(finalTranscript.trim(), attachments);
        setText("");
        setAttachments([]);
      }
    };

    recognition.onerror = (e) => {
      console.error("SpeechRecognition error:", e.error);
      setRecording(false);
      recognitionRef.current = null;
      if (e.error === "not-allowed") {
        alert("Microphone access denied. Please allow microphone access in your browser.");
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const hasContent = text.trim() || attachments.length > 0;

  return (
    <div className="input-bar-wrapper">
      {/* ── Attachment preview strip ── */}
      {attachments.length > 0 && (
        <div className="attachment-preview-strip">
          {attachments.map((att, i) => (
            <div className="attachment-chip" key={i}>
              {att.type === "image" && att.previewUrl ? (
                <img src={att.previewUrl} alt={att.name} className="chip-thumb" />
              ) : att.type === "video" ? (
                <span className="chip-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <rect x="2" y="5" width="15" height="14" rx="2"/>
                    <path d="M17 9l5-3v12l-5-3V9z"/>
                  </svg>
                </span>
              ) : (
                <span className="chip-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="9" y1="13" x2="15" y2="13"/>
                    <line x1="9" y1="17" x2="13" y2="17"/>
                  </svg>
                </span>
              )}
              <span className="chip-name">{att.name}</span>
              <button
                className="chip-remove"
                onClick={() => removeAttachment(i)}
                title="Remove"
              >✕</button>
            </div>
          ))}
        </div>
      )}

      <div className="input-bar">
        {/* Hidden file inputs */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => handleFilePick(e, "image")}
        />
        <input
          ref={videoInputRef}
          type="file"
          accept="video/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => handleFilePick(e, "video")}
        />
        <input
          ref={fileInputRef}
          type="file"
          multiple
          style={{ display: "none" }}
          onChange={(e) => handleFilePick(e, "file")}
        />
        <input
          ref={folderInputRef}
          type="file"
          multiple
          webkitdirectory=""
          directory=""
          style={{ display: "none" }}
          onChange={(e) => handleFilePick(e, "folder")}
        />

        {/* ── + Attach button with popup ── */}
        <div className="attach-wrap" ref={attachMenuRef}>
          <button
            className="attach-btn"
            onClick={() => setAttachMenuOpen((o) => !o)}
            title="Add attachment"
          >
            <svg width="1.25em" height="1.25em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>

          {attachMenuOpen && (
            <div className="attach-popup">
              <button
                className="attach-popup-item"
                onClick={() => imageInputRef.current?.click()}
              >
                <span className="popup-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <rect x="3" y="3" width="18" height="18" rx="3"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <path d="M21 15l-5-5L5 21"/>
                  </svg>
                </span>
                <span>Image</span>
              </button>
              <button
                className="attach-popup-item"
                onClick={() => videoInputRef.current?.click()}
              >
                <span className="popup-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <rect x="2" y="5" width="15" height="14" rx="2"/>
                    <path d="M17 9l5-3v12l-5-3V9z"/>
                  </svg>
                </span>
                <span>Video</span>
              </button>
              <button
                className="attach-popup-item"
                onClick={() => fileInputRef.current?.click()}
              >
                <span className="popup-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="9" y1="13" x2="15" y2="13"/>
                    <line x1="9" y1="17" x2="13" y2="17"/>
                  </svg>
                </span>
                <span>File</span>
              </button>
              <button
                className="attach-popup-item"
                onClick={() => folderInputRef.current?.click()}
              >
                <span className="popup-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>
                  </svg>
                </span>
                <span>Folder</span>
              </button>
            </div>
          )}
        </div>

        <div className="input-language">
          <LanguageSelector />
        </div>

        <textarea
          ref={inputRef}
          className="text-input"
          placeholder={recording ? "Listening…" : "Ask anything..."}
          value={text}
          disabled={isLoading}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          rows={1}
        />

        <button
          className={`mic-btn${recording ? " recording" : ""}`}
          onClick={toggleMic}
          disabled={isLoading}
          title={recording ? "Stop recording" : "Voice input"}
        >
          {recording ? (
            <svg width="1.125em" height="1.125em" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2"></rect>
            </svg>
          ) : (
            <svg width="1.125em" height="1.125em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          )}
        </button>

        <button
          className="send-btn"
          onClick={send}
          disabled={isLoading || !hasContent}
          title="Send message"
        >
          <svg width="1.125em" height="1.125em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  );
}
