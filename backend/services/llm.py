"""Groq completion helper."""
from __future__ import annotations

import logging
from typing import List, Dict, Optional, Tuple

import requests

import config

logger = logging.getLogger(__name__)

def _normalize_key(model_key: str) -> str:
    return (model_key or "").strip().lower()


def _parse_model_key(model_key: Optional[str]) -> Tuple[str, str]:
    key = (model_key or "").strip()
    if not key:
        return "groq", config.GROQ_MODEL

    normalized = _normalize_key(key)
    registry = config.MODEL_REGISTRY
    if normalized in registry:
        item = registry[normalized]
        return item.get("provider", "groq"), item.get("model", config.GROQ_MODEL)

    if ":" in key:
        provider, model_name = key.split(":", 1)
        provider = provider.strip().lower() or "groq"
        model_name = model_name.strip() or config.GROQ_MODEL
        return provider, model_name

    return "groq", key


def _resolve_request_config(model_key: Optional[str]) -> Dict[str, object]:
    provider, model_name = _parse_model_key(model_key)

    if provider == "ollama":
        return {
            "provider": "ollama",
            "model": model_name,
            "endpoint": f"{config.OLLAMA_API_URL.rstrip('/')}/chat/completions",
            "api_key": "",
            "timeout": config.OLLAMA_TIMEOUT,
            "requires_api_key": False,
            "model_key": f"ollama:{model_name}",
        }

    if provider == "openai":
        return {
            "provider": "openai",
            "model": model_name,
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "api_key": config.OPENAI_API_KEY,
            "timeout": config.OPENAI_TIMEOUT,
            "requires_api_key": True,
            "model_key": f"openai:{model_name}",
        }

    # Default provider: groq
    return {
        "provider": "groq",
        "model": model_name,
        "endpoint": f"{config.GROQ_BASE_URL.rstrip('/')}/chat/completions",
        "api_key": config.GROQ_API_KEY,
        "timeout": config.GROQ_TIMEOUT,
        "requires_api_key": True,
        "model_key": f"groq:{model_name}",
    }


def _request_completion(messages: List[Dict[str, str]], model_key: Optional[str]) -> str:
    request_cfg = _resolve_request_config(model_key)

    if request_cfg["provider"] == "ollama" and not config.OLLAMA_ENABLED:
        raise RuntimeError("Ollama provider is disabled")

    if request_cfg["requires_api_key"] and not request_cfg["api_key"]:
        raise RuntimeError(f"{request_cfg['provider']} API key is not configured")

    payload = {
        "model": request_cfg["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 0.9,
    }
    headers = {"Content-Type": "application/json"}
    if request_cfg["api_key"]:
        headers["Authorization"] = f"Bearer {request_cfg['api_key']}"

    response = requests.post(
        request_cfg["endpoint"],
        headers=headers,
        json=payload,
        timeout=request_cfg["timeout"],
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def list_available_models() -> List[Dict[str, object]]:
    """Return model registry metadata for API/UI consumption."""
    models = []
    for model_key, metadata in config.MODEL_REGISTRY.items():
        entry = dict(metadata)
        entry["key"] = model_key
        models.append(entry)
    return sorted(models, key=lambda item: item["key"])


def generate_completion(
    messages: List[Dict[str, str]],
    model_override: Optional[str] = None,
    fallback_models: Optional[List[str]] = None,
) -> str:
    """Generate completion with model override and fallback chain support."""
    candidates: List[Optional[str]] = []
    if model_override:
        candidates.append(model_override)
    else:
        candidates.append(config.DEFAULT_MODEL_KEY)

    if fallback_models:
        candidates.extend(fallback_models)
    else:
        candidates.extend(config.DEFAULT_MODEL_FALLBACKS)

    deduped: List[Optional[str]] = []
    seen = set()
    for candidate in candidates:
        key = _normalize_key(candidate or "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    errors = []
    for candidate in deduped:
        try:
            return _request_completion(messages, candidate)
        except requests.exceptions.Timeout:
            logger.error("Completion timed out for model candidate: %s", candidate)
            errors.append(f"timeout:{candidate}")
        except requests.exceptions.RequestException as exc:
            logger.error("Completion request failed for %s: %s", candidate, exc)
            errors.append(f"request_error:{candidate}")
        except Exception as exc:
            logger.error("Completion failed for %s: %s", candidate, exc)
            errors.append(f"error:{candidate}")

    # Emergency provider chain: mirrors image fallback behavior for text.
    emergency_candidates: List[str] = []
    if config.OPENAI_API_KEY:
        emergency_candidates.append(f"openai:{config.OPENAI_MODEL}")
    if config.OLLAMA_ENABLED:
        emergency_candidates.extend(["ollama:qwen3:4b", "ollama:qwen3:8b"])
    if config.GROQ_API_KEY:
        emergency_candidates.append(f"groq:{config.GROQ_MODEL}")

    for candidate in emergency_candidates:
        key = _normalize_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            logger.warning("Trying emergency fallback text model: %s", candidate)
            return _request_completion(messages, candidate)
        except Exception as exc:
            logger.error("Emergency fallback failed for %s: %s", candidate, exc)
            errors.append(f"emergency_error:{candidate}")

    if errors:
        logger.error("All model candidates failed: %s", ", ".join(errors))
    return "Sorry, I encountered an error while generating the response."
