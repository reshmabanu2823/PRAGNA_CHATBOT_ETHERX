"""
Real-time tone detector for the current user message.
Analyzes the message itself to detect casual, neutral, or formal tone.
"""
import re
from typing import Literal

CASUAL_MARKERS = {
    # Abbreviations & texting
    r'\byo\b', r'\byoyo\b', r'\bwassup\b', r'\bwup\b', r'\bsup\b',
    r'\bhey\b', r'\bey\b', r'\bbruh\b', r'\bdude\b', r'\bman\b',
    r'\bcuz\b', r'\bfam\b', r'\bG\b', r'\bfoo\b', r'\bbro\b',
    # Slang verbs
    r'\bwanna\b', r'\bgonna\b', r'\bgotta\b', r'\bkinda\b', r'\bsorta\b',
    r'\blol\b', r'\bhaha\b', r'\bdamn\b', r'\bhell\b', r'\bcrap\b',
    # Enthusiasm
    r'!!!', r'\?{2,}', r'\.{3,}',
    # Texting/informal
    r'\baight\b', r'\bbtw\b', r'\btbh\b', r'\bfyi\b', r'\bidk\b',
    r'\bafaik\b', r'\blmao\b', r'\bwtf\b', r'\bsmh\b',
    # Emojis (common casual indicators)
    r'[😀-🙏🏻-🏿😀-😻😼-😽😾-😿🙀-🙏]',
    # Lowercase patterns (informal)
    r'^[a-z].*[a-z]$',
    # Numbers as words
    r'\b\d+\b(?!\s[A-Z])',
    # Exclamation-heavy
    r'!{2,}',
}

FORMAL_MARKERS = {
    r'\bplease\b',
    r'\bcould you\b',
    r'\bwould you\b',
    r'\bwould you mind\b',
    r'\bkindly\b',
    r'\brespectfully\b',
    r'\brequire\b',
    r'\bdeemed\b',
    r'\bfurthermore\b',
    r'\bmoreover\b',
    r'\backnowledge\b',
    r'\bincorporate\b',
    r'\bprofessional\b',
    r'\bconduct\b',
    r'\bformaliz\b',
    r'\bprocedure\b',
}


def detect_tone(message: str) -> Literal["casual", "neutral", "formal"]:
    """
    Detect tone from the current user message.

    Args:
        message: The user's message text.

    Returns:
        'casual' | 'neutral' | 'formal'
    """
    msg_lower = message.lower()

    casual_score = sum(
        1
        for pattern in CASUAL_MARKERS
        if re.search(pattern, msg_lower, re.IGNORECASE)
    )
    formal_score = sum(
        1
        for pattern in FORMAL_MARKERS
        if re.search(pattern, msg_lower, re.IGNORECASE)
    )

    if casual_score > formal_score:
        return "casual"
    elif formal_score > casual_score:
        return "formal"
    else:
        return "neutral"
