"""FRIDAY-style agent tools for unified orchestrator usage.

This module ports practical tool capabilities into the EtherX backend so they can be
used from chat and future voice paths through one orchestrator.
"""
from __future__ import annotations

import datetime
import logging
import platform
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

SEED_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.cnbc.com/id/100727362/device/rss/rss.html",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]


def get_current_time() -> str:
    """Return current server time as ISO string."""
    return datetime.datetime.now().isoformat()


def get_system_info() -> Dict[str, str]:
    """Return high-level host system information."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }


def word_count(text: str) -> Dict[str, int]:
    """Count words, characters, and lines for arbitrary input text."""
    lines = text.splitlines()
    words = text.split()
    return {
        "characters": len(text),
        "words": len(words),
        "lines": len(lines),
    }


def open_world_monitor() -> Dict[str, str]:
    """Return a monitor-open action payload for clients to execute."""
    return {
        "action": "open_url",
        "label": "world_monitor",
        "url": "https://www.worldmonitor.app/",
    }


def get_world_news(max_items: int = 12) -> str:
    """Fetch and format world headlines from multiple RSS feeds in parallel."""
    articles: List[Dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=min(6, len(SEED_FEEDS))) as executor:
        futures = [executor.submit(_fetch_and_parse_feed, url) for url in SEED_FEEDS]
        for future in as_completed(futures):
            try:
                articles.extend(future.result())
            except Exception as exc:
                logger.debug("Feed fetch failed: %s", exc)

    if not articles:
        return "The global news grid is unresponsive right now."

    report_lines = ["### GLOBAL NEWS BRIEFING (LIVE)", ""]
    for entry in articles[:max_items]:
        report_lines.append(f"**[{entry['source']}]** {entry['title']}")
        if entry["summary"]:
            report_lines.append(entry["summary"])
        if entry["link"]:
            report_lines.append(f"Link: {entry['link']}")
        report_lines.append("")

    return "\n".join(report_lines).strip()


def _fetch_and_parse_feed(url: str) -> List[Dict[str, str]]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "EtherX-Orchestrator/1.0"},
            timeout=6,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)

        source_name = _source_from_url(url)
        feed_items: List[Dict[str, str]] = []
        for item in root.findall(".//item")[:5]:
            title = (item.findtext("title") or "Untitled").strip()
            description = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()

            if description:
                description = re.sub(r"<[^<]+?>", "", description).strip()
                if len(description) > 220:
                    description = f"{description[:220]}..."

            feed_items.append(
                {
                    "source": source_name,
                    "title": title,
                    "summary": description,
                    "link": link,
                }
            )

        return feed_items
    except Exception:
        return []


def _source_from_url(url: str) -> str:
    try:
        host = url.split("//", 1)[1].split("/", 1)[0]
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2].upper()
        return host.upper()
    except Exception:
        return "NEWS"
