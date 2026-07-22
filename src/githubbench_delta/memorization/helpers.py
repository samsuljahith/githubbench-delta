"""Shared helpers for MDS."""

from __future__ import annotations

import re
from typing import Any


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_prompt(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def deep_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur
