"""NewsAPI helper returning concise article context with caching."""
from __future__ import annotations

import logging
import re
from typing import Dict, List

import requests

import config
from services.cache_service import get_cache_service

logger = logging.getLogger(__name__)

_NEWS_URL = "https://newsapi.org/v2/everything"
_MAX_ARTICLES = 5
_NEWS_CACHE_TTL = 300  # 5 minutes for news results


def fetch_news_context(query: str) -> Dict[str, object]:
    """
    Fetch top news articles for a query.
    
    Results are cached for 5 minutes to reduce API calls.
    """
    if not (config.NEWS_ENABLED and config.NEWS_API_KEY):
        return {"context": None, "sources": []}

    # ==================== CACHING LOGIC ====================
    cache = get_cache_service()
    cache_key = cache.generate_cache_key(query, language="en", cache_type="news")
    
    # Check cache first
    cached_result = cache.get_cache(cache_key)
    if cached_result is not None:
        logger.info(f"🔥 News Cache HIT for: {query[:50]}...")
        return cached_result
    # =====================================================

    params = {
        "q": query,
        "language": config.NEWS_API_LANGUAGE,
        "pageSize": min(_MAX_ARTICLES, config.NEWS_MAX_RESULTS),
        "sortBy": "publishedAt",
    }
    headers = {"X-Api-Key": config.NEWS_API_KEY}

    try:
        response = requests.get(
            _NEWS_URL,
            params=params,
            headers=headers,
            timeout=config.NEWS_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        logger.error("News API request failed: %s", exc)
        return {"context": None, "sources": []}

    articles = payload.get("articles", [])
    cleaned: List[Dict[str, str]] = []
    for article in articles:
        if len(cleaned) >= _MAX_ARTICLES:
            break
        title = (article.get("title", "") or "Headline").strip()
        description = _clean_text(article.get("description", ""))
        if not description:
            continue
        cleaned.append(
            {
                "title": title,
                "snippet": description,
                "link": article.get("url", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("publishedAt", ""),
            }
        )

    if not cleaned:
        return {"context": None, "sources": []}

    bullet_lines = [f"- {entry['title']}: {entry['snippet']}" for entry in cleaned]
    context = "Latest verified headlines:\n" + "\n".join(bullet_lines)
    result = {"context": context, "sources": cleaned}
    
    # ==================== CACHE STORAGE ====================
    # Store result in cache
    cache.set_cache(cache_key, result, _NEWS_CACHE_TTL)
    logger.info(f"💾 News result cached (ttl: {_NEWS_CACHE_TTL}s)")
    # =====================================================
    
    return result


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())
