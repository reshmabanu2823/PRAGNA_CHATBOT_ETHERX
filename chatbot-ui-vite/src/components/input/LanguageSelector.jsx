import { useContext } from "react";
import { ChatContext } from "../../context/ChatContext";
import { SUPPORTED_LANGUAGE_OPTIONS, normalizeLanguageCode } from "../../utils/language";

export default function LanguageSelector() {
  const { language, setLanguage } = useContext(ChatContext);

  return (
    <select
      className="language-select"
      value={normalizeLanguageCode(language)}
      onChange={(e) => setLanguage(normalizeLanguageCode(e.target.value))}
    >
      {SUPPORTED_LANGUAGE_OPTIONS.map((item) => (
        <option key={item.code} value={item.code}>
          {item.label}
        </option>
      ))}
    </select>
  );
}

