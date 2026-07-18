"""Deterministic shuffle and sampling helpers."""

from __future__ import annotations

import random


def shuffle_deterministic[T](items: list[T], seed: int) -> list[T]:
    """Return a new list shuffled with a deterministic seed."""

    out = list(items)
    rng = random.Random(seed)
    rng.shuffle(out)
    return out


def sample_deterministic[T](items: list[T], n: int, seed: int) -> list[T]:
    """Sample ``n`` items without replacement using a deterministic seed.

    If ``n >= len(items)``, returns a deterministic shuffle of all items.
    """

    if n < 0:
        raise ValueError("n must be >= 0")
    shuffled = shuffle_deterministic(items, seed)
    if n >= len(shuffled):
        return shuffled
    return shuffled[:n]
