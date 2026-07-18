"""Shared deterministic scoring helpers for methodology evaluators."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

from githubbench_delta.core.config import ConfidenceMode, NormalizationStrategy
from githubbench_delta.core.models import MetricGroup, MetricResult, ToolCall, Trajectory

_TOKEN_RE = re.compile(r"[a-zA-Z_][\w./:-]{1,}")
_PATH_RE = re.compile(r"(?:[\w.-]+/)+[\w.-]+\.[a-zA-Z0-9]+|[\w.-]+\.(?:py|ts|tsx|js|go|rs|java|md)")
_SYMBOL_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]+|[a-z_][a-z0-9_]{2,})\b")


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_score(
    raw: float,
    strategy: NormalizationStrategy | str = NormalizationStrategy.CLAMP_01,
) -> float:
    if strategy == NormalizationStrategy.IDENTITY or strategy == "identity":
        return float(raw)
    return clamp01(raw)


def tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def token_jaccard(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def substring_coverage(needle: str, haystack: str) -> float:
    n = (needle or "").strip().lower()
    h = (haystack or "").lower()
    if not n:
        return 0.0
    if n in h:
        return 1.0
    tokens = [t for t in re.split(r"\s+", n) if t]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in h)
    return hits / len(tokens)


def criteria_hit_rate(criteria: Iterable[str], response: str) -> float:
    items = [c.strip() for c in criteria if c and c.strip()]
    if not items:
        return 0.0
    text = (response or "").lower()
    hits = sum(1 for c in items if c.lower() in text)
    return hits / len(items)


def extract_paths(text: str) -> set[str]:
    return {m.group(0) for m in _PATH_RE.finditer(text or "")}


def extract_symbols(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "into",
        "return",
        "true",
        "false",
        "none",
        "null",
        "def",
        "class",
        "function",
        "import",
        "const",
        "let",
        "var",
        "public",
        "private",
        "void",
        "string",
        "int",
        "float",
        "bool",
        "test",
        "assert",
    }
    out: set[str] = set()
    for m in _SYMBOL_RE.finditer(text or ""):
        sym = m.group(1)
        if sym.lower() in stop:
            continue
        out.add(sym)
    return out


def tool_calls_from_trajectory(trajectory: Trajectory | None) -> list[ToolCall]:
    if trajectory is None:
        return []
    calls: list[ToolCall] = []
    for step in trajectory.steps:
        if step.tool_call is not None:
            calls.append(step.tool_call)
    return calls


def tool_name_sequence(trajectory: Trajectory | None) -> list[str]:
    return [c.name for c in tool_calls_from_trajectory(trajectory)]


def lcs_ratio(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[n][m] / max(n, m)


def multiset_f1(expected: list[str], actual: list[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    exp_c, act_c = Counter(expected), Counter(actual)
    overlap = sum((exp_c & act_c).values())
    precision = overlap / sum(act_c.values())
    recall = overlap / sum(exp_c.values())
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def sequence_similarity(a: list[str], b: list[str]) -> float:
    return lcs_ratio(a, b)


def evidence_confidence(
    mode: ConfidenceMode | str,
    *,
    evidence_items: int,
    expected_items: int = 1,
    fixed: float = 1.0,
) -> float:
    if mode == ConfidenceMode.FIXED or mode == "fixed":
        return clamp01(fixed)
    if expected_items <= 0:
        return 0.5
    return clamp01(evidence_items / expected_items)


def build_result(
    *,
    metric_id: str,
    display_name: str,
    group: MetricGroup,
    raw_score: float,
    weight: float = 1.0,
    normalization: NormalizationStrategy | str = NormalizationStrategy.CLAMP_01,
    confidence: float = 1.0,
    reasoning: str = "",
    evidence: list[Any] | dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    suggested_improvements: list[str] | None = None,
    metric_version: str = "1.0.0",
    details: dict[str, Any] | None = None,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> MetricResult:
    score = 0.0 if skipped else normalize_score(raw_score, normalization)
    return MetricResult(
        metric_id=metric_id,
        display_name=display_name,
        group=group,
        raw_score=float(raw_score),
        score=score if not skipped else 0.0,
        weight=weight,
        confidence=clamp01(confidence),
        reasoning=reasoning,
        evidence=evidence if evidence is not None else [],
        warnings=warnings or [],
        suggested_improvements=suggested_improvements or [],
        metric_version=metric_version,
        details=details or {},
        skipped=skipped,
        skip_reason=skip_reason,
    )


def skip_result(
    *,
    metric_id: str,
    display_name: str,
    group: MetricGroup,
    reason: str,
    weight: float = 1.0,
    metric_version: str = "1.0.0",
    strict_zero: bool = False,
) -> MetricResult:
    if strict_zero:
        return build_result(
            metric_id=metric_id,
            display_name=display_name,
            group=group,
            raw_score=0.0,
            weight=weight,
            confidence=0.0,
            reasoning=f"Missing inputs (strict): {reason}",
            warnings=[reason],
            suggested_improvements=[f"Provide required context: {reason}"],
            metric_version=metric_version,
            details={"strict_missing": reason},
            skipped=False,
        )
    return build_result(
        metric_id=metric_id,
        display_name=display_name,
        group=group,
        raw_score=0.0,
        weight=weight,
        confidence=0.0,
        reasoning=f"Skipped: {reason}",
        metric_version=metric_version,
        details={"skip_reason": reason},
        skipped=True,
        skip_reason=reason,
    )
