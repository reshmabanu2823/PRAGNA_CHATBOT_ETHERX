import { useContext } from "react";
import { ChatContext } from "../../context/ChatContext";
import { SUPPORTED_LANGUAGE_OPTIONS, normalizeLanguageCode } from "../../utils/language";

export default function LanguageSelector() {
  const { language, setLanguage } = useContext(ChatContext);

  return (
    <div className="group relative flex h-10 shrink-0 items-center rounded-xl transition-colors duration-150 hover:bg-surface-subtle">
      <select
        className="h-10 cursor-pointer appearance-none rounded-xl border-none bg-transparent pl-3.5 pr-7 text-[13px] font-semibold transition-colors duration-150 group-hover:text-accent-400 focus:outline-none"
        style={{ color: "var(--pragna-text-muted)" }}
        value={normalizeLanguageCode(language)}
        onChange={(e) => setLanguage(normalizeLanguageCode(e.target.value))}
        title="Language"
      >
        {SUPPORTED_LANGUAGE_OPTIONS.map((item) => (
          <option 
            key={item.code} 
            value={item.code} 
            style={{ backgroundColor: "#1e1e1e", color: "#ffffff" }}
          >
            {item.label}
          </option>
        ))}
      </select>
      <svg
        className="pointer-events-none absolute right-2.5 h-[11px] w-[11px] transition-colors duration-150 group-hover:text-accent-400"
        style={{ color: "var(--pragna-text-muted)" }}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>
  );
}

