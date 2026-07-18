"""Reproducibility evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    sequence_similarity,
    skip_result,
    tool_name_sequence,
)


class ReproducibilityMetric(BaseMetric):
    """Seeded trajectory equivalence within tolerance across peer runs."""

    id: str = "reproducibility"
    display_name: str = "Reproducibility"
    requires_peer_runs: bool = True
    group: MetricGroup = MetricGroup.EFFICIENCY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        min_sim = float(self._threshold("trajectory_similarity_min", 0.8))
        primary = tool_name_sequence(ctx.trajectory) or [c.name for c in ctx.tool_calls]
        peers = ctx.peer_results
        if not peers:
            return skip_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                reason="Requires peer_results for reproducibility",
                weight=self.config.weight,
                metric_version=self.config.version,
                strict_zero=self.config.strict,
            )

        sims: list[float] = []
        for peer in peers:
            peer_seq = tool_name_sequence(peer.trajectory)
            if not peer_seq and not primary:
                sims.append(1.0)
            else:
                sims.append(sequence_similarity(primary, peer_seq))

        mean_sim = sum(sims) / len(sims)
        # Score relative to threshold: at/above min_sim → 1.0 linearly below
        if mean_sim >= min_sim:
            raw = 1.0
        else:
            raw = mean_sim / min_sim if min_sim > 0 else mean_sim

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(sims),
            expected_items=len(sims),
        )
        improvements = []
        if mean_sim < min_sim:
            improvements.append("Make tool trajectories more stable across seeded peer runs")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"Mean trajectory similarity={mean_sim:.2f} "
                f"(threshold={min_sim:.2f}) across {len(sims)} peer(s)"
            ),
            evidence=[{"similarities": sims, "primary": primary}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"mean_similarity": mean_sim, "threshold": min_sim},
        )
