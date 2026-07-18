"""Test Honesty evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

import re

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import build_result, evidence_confidence

_VACUOUS = [
    re.compile(r"assert\s+True\b", re.I),
    re.compile(r"assert\s+1\s*==\s*1\b", re.I),
    re.compile(r"^\s*pass\s*$", re.M),
    re.compile(r"self\.assertTrue\(\s*True\s*\)", re.I),
    re.compile(r"expect\(true\)\.toBe\(true\)", re.I),
    re.compile(r"@pytest\.mark\.skip", re.I),
]
_HONEST = [
    re.compile(r"assert\s+(?!True\b|False\b|1\b)\w+", re.I),
    re.compile(r"self\.assert(?:Equal|NotEqual|In|NotIn|Raises|Is|IsNone)\(", re.I),
    re.compile(r"expect\((?!true\b|false\b)[^)]+\)\.(to|not)", re.I),
]


class TestHonestyMetric(BaseMetric):
    """Tests assert real behavior rather than vacuous placeholders."""

    id: str = "test_honesty"
    display_name: str = "Test Honesty"
    group: MetricGroup = MetricGroup.GROUNDING

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        text = ctx.response or ""
        patch = ""
        if ctx.diff and ctx.diff.patch:
            patch = ctx.diff.patch
        elif ctx.agent_result.output.patch:
            patch = ctx.agent_result.output.patch
        blob = f"{text}\n{patch}"

        vacuous_hits = [p.pattern for p in _VACUOUS if p.search(blob)]
        honest_hits = [p.pattern for p in _HONEST if p.search(blob)]

        if not vacuous_hits and not honest_hits:
            # No test-like content — neutral/high for non-test tasks
            raw = 0.75
            reasoning = "No test-like content detected; neutral honesty score"
        elif vacuous_hits and not honest_hits:
            raw = 0.0
            reasoning = f"Vacuous test patterns only: {vacuous_hits[:3]}"
        elif vacuous_hits and honest_hits:
            raw = 0.35
            reasoning = "Mix of vacuous and real assertions"
        else:
            raw = 1.0
            reasoning = f"Honest assertion patterns found ({len(honest_hits)})"

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(vacuous_hits) + len(honest_hits) + 1,
            expected_items=2,
        )
        improvements = []
        if vacuous_hits:
            improvements.append(
                "Replace vacuous asserts (assert True / bare pass) with behavior checks"
            )
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=reasoning,
            evidence=[{"vacuous": vacuous_hits, "honest": honest_hits}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={
                "vacuous_count": len(vacuous_hits),
                "honest_count": len(honest_hits),
            },
        )
