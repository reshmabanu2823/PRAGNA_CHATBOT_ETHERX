import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

// Password <input> with a show/hide toggle. Renders a wrapper div in place of
// the bare input, so it drops into flex-column forms (auth.css's
// `.auth-box form` and SettingsModal's inline flex-column rows both use
// `align-items: stretch`, which is what makes the input full-width here too).
export default function PasswordInput({
  style,
  wrapperStyle,
  className,
  toggleTitle,
  ...inputProps
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div style={{ position: "relative", width: "100%", ...wrapperStyle }}>
      <input
        {...inputProps}
        type={visible ? "text" : "password"}
        className={className}
        style={{ width: "100%", paddingRight: "42px", ...style }}
      />
      <button
        type="button"
        onClick={() => setVisible((prev) => !prev)}
        title={toggleTitle || (visible ? "Hide password" : "Show password")}
        tabIndex={-1}
        style={{
          position: "absolute",
          right: "4px",
          top: "50%",
          transform: "translateY(-50%)",
          width: "32px",
          height: "32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          border: "none",
          background: "transparent",
          color: "var(--pragna-text-muted, rgba(255,255,255,0.5))",
          cursor: "pointer",
          borderRadius: "6px",
        }}
        className="hover:text-[var(--pragna-gold-soft)]"
      >
        {visible ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </div>
  );
}
