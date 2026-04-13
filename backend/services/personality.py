"""
Personality injection system: adds creative flair to responses based on tone.
Makes responses more engaging, witty, and personality-driven.
"""
from typing import Dict

CASUAL_PERSONALITY = {
    "opening_hooks": [
        "yo, ",
        "so check it out ",
        "alright, ",
        "lemme break it down ",
        "real talk, ",
        "boom, ",
        "facts, ",
    ],
    "transition_phrases": [
        "right? like",
        "you feelme?",
        "no cap,",
        "deadass though,",
        "for real for real,",
        "bestie,",
    ],
    "closing_vibes": [
        "that's it, that's the move 🤙",
        "you got this!",
        "keep it 💯",
        "stay blessed bro",
        "that's the tea ☕",
        "periodt 💅",
    ],
}

FORMAL_PERSONALITY = {
    "opening_hooks": [
        "certainly, ",
        "to clarify, ",
        "here's the thing: ",
        "in essence, ",
        "fundamentally, ",
    ],
    "transition_phrases": [
        "furthermore,",
        "notably,",
        "in addition,",
        "however,",
        "conversely,",
    ],
    "closing_vibes": [
        "I hope this clarifies matters.",
        "Please let me know if you need further explanation.",
        "Thank you for the question.",
        "I trust this addresses your inquiry.",
    ],
}

NEUTRAL_PERSONALITY = {
    "opening_hooks": [
        "so, ",
        "basically, ",
        "essentially, ",
        "to sum it up, ",
    ],
    "transition_phrases": [
        "also,",
        "another thing is,",
        "that said,",
        "on that note,",
    ],
    "closing_vibes": [
        "hope that helps!",
        "let me know if you have questions",
        "anything else?",
        "that covers it",
    ],
}


def get_personality_markers(tone: str) -> Dict[str, list]:
    """
    Get personality markers (opening hooks, transitions, closing vibes) for a tone.
    """
    if tone == "casual":
        return CASUAL_PERSONALITY
    elif tone == "formal":
        return FORMAL_PERSONALITY
    else:
        return NEUTRAL_PERSONALITY


def inject_personality(response: str, tone: str) -> str:
    """
    Inject personality into a response based on tone.
    Adds creative flair without changing core content.
    """
    if not response or len(response) < 20:
        return response

    markers = get_personality_markers(tone)

    # For casual responses, add a bit more flair
    if tone == "casual":
        # Add emoji-like vibes if it makes sense
        if response.endswith("."):
            response = response[:-1] + " 💪"
        if "?" in response and not response.endswith("?"):
            pass  # Already has personality

    return response
