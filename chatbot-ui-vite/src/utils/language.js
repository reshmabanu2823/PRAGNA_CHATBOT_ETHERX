export const SUPPORTED_LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "kn", label: "Kannada" },
  { code: "ml", label: "Malayalam" },
  { code: "mr", label: "Marathi" },
  { code: "gu", label: "Gujarati" },
  { code: "pa", label: "Punjabi" },
  { code: "bn", label: "Bengali" },
  { code: "ur", label: "Urdu" },
];

const VALID_CODES = new Set(SUPPORTED_LANGUAGE_OPTIONS.map((item) => item.code));

const ALIASES = {
  english: "en",
  hindi: "hi",
  tamil: "ta",
  telugu: "te",
  kannada: "kn",
  malayalam: "ml",
  marathi: "mr",
  gujarati: "gu",
  punjabi: "pa",
  bengali: "bn",
  bangla: "bn",
  urdu: "ur",
  "en-us": "en",
  "en-gb": "en",
  "hi-in": "hi",
  "ta-in": "ta",
  "te-in": "te",
  "kn-in": "kn",
  "ml-in": "ml",
  "mr-in": "mr",
  "gu-in": "gu",
  "pa-in": "pa",
  "bn-in": "bn",
  "ur-pk": "ur",
};

export function normalizeLanguageCode(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) return "en";

  if (VALID_CODES.has(raw)) return raw;

  const compact = raw.replace(/_/g, "-");
  if (VALID_CODES.has(compact)) return compact;

  if (ALIASES[compact]) return ALIASES[compact];

  const base = compact.split("-")[0];
  if (VALID_CODES.has(base)) return base;

  if (ALIASES[base]) return ALIASES[base];

  return "en";
}
