"""Multi-model side-by-side comparison: send one prompt to several models at
once and return each model's answer (or failure) independently."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import config
from services.llm import _request_completion, list_available_models

logger = logging.getLogger(__name__)

MAX_COMPARE_MODELS = 4


def run_compare(
    message: str,
    model_keys: List[str],
    language: str = "en",
) -> List[Dict[str, object]]:
    """Run the same prompt against multiple models in parallel.

    Calls the low-level _request_completion directly instead of
    generate_completion - the latter has a hardcoded "emergency fallback"
    chain (falls back to config.OLLAMA_MODEL/OPENAI_MODEL/GROQ_MODEL when a
    requested model fails) that exists to keep normal chat always answering,
    but would silently substitute a different model's response here, making
    a "failed" column secretly show another model's answer instead of an
    honest error - defeating the whole point of a side-by-side comparison.
    """
    catalog = {m["key"]: m for m in list_available_models()}
    language_name = config.SUPPORTED_LANGUAGES.get(language, "English")
    messages = [
        {"role": "system", "content": f"You are a helpful assistant. Respond in {language_name}."},
        {"role": "user", "content": message},
    ]

    def _run_one(model_key: str) -> Dict[str, object]:
        started = time.monotonic()
        try:
            response = _request_completion(messages, model_key)
            return {
                "model": model_key,
                "display_name": catalog.get(model_key, {}).get("display_name", model_key),
                "response": response,
                "error": None,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
            }
        except Exception as exc:
            logger.error("Compare mode failed for %s: %s", model_key, exc)
            return {
                "model": model_key,
                "display_name": catalog.get(model_key, {}).get("display_name", model_key),
                "response": None,
                "error": str(exc),
                "elapsed_ms": int((time.monotonic() - started) * 1000),
            }

    results: List[Dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=len(model_keys)) as executor:
        futures = {executor.submit(_run_one, key): key for key in model_keys}
        for future in as_completed(futures):
            results.append(future.result())

    order = {key: idx for idx, key in enumerate(model_keys)}
    results.sort(key=lambda r: order.get(r["model"], 0))
    return results
