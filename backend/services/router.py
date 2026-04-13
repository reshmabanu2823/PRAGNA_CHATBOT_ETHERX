"""Route intents to concrete handlers."""
from __future__ import annotations

from typing import Dict

_ROUTE_TABLE: Dict[str, Dict[str, object]] = {
    "general": {
        "target": "llm",
        "needs_context": False,
        "description": "General knowledge handled directly by LLM",
    },
    "realtime": {
        "target": "search",
        "needs_context": True,
        "description": "Requires fresh realtime web search",
    },
    "news": {
        "target": "news",
        "needs_context": True,
        "description": "Needs curated news headlines",
    },
    "tool": {
        "target": "tool",
        "needs_context": False,
        "description": "Calculator tool",
    },
}


def route_query(intent: str) -> Dict[str, object]:
    """Return the route metadata for a detected intent."""
    normalized = (intent or "general").strip().lower()
    return _ROUTE_TABLE.get(normalized, _ROUTE_TABLE["general"])
