"""Realtime intelligence feed helpers for dashboard and map-oriented views."""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from services.cache_service import get_cache_service
from services.news import fetch_news_context

logger = logging.getLogger(__name__)

_EVENTS_CACHE_TTL = 180
_FEED_CACHE_VERSION = "v3"
_GLOBAL_FEED_QUERY = (
    "global geopolitics economy technology security"
)
_INDIA_FEED_QUERY = (
    "India latest news politics economy sports technology"
)

_INDIA_FALLBACK_QUERY = "India breaking news"

_INDIA_SOURCE_KEYWORDS = [
    "times of india", "hindustan times", "the hindu", "indian express", "ndtv",
    "livemint", "moneycontrol", "business standard", "india today", "news18 india",
]

_INDIA_TERMS = [
    "india", "indian", "new delhi", "mumbai", "bengaluru", "bangalore", "kolkata",
    "chennai", "hyderabad", "rbi", "bcci", "lok sabha", "rajya sabha",
]

_REGION_KEYWORDS = {
    "India": ["india", "new delhi", "mumbai", "bengaluru", "bangalore", "kolkata", "chennai", "hyderabad"],
    "North America": ["us", "usa", "canada", "mexico", "washington", "new york"],
    "Europe": ["europe", "eu", "uk", "london", "france", "germany", "italy"],
    "Middle East": ["middle east", "israel", "iran", "saudi", "qatar", "uae"],
    "Asia": ["asia", "india", "china", "japan", "korea", "indonesia"],
    "Africa": ["africa", "nigeria", "kenya", "egypt", "south africa"],
    "South America": ["south america", "brazil", "argentina", "chile", "colombia"],
    "Oceania": ["australia", "new zealand", "oceania"],
}

_REGION_COORDINATES = {
    "India": {"lat": 20.5937, "lon": 78.9629},
    "North America": {"lat": 39.8283, "lon": -98.5795},
    "Europe": {"lat": 54.5260, "lon": 15.2551},
    "Middle East": {"lat": 29.2985, "lon": 42.5510},
    "Asia": {"lat": 34.0479, "lon": 100.6197},
    "Africa": {"lat": -8.7832, "lon": 34.5085},
    "South America": {"lat": -8.7832, "lon": -55.4915},
    "Oceania": {"lat": -22.7359, "lon": 140.0188},
    "Global": {"lat": 0.0, "lon": 0.0},
}


def get_live_feed(limit: int = 20, focus: str = "india") -> Dict[str, Any]:
    """Return normalized event feed suitable for timeline/chat sidepanels."""
    focus_key = (focus or "india").strip().lower()
    query = _INDIA_FEED_QUERY if focus_key == "india" else _GLOBAL_FEED_QUERY

    cache = get_cache_service()
    cache_key = cache.generate_cache_key(f"{_FEED_CACHE_VERSION}:{query}:{limit}:{focus_key}", language="en", cache_type="events")
    cached = cache.get_cache(cache_key)
    if cached is not None:
        if focus_key == "india" and not (cached.get("events") or []):
            logger.info("Bypassing cached empty India feed result to recompute fallback events")
        else:
            return cached

    payload = fetch_news_context(query)
    sources = payload.get("sources", []) if payload else []

    if focus_key == "india" and not sources:
        fallback_payload = fetch_news_context(_INDIA_FALLBACK_QUERY)
        sources = fallback_payload.get("sources", []) if fallback_payload else []

    events: List[Dict[str, Any]] = []
    for item in sources[:limit]:
        title = item.get("title", "Untitled Event")
        snippet = item.get("snippet", "")
        source_name = (item.get("source") or "").lower()
        if any(k in source_name for k in _INDIA_SOURCE_KEYWORDS):
            region = "India"
        else:
            region = _infer_region(f"{title} {snippet} {source_name}")
        coords = _REGION_COORDINATES.get(region, _REGION_COORDINATES["Global"])

        event_id = hashlib.md5(f"{title}:{item.get('link', '')}".encode("utf-8")).hexdigest()[:16]
        events.append(
            {
                "event_id": event_id,
                "title": title,
                "summary": snippet,
                "source": item.get("source", "Unknown"),
                "link": item.get("link", ""),
                "published_at": item.get("published_at", ""),
                "region": region,
                "severity": _infer_severity(f"{title} {snippet}"),
                "coordinates": coords,
                "is_india_focus": region == "India",
                "india_relevance": _india_relevance(f"{title} {snippet}", source_name),
            }
        )

    if focus_key == "india" and not events:
        events.append(
            {
                "event_id": "india-focus-fallback",
                "title": "India Focus Active",
                "summary": "Live India news sources are temporarily unavailable. Dashboard remains pinned to India-first mode and will refresh automatically.",
                "source": "Pragna Monitor",
                "link": "",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "region": "India",
                "severity": "low",
                "coordinates": _REGION_COORDINATES["India"],
                "is_india_focus": True,
            }
        )

    # India-first ranking while still keeping global visibility.
    if focus_key == "india":
        india_events = [event for event in events if (event.get("india_relevance") or 0) > 0]
        non_india_events = [event for event in events if (event.get("india_relevance") or 0) <= 0]
        events.sort(key=lambda event: _event_priority(event), reverse=True)
        if india_events:
            india_events.sort(key=lambda event: _event_priority(event), reverse=True)
            non_india_events.sort(key=lambda event: _event_priority(event), reverse=True)
            events = india_events + non_india_events
        else:
            events.insert(
                0,
                {
                    "event_id": "india-focus-priority",
                    "title": "India Focus Priority",
                    "summary": "No strongly India-tagged stories were found in this refresh cycle. Monitoring remains pinned to India-first and will auto-refresh.",
                    "source": "Pragna Monitor",
                    "link": "",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "region": "India",
                    "severity": "low",
                    "coordinates": _REGION_COORDINATES["India"],
                    "is_india_focus": True,
                    "india_relevance": 999,
                },
            )
    events = events[:limit]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "focus": focus_key,
        "count": len(events),
        "events": events,
    }
    cache.set_cache(cache_key, result, _EVENTS_CACHE_TTL)
    return result


