"""Debug artifact logging for reverse app-chat calls."""

from __future__ import annotations

import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

import orjson

from app.core.logger import logger
from app.core.storage import DATA_DIR


_SENSITIVE_KEYS = {"authorization", "cookie", "token", "sso", "sso-rw", "cf_clearance"}
_TOKEN_RE = re.compile(r"(sso(?:-rw)?=|cf_clearance=)[^;\s]+", re.IGNORECASE)
_TRUE_VALUES = {"1", "true", "yes", "on", "y"}


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse an environment boolean flag with exact-name and uppercase support."""
    raw = os.getenv(name)
    if raw is None:
        raw = os.getenv(name.upper())
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def app_chat_debug_enabled() -> bool:
    """
    Return whether app-chat debug artifacts should be persisted.

    @complexity LOW
    @ai_context Env-only feature flag for sensitive app-chat debug artifacts.
    @pure true
    """
    return _env_flag("debug_app_log", default=False)


def new_debug_pair_id() -> str:
    """Create a short ID shared by request, stream, and error artifacts."""
    return uuid.uuid4().hex[:12]


def _debug_dir() -> Path:
    return DATA_DIR / "debug" / "app-chat"


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _TOKEN_RE.sub(r"\1[REDACTED]", value)
    return value


def redact(data: dict[str, Any]) -> dict[str, Any]:
    """Redact headers and known token-bearing fields while preserving shape."""
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = _redact_value(value)
    return redacted


def write_debug_json(pair_id: str, suffix: str, payload: dict[str, Any]) -> Path | None:
    """Persist a JSON debug artifact when app-chat debug logging is enabled."""
    if not app_chat_debug_enabled():
        return None
    try:
        base_dir = _debug_dir()
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"{_timestamp()}-{pair_id}-{suffix}.json"
        path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
        logger.info("App-chat debug artifact written: {}", path)
        return path
    except Exception as exc:
        logger.warning("Failed to write app-chat debug JSON artifact: {}", exc)
        return None


def write_debug_text(pair_id: str, suffix: str, text: str) -> Path | None:
    """Persist a text debug artifact when app-chat debug logging is enabled."""
    if not app_chat_debug_enabled():
        return None
    try:
        base_dir = _debug_dir()
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"{_timestamp()}-{pair_id}-{suffix}.txt"
        path.write_text(_TOKEN_RE.sub(r"\1[REDACTED]", text), encoding="utf-8")
        logger.info("App-chat debug artifact written: {}", path)
        return path
    except Exception as exc:
        logger.warning("Failed to write app-chat debug text artifact: {}", exc)
        return None


__all__ = [
    "app_chat_debug_enabled",
    "new_debug_pair_id",
    "redact",
    "write_debug_json",
    "write_debug_text",
]
