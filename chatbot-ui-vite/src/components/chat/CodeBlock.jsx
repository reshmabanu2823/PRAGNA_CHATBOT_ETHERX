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
    <div className="rounded-[14px] overflow-hidden border border-border shadow-premium-md">
      <div className="flex items-center justify-between px-4 py-[9px] bg-surface-subtle border-b border-border">
        <span
          className="text-[12px] font-semibold uppercase tracking-[0.8px]"
          style={{ color: "var(--pragna-gold)" }}
        >
          {displayLang}
        </span>
        <button
          className="flex items-center gap-1.5 rounded-[7px] border border-border bg-transparent px-[11px] py-1 text-[12px] transition-colors duration-150 text-[color:var(--pragna-text-muted)] hover:text-accent-400 hover:border-accent-500/35"
          onClick={copyToClipboard}
          title={copied ? "Copied!" : "Copy code"}
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
          <span className="hidden sm:inline">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre
        className={`m-0 overflow-x-auto px-[18px] py-4 font-mono text-[13.5px] leading-[1.6] language-${language}`}
        style={{ background: "#101010", color: "#e8dcc0" }}
      >
        <code className="font-inherit text-inherit bg-transparent p-0">{code}</code>
      </pre>
    </div>
  );
}
