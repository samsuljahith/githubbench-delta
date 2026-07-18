"""Grounding Ratio evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    extract_paths,
    extract_symbols,
)


class GroundingRatioMetric(BaseMetric):
    """Claims/edits grounded in repository / tool evidence."""

    id: str = "grounding_ratio"
    display_name: str = "Grounding Ratio"
    group: MetricGroup = MetricGroup.GROUNDING

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        min_ratio = float(self._threshold("min_grounding_ratio", 0.7))
        response = ctx.response or ""
        claims = extract_paths(response) | extract_symbols(response)

        evidence_text_parts: list[str] = []
        if ctx.trajectory:
            for step in ctx.trajectory.steps:
                if step.tool_result and step.tool_result.output:
                    evidence_text_parts.append(step.tool_result.output)
                if step.content:
                    evidence_text_parts.append(step.content)
        if ctx.task:
            evidence_text_parts.extend(ctx.task.files)
            evidence_text_parts.append(ctx.task.prompt)
        if ctx.gold_answer:
            evidence_text_parts.append(ctx.gold_answer.content)
            evidence_text_parts.extend(ctx.gold_answer.acceptance_criteria)
        evidence_blob = "\n".join(evidence_text_parts)
        evidence_set = extract_paths(evidence_blob) | extract_symbols(evidence_blob)
        # Also treat task files as grounded
        if ctx.task:
            evidence_set |= set(ctx.task.files)

        if not claims:
            raw = 1.0 if not response.strip() else 0.6
            grounded: set[str] = set()
            ungrounded: set[str] = set()
        else:
            grounded = {
                c for c in claims if c in evidence_set or c.lower() in evidence_blob.lower()
            }
            ungrounded = claims - grounded
            raw = len(grounded) / len(claims)

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(evidence_set),
            expected_items=max(1, len(claims) or 1),
        )
        improvements = []
        if raw < min_ratio:
            improvements.append(
                "Cite only files/symbols observed via tools or present in the task files"
            )
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"Grounded {len(grounded)}/{len(claims) or 0} claims "
                f"(ratio={raw:.2f}, threshold={min_ratio:.2f})"
            ),
            evidence=[
                {
                    "grounded": sorted(grounded)[:20],
                    "ungrounded": sorted(ungrounded)[:20],
                }
            ],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"ratio": raw, "min_grounding_ratio": min_ratio},
        )
