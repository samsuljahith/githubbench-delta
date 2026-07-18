"""Cross-cutting / adversarial edge-case tasks (future expansion).

Language-primary tasks live in ``*_tasks.py``. Keep rare multi-language,
fixture-boundary, or deliberately tricky cases here when they do not
belong cleanly in a single language module.
"""

from __future__ import annotations

from typing import Any


def tasks() -> list[dict[str, Any]]:
    """Return edge-case task records (empty in v1)."""

    return []


__all__ = ["tasks"]
