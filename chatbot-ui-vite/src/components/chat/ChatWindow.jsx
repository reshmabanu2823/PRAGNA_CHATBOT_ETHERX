import { useContext, useCallback } from "react";
import { ChatContext } from "../../context/ChatContext";
import { generateAIImage, sendOrchestratedMessage } from "../../api/api";
import MessageBubble from "./MessageBubble";
import ChatModeSelector from "./ChatModeSelector";
import { normalizeLanguageCode } from "../../utils/language";

const IMAGE_REQUEST_RE = /(create|generate|make|design)\s+(an?\s+)?(ai\s+)?image|image\s+of|illustration\s+of|poster\s+of|logo\s+of/i;

const extractImagePrompt = (text) => {
  const raw = (text || "").trim();
  if (!raw) return "";
  return raw
    .replace(/^(please\s+)?(create|generate|make|design)\s+(an?\s+)?(ai\s+)?(image|picture|photo|illustration)\s+(of|for)?\s*/i, "")
    .trim() || raw;
};

export default function ChatWindow() {
  const { chats, setChats, activeChatId, setActiveChatId, language, isLoading, setIsLoading, chatMode } = useContext(ChatContext);
  const chat = chats.find((c) => c.id === activeChatId);

  // Mode display name
  const getModeDisplayName = (mode) => {
    const modeNames = {
      general: "General Chat",
      explain_concepts: "Explain Concepts",
      generate_ideas: "Brainstorm Ideas",
      write_content: "Writing Assistant",
      code_assistance: "Code Help",
      ask_questions: "Curious Questions",
      creative_writing: "Storytelling",
    };
    return modeNames[mode] || mode;
  };

  // Send suggestion message to backend
  const sendSuggestionMessage = useCallback(async (suggestion) => {
    if (isLoading) return;

    let targetChatId = activeChatId;
    let currentChat = chat;

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

    // Add user message to chat
    const updatedMessages = [
      ...currentChat.messages,
      { sender: "user", text: suggestion, attachments: [] },
    ];
    const botMsg = { sender: "bot", text: "", isStreaming: true };

    setChats((prev) =>
      prev.map((c) =>
        c.id === targetChatId ? { ...c, messages: [...updatedMessages, botMsg] } : c
      )
    );
    setIsLoading(true);

    try {
      if (IMAGE_REQUEST_RE.test(suggestion)) {
        const imageResult = await generateAIImage({
          prompt: extractImagePrompt(suggestion),
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
    } finally {
      setIsLoading(false);
    }
  }, [activeChatId, chat, isLoading, language, setChats, setActiveChatId, setIsLoading, chatMode]);

  if (!chat || chat.messages.length === 0) {
    const suggestions = [
      {
        title: "Create image",
        description: "Generate visuals from text prompts",
        prompt: "Create an image concept for a futuristic city at sunrise",
      },
      {
        title: "Follow sports",
        description: "Live scores and quick match updates",
        prompt: "Give me the latest sports headlines and score updates",
      },
      {
        title: "Write content",
        description: "Draft posts, scripts, and copy",
        prompt: "Write a LinkedIn post about practical AI adoption in business",
      },
      {
        title: "Code help",
        description: "Debugging and implementation support",
        prompt: "Help me optimize a slow Flask API endpoint step-by-step",
      },
      {
        title: "Research mode",
        description: "Summaries with context and action points",
        prompt: "Summarize today's key AI policy updates with implications",
      },
      {
        title: "Brainstorm",
        description: "Generate strategic ideas quickly",
        prompt: "Give 10 startup ideas at the intersection of AI and sports",
      },
    ];

    return (
      <div className="chat-window" style={{ justifyContent: "center" }}>
        <div className="empty studio-empty">
          <h2 className="studio-title">Hi, where should we start?</h2>
          <p className="studio-subtitle">
            Explore, create, or ask anything. Your current mode is {getModeDisplayName(chatMode)}.
          </p>
          <p className="studio-subtitle" style={{ marginTop: "0.35rem" }}>
            Pick a quick starter below, or type your own prompt.
          </p>

          <div className="studio-mode-wrap">
            <ChatModeSelector />
          </div>

          <div className="studio-suggestion-grid">
            {suggestions.map((item) => (
              <button
                key={item.title}
                className="studio-suggestion-card"
                onClick={() => sendSuggestionMessage(item.prompt)}
                disabled={isLoading}
              >
                <span className="studio-suggestion-title">{item.title}</span>
                <span className="studio-suggestion-description">{item.description}</span>
              </button>
            ))}
          </div>

          <p className="studio-footer-note">
            Powered by advanced AI. Responses may vary.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-window">
      {chat.messages.map((m, i) => (
        <MessageBubble key={i} message={m} language={language} />
      ))}
    </div>
  );
}
