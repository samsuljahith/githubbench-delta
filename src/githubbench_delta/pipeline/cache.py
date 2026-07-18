"""Evaluation cache key helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from githubbench_delta.core.models import AgentResult


def content_hash_agent_result(agent_result: AgentResult) -> str:
    """Stable hash of agent output + trajectory for cache keys."""

    payload = {
        "success": agent_result.success,
        "output": agent_result.output.model_dump(mode="json"),
        "error": agent_result.error,
        "trajectory": (
            agent_result.trajectory.model_dump(mode="json") if agent_result.trajectory else None
        ),
        "diff_stats": (
            agent_result.diff_stats.model_dump(mode="json") if agent_result.diff_stats else None
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def make_cache_key(
    *,
    task_id: str,
    agent_id: str,
    trial_index: int,
    seed: int,
    agent_result: AgentResult | None = None,
    content_hash: str | None = None,
) -> str:
    """Build a deterministic evaluation cache key."""

    digest = content_hash or (
        content_hash_agent_result(agent_result) if agent_result is not None else "pending"
    )
    payload: dict[str, Any] = {
        "task_id": task_id,
        "agent_id": str(agent_id),
        "trial_index": trial_index,
        "seed": seed,
        "content_hash": digest,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def unit_seed(base_seed: int, task_id: str, agent_id: str, trial_index: int) -> int:
    """Derive a deterministic per-unit seed."""

    raw = f"{base_seed}:{task_id}:{agent_id}:{trial_index}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)
