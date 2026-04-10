"""Structured logger utility with module tagging and timestamps."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class AppLogger:
    """Small structured logger wrapper used by service modules."""

    def __init__(self, module: str) -> None:
        self.module = module
        self._logger = logging.getLogger(f"greengate.{module}")

    def _emit(self, level: int, event: str, data: dict[str, Any] | None = None) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "module": self.module,
            "event": event,
            "data": data or {},
        }
        self._logger.log(level, json.dumps(payload, default=str))

    def info(self, event: str, data: dict[str, Any] | None = None) -> None:
        self._emit(logging.INFO, event, data)

    def warn(self, event: str, data: dict[str, Any] | None = None) -> None:
        self._emit(logging.WARNING, event, data)

    def error(self, event: str, data: dict[str, Any] | None = None) -> None:
        self._emit(logging.ERROR, event, data)


def get_logger(module: str) -> AppLogger:
    """Return a structured logger scoped to a module."""
    return AppLogger(module)
