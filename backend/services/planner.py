"""Execution planner that prepares context based on routing."""
from __future__ import annotations

import logging
from typing import Dict

from .news import fetch_news_context
from .search import fetch_search_context
from .tools import handle_calculator

logger = logging.getLogger(__name__)


def create_plan(query: str, route: Dict[str, object]) -> Dict[str, object]:
    """Generate execution plan for the given query and route."""
    target = route.get("target")
    plan: Dict[str, object] = {"mode": "llm", "context": None, "sources": []}

    if target == "tool":
        tool_payload = handle_calculator(query)
        if tool_payload["handled"]:
            return {
                "mode": "tool",
                "tool_result": tool_payload["result"],
                "sources": [],
            }
        logger.info("Tool routing could not evaluate expression; falling back to LLM")
        return plan

    if target == "search":
        payload = fetch_search_context(query)
        plan["context"] = payload["context"]
        plan["sources"] = payload["sources"]
        return plan

    if target == "news":
        payload = fetch_news_context(query)
        plan["context"] = payload["context"]
        plan["sources"] = payload["sources"]
        return plan

    return plan
