import { useEffect, useState } from "react";
import etherxLogo from "../assets/etherx-logo.png";
import pragnaLogoFull from "../assets/pragna-logo-full.png";

// Full 8-frame sequence from the "Pragna Splash screen" Figma file, in canvas
// order (left to right): EtherX intro -> Hindi -> Kannada -> Telugu -> Tamil
// -> English (full Pragna wordmark) -> EtherX ending -> closing tagline.
//
// Two background elements tie the frames together, exactly as in the file:
// - a huge gold triangle ("Polygon 1") whose x position slides further left
//   on every frame (1043 -> 642 -> 326 -> 120 -> -134 -> -268 -> -270 on the
//   1440px canvas), so its visible sliver morphs from a top-right corner
//   accent into a full-width top band;
// - a #c9b037 rectangle anchored top-right that appears from the Kannada
//   frame onward, filling the gap the triangle leaves as it exits left.
//
// Regional titles render in per-script Noto fonts (single combined stylesheet
// loaded on mount); title color #a07c31 and white subtitles per the file.

const GOLD_BAND = "#c9b037";
const GOLD_TITLE = "#a07c31";

const FONT_URL =
  "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@700&family=Noto+Sans+Kannada:wght@700&family=Noto+Sans+Telugu:wght@700&family=Noto+Sans+Tamil:wght@700&display=swap";

// polygonLeft values are the Figma x offsets converted to vw (x / 1440 * 100).
const FRAMES = [
  { id: "intro", duration: 900, polygonLeft: 72.4, band: false, kind: "logo" },
  { id: "hi", duration: 800, polygonLeft: 44.6, band: false, kind: "lang", title: "प्रज्ञा-1 A", subtitle: "एक क्षेत्रीय चैटबॉट", font: "'Noto Sans Devanagari', sans-serif" },
  { id: "kn", duration: 800, polygonLeft: 22.6, band: true, kind: "lang", title: "ಪ್ರಜ್ಞಾ-1 A", subtitle: "ಒಂದು ಪ್ರಾದೇಶಿಕ ಚಾಟ್‌ಬಾಟ್", font: "'Noto Sans Kannada', sans-serif" },
  { id: "te", duration: 800, polygonLeft: 8.3, band: true, kind: "lang", title: "ప్రజ్ఞ 1 A", subtitle: "ఒక ప్రాంతీయ చాట్‌బాట్", font: "'Noto Sans Telugu', sans-serif" },
  { id: "ta", duration: 800, polygonLeft: -9.3, band: true, kind: "lang", title: "பிரக்ஞா 1 A", subtitle: "ஒரு பிராந்திய சாட்பாட்", font: "'Noto Sans Tamil', sans-serif" },
  { id: "en", duration: 1000, polygonLeft: -18.6, band: true, kind: "pragna" },
  { id: "ending", duration: 800, polygonLeft: -18.75, band: true, kind: "logo" },
  { id: "tagline", duration: 1300, polygonLeft: -40, band: false, kind: "tagline" },
];

// App.jsx imports these so its dismissal timers always match the sequence.
export const SPLASH_TOTAL_MS = FRAMES.reduce((sum, f) => sum + f.duration, 0);
export const SPLASH_FADE_MS = 500;