def get_geo_summary(limit: int = 50, focus: str = "india") -> Dict[str, Any]:
    """Aggregate the event feed into region-level map summary points."""
    focus_key = (focus or "india").strip().lower()
    feed = get_live_feed(limit=limit, focus=focus_key)
    region_counts: Dict[str, int] = {}

    for event in feed.get("events", []):
        region = event.get("region", "Global")
        region_counts[region] = region_counts.get(region, 0) + 1

    regions = []
    if focus_key == "india":
        sorted_regions = sorted(
            region_counts.items(),
            key=lambda kv: (1 if kv[0] == "India" else 0, kv[1]),
            reverse=True,
        )
    else:
        sorted_regions = sorted(region_counts.items(), key=lambda kv: kv[1], reverse=True)

    for region, count in sorted_regions:
        coords = _REGION_COORDINATES.get(region, _REGION_COORDINATES["Global"])
        regions.append(
            {
                "region": region,
                "events": count,
                "lat": coords["lat"],
                "lon": coords["lon"],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "focus": focus_key,
        "regions": regions,
    }


def _event_priority(event: Dict[str, Any]) -> tuple:
    region = event.get("region", "Global")
    severity = event.get("severity", "low")
    severity_rank = {"high": 3, "medium": 2, "low": 1}.get(severity, 0)
    india_boost = 1 if region == "India" else 0
    relevance = event.get("india_relevance", 0)
    return india_boost, relevance, severity_rank


def _contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    escaped = re.escape(keyword)
    if re.fullmatch(r"[a-z0-9]+", keyword):
        return re.search(rf"\b{escaped}\b", text) is not None
    return keyword in text


def _infer_region(text: str) -> str:
    lowered = (text or "").lower()
    for region, keywords in _REGION_KEYWORDS.items():
        if any(_contains_keyword(lowered, keyword) for keyword in keywords):
            return region
    return "Global"


def _india_relevance(text: str, source_name: str) -> int:
    lowered = (text or "").lower()
    score = 0
    for term in _INDIA_TERMS:
        if _contains_keyword(lowered, term):
            score += 2
    if any(k in (source_name or "") for k in _INDIA_SOURCE_KEYWORDS):
        score += 4
    return score


def _infer_severity(text: str) -> str:
    lowered = (text or "").lower()
    critical = ["war", "attack", "earthquake", "sanction", "crisis", "outbreak"]
    elevated = ["election", "inflation", "market", "protest", "strike", "cyber"]

    if any(token in lowered for token in critical):
        return "high"
    if any(token in lowered for token in elevated):
        return "medium"
    return "low"
