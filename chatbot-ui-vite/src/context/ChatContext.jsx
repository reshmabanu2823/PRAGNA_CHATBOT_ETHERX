import { createContext, useState, useEffect, useRef } from "react";
import { normalizeLanguageCode } from "../utils/language";

export const ChatContext = createContext();

const isMobile = () =>
  typeof window !== "undefined" && window.innerWidth <= 768;

export function ChatProvider({ children }) {
  const [chats, setChats] = useState(() => {
    const saved = localStorage.getItem("pragna_chats");
    return saved ? JSON.parse(saved) : [];
  });

  const [activeChatId, setActiveChatId] = useState(() => {
    const saved = localStorage.getItem("pragna_active_chat_id");
    return saved || null;
  });

  const [language, setLanguage] = useState(() => {
    return normalizeLanguageCode(localStorage.getItem("pragna_language") || "en");
  });

  const setNormalizedLanguage = (nextLanguage) => {
    setLanguage(normalizeLanguageCode(nextLanguage));
  };

  const [isLoading, setIsLoading] = useState(false);

  // Sidebar: closed by default on mobile, open on desktop
  const [sidebarOpen, setSidebarOpen] = useState(() => !isMobile());

  const [user, setUser] = useState(null);

  const [chatMode, setChatMode] = useState(() => {
    return localStorage.getItem("pragna_chat_mode") || "general";
  });

  // Ref to input field for focusing when mode is selected
  const inputRef = useRef(null);

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

  // Save chat mode
  useEffect(() => {
    localStorage.setItem("pragna_chat_mode", chatMode);
  }, [chatMode]);

  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem("pragna_active_chat_id", activeChatId);
    } else {
      localStorage.removeItem("pragna_active_chat_id");
    }
  }, [activeChatId]);

  useEffect(() => {
    localStorage.setItem("pragna_language", language);
  }, [language]);

  // Auto-initialize first chat if none exist
  useEffect(() => {
    if (!activeChatId && chats.length > 0) {
      setActiveChatId(chats[0].id);
    }
  }, []);

  const newChat = () => {
    const chat = {
      id: Date.now().toString(),
      title: "New chat",
      messages: [],
    };
    setChats((prev) => [chat, ...prev]);
    setActiveChatId(chat.id);
  };

  const toggleSidebar = () => {
    setSidebarOpen((prev) => !prev);
  };

  const login = (name, email) => {
    setUser({ name, email });
  };

  const logout = () => {
    setUser(null);
  };

  const deleteChat = (chatId) => {
    setChats((prev) => prev.filter((c) => c.id !== chatId));
    if (activeChatId === chatId) {
      setActiveChatId(null);
    }
  };

  return (
    <ChatContext.Provider
      value={{
        chats,
        setChats,
        activeChatId,
        setActiveChatId,
        newChat,
        language,
        setLanguage: setNormalizedLanguage,
        isLoading,
        setIsLoading,
        sidebarOpen,
        toggleSidebar,
        user,
        login,
        logout,
        deleteChat,
        chatMode,
        setChatMode,
        inputRef,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}
