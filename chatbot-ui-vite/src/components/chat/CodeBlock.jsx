import { useState } from "react";

const CopyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

export default function CodeBlock({ code, language = "python" }) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const languageMap = {
    python: "py",
    javascript: "js",
    jsx: "jsx",
    typescript: "ts",
    tsx: "tsx",
    html: "html",
    css: "css",
    sql: "sql",
    bash: "bash",
    shell: "sh",
    json: "json",
  };

  const displayLang = languageMap[language.toLowerCase()] || language.toLowerCase() || "code";

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-block-lang">{displayLang}</span>
        <button
          className="code-block-copy-btn"
          onClick={copyToClipboard}
          title={copied ? "Copied!" : "Copy code"}
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
          <span className="code-block-copy-text">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className={`code-block-pre language-${language}`}>
        <code>{code}</code>
      </pre>
    </div>
  );
}
