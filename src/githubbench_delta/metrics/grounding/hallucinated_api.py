"""Hallucinated API evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import FailureExampleKind, MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    extract_paths,
    extract_symbols,
)


class HallucinatedAPIMetric(BaseMetric):
    """Non-existent APIs/symbols/files referenced in the response."""

    id: str = "hallucinated_api"
    display_name: str = "Hallucinated API"
    group: MetricGroup = MetricGroup.GROUNDING

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        max_h = int(self._threshold("max_hallucinated_refs", 0))
        response = ctx.response or ""
        claims = extract_paths(response) | extract_symbols(response)

        evidence_parts: list[str] = []
        if ctx.trajectory:
            for step in ctx.trajectory.steps:
                if step.tool_result and step.tool_result.output:
                    evidence_parts.append(step.tool_result.output)
        if ctx.task:
            evidence_parts.extend(ctx.task.files)
            evidence_parts.append(ctx.task.prompt)
        if ctx.gold_answer:
            evidence_parts.append(ctx.gold_answer.content)
        evidence_blob = "\n".join(evidence_parts).lower()
        evidence_set = {
            e.lower()
            for e in (
                extract_paths("\n".join(evidence_parts))
                | extract_symbols("\n".join(evidence_parts))
            )
        }
        if ctx.task:
            evidence_set |= {f.lower() for f in ctx.task.files}

        hallucinated = [
            c for c in claims if c.lower() not in evidence_set and c.lower() not in evidence_blob
        ]

        for fe in ctx.failure_examples:
            if fe.kind in {
                FailureExampleKind.HALLUCINATED_API,
                FailureExampleKind.HALLUCINATION,
            }:
                needle = (fe.example or fe.description or "").lower()
                if needle and needle in response.lower():
                    hallucinated.append(f"failure_example:{fe.kind.value}")

        count = len(set(hallucinated))
        raw = 1.0 if count <= max_h else 0.0
        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(evidence_set) + 1,
            expected_items=max(1, len(claims) or 1),
        )
        improvements = []
        if count > max_h:
            improvements.append("Remove references to APIs/files not observed in tool evidence")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"{count} hallucinated reference(s); threshold max_hallucinated_refs={max_h}"
            ),
            evidence=[{"hallucinated": sorted(set(hallucinated))[:30]}],
            warnings=sorted(set(hallucinated))[:10],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"hallucinated_count": count, "max_hallucinated_refs": max_h},
        )
