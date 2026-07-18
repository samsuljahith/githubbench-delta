"""Prompt content hashing."""

from __future__ import annotations

import hashlib


def hash_prompt_content(content: str) -> str:
    """Return sha256 hex digest of normalized prompt content."""

    normalized = content.replace("\r\n", "\n").strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