export default function SplashScreen({ visible = true }) {
  const [frameIndex, setFrameIndex] = useState(0);

  // Load the regional-script fonts once for the whole sequence.
  useEffect(() => {
    const link = document.createElement("link");
    link.href = FONT_URL;
    link.rel = "stylesheet";
    document.head.appendChild(link);
    return () => {
      try {
        document.head.removeChild(link);
      } catch {
        // already removed
      }
    };
  }, []);

  // Advance one frame at a time; each timeout depends only on frameIndex, so
  // parent re-renders can't reset the sequence.
  useEffect(() => {
    if (frameIndex >= FRAMES.length - 1) return undefined;
    const t = setTimeout(() => setFrameIndex((i) => i + 1), FRAMES[frameIndex].duration);
    return () => clearTimeout(t);
  }, [frameIndex]);

  const frame = FRAMES[frameIndex];
  const isTagline = frame.kind === "tagline";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "#000",
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: visible ? 1 : 0,
        transition: `opacity ${SPLASH_FADE_MS}ms ease`,
        pointerEvents: visible ? "auto" : "none",
      }}
    >
      <style>{`
        @keyframes splashFrameIn {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Polygon 1 - the gold triangle sweeping left across the sequence */}
      <div
        style={{
          position: "absolute",
          top: "-56.3vh",
          left: `${frame.polygonLeft}vw`,
          width: "104.7vw",
          height: "74.9vh",
          background: GOLD_BAND,
          clipPath: "polygon(50% 0%, 0% 100%, 100% 100%)",
          opacity: isTagline ? 0 : 1,
          transition: "left 0.7s ease-in-out, opacity 0.5s ease",
        }}
      />

      {/* Rectangle 1 - top-right band, present from the Kannada frame on */}
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: "41.8vw",
          height: "18.6vh",
          background: GOLD_BAND,
          opacity: frame.band && !isTagline ? 1 : 0,
          transition: "opacity 0.7s ease",
        }}
      />

      {/* Center content - keyed per frame so each one animates in fresh */}
      <div
        key={frame.id}
        style={{
          position: "relative",
          zIndex: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          animation: "splashFrameIn 0.35s ease",
        }}
      >
        {frame.kind === "logo" && (
          <img
            src={etherxLogo}
            alt="EtherX Innovations"
            style={{
              width: "clamp(110px, 11.25vw, 162px)",
              height: "clamp(110px, 11.25vw, 162px)",
              objectFit: "contain",
              filter: "drop-shadow(0 0 20px rgba(212, 175, 55, 0.35))",
            }}
          />
        )}

        {frame.kind === "lang" && (
          <div style={{ display: "flex", alignItems: "center", gap: "clamp(16px, 2vw, 28px)" }}>
            <img
              src={etherxLogo}
              alt=""
              style={{
                width: "clamp(96px, 11.25vw, 162px)",
                height: "clamp(96px, 11.25vw, 162px)",
                objectFit: "contain",
                filter: "drop-shadow(0 0 20px rgba(212, 175, 55, 0.35))",
              }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <span
                style={{
                  fontFamily: frame.font,
                  fontWeight: 700,
                  fontSize: "clamp(34px, 4.4vw, 64px)",
                  lineHeight: 1.15,
                  color: GOLD_TITLE,
                  whiteSpace: "nowrap",
                }}
              >
                {frame.title}
              </span>
              <span
                style={{
                  fontFamily: frame.font,
                  fontWeight: 400,
                  fontSize: "clamp(15px, 1.7vw, 24px)",
                  color: "#fff",
                  whiteSpace: "nowrap",
                }}
              >
                {frame.subtitle}
              </span>
            </div>
          </div>
        )}

        {frame.kind === "pragna" && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
            <img
              src={pragnaLogoFull}
              alt="Pragna-1 A"
              style={{
                width: "clamp(300px, 40.7vw, 586px)",
                objectFit: "contain",
                filter: "drop-shadow(0 0 24px rgba(212, 175, 55, 0.3))",
              }}
            />
            <span
              style={{
                fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
                fontWeight: 700,
                fontSize: "clamp(15px, 1.7vw, 24px)",
                color: "#fff",
                marginTop: "-24px",
              }}
            >
              A regional chatbot
            </span>
          </div>
        )}

        {frame.kind === "tagline" && (
          <div style={{ display: "flex", alignItems: "center", gap: "clamp(16px, 2vw, 24px)" }}>
            <img
              src={etherxLogo}
              alt=""
              style={{
                width: "clamp(110px, 11.25vw, 162px)",
                height: "clamp(110px, 11.25vw, 162px)",
                objectFit: "contain",
                filter: "drop-shadow(0 0 20px rgba(212, 175, 55, 0.35))",
              }}
            />
            <span
              style={{
                fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
                fontWeight: 700,
                fontSize: "clamp(16px, 2.2vw, 32px)",
                letterSpacing: "1px",
                color: GOLD_BAND,
                whiteSpace: "nowrap",
              }}
            >
              A PRODUCT OF ETHERX INNOVATIONS
            </span>
          </div>
        )}
      </div>

      {/* Persistent bottom-right wordmark - hidden only on the final frame */}
      <div
        style={{
          position: "absolute",
          right: "2.5vw",
          bottom: "3.5vh",
          fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
          fontWeight: 700,
          fontSize: "clamp(16px, 2.2vw, 32px)",
          letterSpacing: "0.5px",
          color: GOLD_BAND,
          opacity: isTagline ? 0 : 1,
          transition: "opacity 0.4s ease",
          zIndex: 2,
        }}
      >
        ETHERX INNOVATIONS
      </div>
    </div>
  );
}
