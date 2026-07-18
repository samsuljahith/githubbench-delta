"""Cross Trial Consistency evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

import hashlib

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    skip_result,
    variance,
)


class CrossTrialConsistencyMetric(BaseMetric):
    """Score variance across peer trials of the same task."""

    id: str = "cross_trial_consistency"
    display_name: str = "Cross Trial Consistency"
    requires_peer_runs: bool = True
    group: MetricGroup = MetricGroup.RELIABILITY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        max_var = float(self._threshold("max_score_variance", 0.15))
        peers = list(ctx.peer_results)
        if len(peers) < 1 and not ctx.peer_evaluations:
            return skip_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                reason="Requires peer_results or peer_evaluations",
                weight=self.config.weight,
                metric_version=self.config.version,
                strict_zero=self.config.strict,
            )

        values: list[float] = []
        if ctx.peer_evaluations:
            for ev in ctx.peer_evaluations:
                if ev.overall_score is not None:
                    values.append(float(ev.overall_score))
        if not values:
            # Hash-based consistency of response texts including primary
            texts = [ctx.response or ""]
            texts.extend(p.output.content for p in peers)
            # Map identical hashes to 1, diversity via unique ratio
            hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts if t is not None]
            if len(hashes) < 2:
                return skip_result(
                    metric_id=self.id,
                    display_name=self.display_name,
                    group=self.group,
                    reason="Need at least two trial outputs for consistency",
                    weight=self.config.weight,
                    metric_version=self.config.version,
                    strict_zero=self.config.strict,
                )
            unique = len(set(hashes))
            raw = 1.0 - (unique - 1) / max(1, len(hashes) - 1)
            conf = evidence_confidence(
                self.config.confidence_mode,
                evidence_items=len(hashes),
                expected_items=len(hashes),
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
                    f"Response hash uniqueness {unique}/{len(hashes)}; consistency={raw:.2f}"
                ),
                evidence=[{"unique_hashes": unique, "trials": len(hashes)}],
                suggested_improvements=(
                    ["Reduce cross-trial answer divergence"] if raw < 1.0 else []
                ),
                metric_version=self.config.version,
                details={"mode": "hash", "unique": unique},
            )

        # Include primary overall if present in metadata
        primary = ctx.metadata.get("primary_overall_score")
        if primary is not None:
            values.append(float(primary))
        var = variance(values)
        raw = 1.0 - min(1.0, var / max_var) if max_var > 0 else 1.0 - min(1.0, var)
        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(values),
            expected_items=max(2, len(values)),
        )
        improvements = ["Stabilize scores across repeated trials"] if var > max_var else []
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=f"Peer score variance={var:.4f} (max={max_var:.4f})",
            evidence=[{"scores": values, "variance": var}],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={"variance": var, "max_score_variance": max_var},
        )
