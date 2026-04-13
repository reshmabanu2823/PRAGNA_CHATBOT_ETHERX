"""Serper-based search helper with cleaned context and caching."""
from __future__ import annotations

import logging
import re
from typing import Dict, List

import requests

import config
from services.cache_service import get_cache_service

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://google.serper.dev/search"
_MAX_RESULTS = 3
_MIN_SNIPPET_LEN = 25
_SEARCH_CACHE_TTL = 300  # 5 minutes for search results
_LIVE_SEARCH_CACHE_TTL = 45

_SPORTS_LIVE_KEYWORDS = {
    "ipl", "cricket", "live score", "score", "match", "t20", "odi", "test",
    "csk", "rcb", "mi", "kkr", "srh", "dc", "rr", "pbks", "lsg", "gt",
}


def fetch_search_context(query: str) -> Dict[str, object]:
    """
    Return formatted context and sources for realtime queries.
    
    Results are cached for 5 minutes to avoid repeated API calls.
    """
    if not (config.SERPER_ENABLED and config.SERPER_API_KEY):
        return {"context": None, "sources": []}

    # ==================== CACHING LOGIC ====================
    cache = get_cache_service()
    prepared_query = _prepare_live_query(query)
    live_mode = _is_live_query(query)
    cache_key = cache.generate_cache_key(prepared_query, language="en", cache_type="search")
    
    # Check cache first
    cached_result = cache.get_cache(cache_key)
    if cached_result is not None:
        logger.info(f"🔥 Search Cache HIT for: {query[:50]}...")
        return cached_result
    # =====================================================

    headers = {
        "X-API-KEY": config.SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": prepared_query,
        "num": _MAX_RESULTS,
        # Encourage fresher results for live queries.
        **({"tbs": "qdr:h"} if live_mode else {}),
    }

    try:
        response = requests.post(
            _SEARCH_URL,
            headers=headers,
            json=payload,
            timeout=config.SERPER_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        logger.error("Serper search failed: %s", exc)
        return {"context": None, "sources": []}

    cleaned: List[Dict[str, str]] = []
    organic = data.get("organic", [])
    answer_box = data.get("answerBox")
    sports_box = data.get("sportsResults") or data.get("sports") or {}
    kg = data.get("knowledgeGraph") or {}

    # Prefer explicit sports result payloads when available.
    if isinstance(sports_box, dict):
        title = (sports_box.get("title") or sports_box.get("match") or "Live Sports Update").strip()
        summary_bits = []
        for key in ("gameSpotlight", "score", "summary", "status", "date"):
            value = sports_box.get(key)
            if value:
                summary_bits.append(str(value).strip())
        if summary_bits:
            cleaned.append(
                {
                    "title": title,
                    "snippet": _clean_snippet(" | ".join(summary_bits)),
                    "link": sports_box.get("link", ""),
                }
            )

    # Add knowledge graph top-line for better factual grounding.
    if isinstance(kg, dict):
        kg_title = (kg.get("title") or kg.get("type") or "").strip()
        kg_desc = _clean_snippet(kg.get("description") or "")
        if kg_title and len(kg_desc) >= _MIN_SNIPPET_LEN:
            cleaned.append(
                {
                    "title": kg_title,
                    "snippet": kg_desc,
                    "link": kg.get("website", ""),
                }
            )

    if answer_box:
        cleaned.append(
            {
                "title": answer_box.get("title", "Answer"),
                "snippet": _clean_snippet(answer_box.get("answer") or answer_box.get("snippet", "")),
                "link": answer_box.get("link", ""),
            }
        )

    for item in organic:
        if len(cleaned) >= _MAX_RESULTS:
            break
        snippet = _clean_snippet(item.get("snippet", ""))
        title = (item.get("title", "") or "Untitled").strip()
        if len(snippet) < _MIN_SNIPPET_LEN:
            continue
        cleaned.append({
            "title": title,
            "snippet": snippet,
            "link": item.get("link", ""),
        })

    cleaned = cleaned[:_MAX_RESULTS]
    if not cleaned:
        return {"context": None, "sources": []}

    bullet_lines = [f"- {entry['title']}: {entry['snippet']}" for entry in cleaned]
    context = "Current trusted findings:\n" + "\n".join(bullet_lines)
    result = {
        "context": context,
        "sources": cleaned,
        "live_mode": live_mode,
        "resolved_query": prepared_query,
    }
    
    # ==================== CACHE STORAGE ====================
    # Store result in cache
    ttl = _LIVE_SEARCH_CACHE_TTL if live_mode else _SEARCH_CACHE_TTL
    cache.set_cache(cache_key, result, ttl)
    logger.info(f"💾 Search result cached (ttl: {ttl}s)")
    # =====================================================
    
    return result


def _clean_snippet(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _is_live_query(query: str) -> bool:
    lowered = (query or "").lower()
    return any(token in lowered for token in _SPORTS_LIVE_KEYWORDS) or "live" in lowered


def _prepare_live_query(query: str) -> str:
    raw = (query or "").strip()
    lowered = raw.lower()
    if not raw:
        return raw

    # Bias cricket/ipl requests toward trusted scoreboard providers.
    if any(token in lowered for token in ("ipl", "cricket", "live score", "score")):
        return (
            f"{raw} latest live score from Cricbuzz OR ESPNcricinfo OR IPL official"
        )
    return raw
