"""
Style profiler: derives a user style profile from recent user messages.
Caches results to avoid re-summarizing on every turn.
"""
import logging
import time
from typing import Dict, Tuple

from services import memory_db
from services.llm import generate_completion

logger = logging.getLogger(__name__)

# Cache: user_id -> (profile_json_str, user_msg_count, timestamp)
_CACHE: Dict[str, Tuple[str, int, float]] = {}

# Re-profile cadence controls to avoid an extra LLM call on every turn.
MIN_MESSAGES_FOR_LLM_PROFILE = 6
REPROFILE_MESSAGE_DELTA = 4

DEFAULT_PROFILE = {
    "tone": "neutral",
    "formality": "medium",
    "verbosity": "medium",
    "structure": "paragraph",
    "persona": "helpful and concise",
    "formatting": "markdown when useful, bullets for lists",
}

SUMMARIZE_SYSTEM = (
    "You are a style analyzer. Given recent user messages, return ONE JSON object "
    'with keys: tone (casual|neutral|formal), formality (low|medium|high), '
    'verbosity (short|medium|long), structure (paragraph|bullets|mixed), '
    'persona (short text), formatting (short text). Be concise.'
)


def _summarize(messages_text: str) -> Dict[str, str]:
    """Call Groq to summarize style from user messages."""
    prompt = [
        {"role": "system", "content": SUMMARIZE_SYSTEM},
        {"role": "user", "content": messages_text},
    ]
    try:
        resp = generate_completion(prompt)
        # Best-effort JSON extraction; if parsing fails, return default
        import json
        return json.loads(resp)
    except Exception as e:
        logger.warning(f"Style summarization failed: {e}. Using default profile.")
        return DEFAULT_PROFILE


def get_style_profile(
    user_id: str, max_messages: int = 20, cache_ttl: int = 300
) -> Dict[str, str]:
    """
    Return a style profile derived from the last `max_messages` user messages.
    Cached for `cache_ttl` seconds and refreshed if message count changes.

    Args:
        user_id: User identifier (chat ID in frontend).
        max_messages: Max user messages to scan for style.
        cache_ttl: Cache time-to-live in seconds.

    Returns:
        Dict with keys: tone, formality, verbosity, structure, persona, formatting.
    """
    history = memory_db.get_history(user_id, max_messages)
    user_msgs = [m["content"] for m in history if m.get("role") == "user"]
    msg_count = len(user_msgs)
    now = time.time()

    # Check cache
    cached = _CACHE.get(user_id)
    if cached:
        cached_count = cached[1]
        cached_age_ok = (now - cached[2] < cache_ttl)
        count_delta_small = (msg_count - cached_count) < REPROFILE_MESSAGE_DELTA
        if cached_age_ok and count_delta_small:
            try:
                import json

                return json.loads(cached[0])
            except Exception:
                pass  # fall through and recompute

    # For small histories, default profile is good enough and faster.
    if msg_count < MIN_MESSAGES_FOR_LLM_PROFILE:
        profile = DEFAULT_PROFILE
        import json
        _CACHE[user_id] = (json.dumps(profile), msg_count, now)
        return profile

    if cached and (now - cached[2] < cache_ttl):
        try:
            import json
            return json.loads(cached[0])
        except Exception:
            pass  # fall through and recompute

    # Compute profile
    if not user_msgs:
        profile = DEFAULT_PROFILE
    else:
        text_blob = "\n\n".join(user_msgs[-max_messages:])
        profile = _summarize(text_blob)

    # Cache result
    import json

    _CACHE[user_id] = (json.dumps(profile), msg_count, now)
    logger.info(f"Profiled style for user {user_id}: {profile}")
    return profile


def style_system_message(profile: Dict[str, str], language: str = 'en') -> str:
    """Build a system message that instructs the model to adapt to the user's style with personality and language.
    
    Args:
        profile: User style profile
        language: Language code for response (e.g., 'hi', 'ta', 'en')
    """
    import config
    
    tone = profile.get('tone', 'neutral')
    formality = profile.get('formality', 'medium')
    verbosity = profile.get('verbosity', 'medium')
    structure = profile.get('structure', 'paragraph')
    persona = profile.get('persona', 'helpful and concise')
    formatting = profile.get('formatting', 'markdown when useful')
    
    # Get language name
    language_name = config.SUPPORTED_LANGUAGES.get(language, 'English')
    
    # Tone-specific personality instructions
    tone_instructions = ""
    if tone == "casual":
        tone_instructions = (
            "Keep it conversational and fun. Use natural speech patterns, abbreviations, "
            "and casual language. Be witty and relatable. Feel free to use emojis sparingly "
            "when appropriate. Sound like a real friend, not a bot."
        )
    elif tone == "formal":
        tone_instructions = (
            "Maintain a professional and respectful tone. Use complete sentences and proper grammar. "
            "Be thorough and detailed. Structure your response clearly with logical flow."
        )
    else:
        tone_instructions = (
            "Balance professionalism with friendliness. Be clear and helpful. "
            "Use natural language without being too stiff or too casual."
        )
    
    return (
        f"You are a creative and engaging AI assistant called Pragna. "
        f"IMPORTANT: Always respond in {language_name}, regardless of the input language.\n\n"
        f"Adapt to the user's communication style:\n"
        f"Tone: {tone}\n"
        f"Formality: {formality}\n"
        f"Verbosity: {verbosity}\n"
        f"Structure: {structure}\n"
        f"Persona: {persona}\n"
        f"Formatting: {formatting}\n\n"
        f"Style Instructions: {tone_instructions}\n\n"
        f"General Guidelines:\n"
        f"- Be authentic and personality-driven\n"
        f"- Adapt your response style to mirror the user's energy\n"
        f"- Be creative and add flair when appropriate\n"
        f"- Respect safety and clarity above all else\n"
        f"- Don't mimic harmful or disrespectful language\n"
        f"- Be helpful, honest, and genuine"
    )
