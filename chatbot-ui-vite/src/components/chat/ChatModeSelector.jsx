import { useContext } from "react";
import { ChatContext } from "../../context/ChatContext";
import "../../styles/chat_modes.css";

const CHAT_MODES = [
  {
    id: "general",
    label: "General",
    description: "Standard helpful assistant",
  },
  {
    id: "explain_concepts",
    label: "Explain",
    description: "Break down complex ideas",
  },
  {
    id: "generate_ideas",
    label: "Ideas",
    description: "Creative brainstorming",
  },
  {
    id: "write_content",
    label: "Write",
    description: "Professional writing",
  },
  {
    id: "code_assistance",
    label: "Code",
    description: "Programming help",
  },
  {
    id: "ask_questions",
    label: "Questions",
    description: "Curious inquiry",
  },
  {
    id: "creative_writing",
    label: "Story",
    description: "Storytelling & narrative",
  },
];

export default function ChatModeSelector() {
  const { chatMode, setChatMode, inputRef } = useContext(ChatContext);

  const handleModeSelect = (modeId) => {
    // Set the chat mode
    setChatMode(modeId);

    // Focus input field after a brief delay to let state update
    setTimeout(() => {
      if (inputRef?.current) {
        inputRef.current.focus();
      }
    }, 100);
  };

  return (
    <div className="chat-mode-selector">
      <div className="chat-mode-label">Chat Mode:</div>
      <div className="chat-mode-buttons">
        {CHAT_MODES.map((mode) => (
          <button
            key={mode.id}
            className={`chat-mode-btn ${chatMode === mode.id ? "active" : ""}`}
            onClick={() => handleModeSelect(mode.id)}
            title={mode.description}
            aria-pressed={chatMode === mode.id}
          >
            <span className="mode-label">{mode.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
