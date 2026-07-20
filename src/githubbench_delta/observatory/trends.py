"""Trend analysis over historical snapshots."""

from __future__ import annotations

from collections import defaultdict

from githubbench_delta.observatory.half_life import cohort_series
from githubbench_delta.observatory.models import (
    BenchmarkSnapshot,
    TrendReport,
    TrendSeriesPoint,
)


class TrendAnalyzer:
    """Build score / provider / model / saturation / differentiation series."""

    def analyze(self, snapshots: list[BenchmarkSnapshot]) -> TrendReport:
        score_vs_time: list[TrendSeriesPoint] = []
        provider_trends: dict[str, list[TrendSeriesPoint]] = defaultdict(list)
        model_progression: dict[str, list[TrendSeriesPoint]] = defaultdict(list)

        for snap in sorted(snapshots, key=lambda s: (s.timestamp, s.agent_id)):
            score_vs_time.append(
                TrendSeriesPoint(
                    timestamp=snap.timestamp,
                    value=snap.score,
                    label=snap.agent_id,
                    metadata={
                        "experiment_id": snap.experiment_id,
                        "provider": snap.provider,
                        "model": snap.model,
                    },
                )
            )
            provider_trends[snap.provider].append(
                TrendSeriesPoint(
                    timestamp=snap.timestamp,
                    value=snap.score,
                    label=snap.agent_id,
                    metadata={"model": snap.model, "experiment_id": snap.experiment_id},
                )
            )
            model_key = f"{snap.provider}/{snap.model}"
            model_progression[model_key].append(
                TrendSeriesPoint(
                    timestamp=snap.timestamp,
                    value=snap.score,
                    label=snap.agent_id,
                    metadata={"experiment_id": snap.experiment_id},
                )
            )

        timestamps, diffs, sats, _counts = cohort_series(snapshots)
        saturation_vs_time = [
            TrendSeriesPoint(timestamp=t, value=s, label="saturation")
            for t, s in zip(timestamps, sats, strict=True)
        ]
        differentiation_vs_time = [
            TrendSeriesPoint(timestamp=t, value=d, label="differentiation")
            for t, d in zip(timestamps, diffs, strict=True)
        ]

        return TrendReport(
            score_vs_time=score_vs_time,
            provider_trends=dict(provider_trends),
            model_progression=dict(model_progression),
            saturation_vs_time=saturation_vs_time,
            differentiation_vs_time=differentiation_vs_time,
            metadata={
                "n_snapshots": len(snapshots),
                "n_cohorts": len(timestamps),
                "providers": sorted(provider_trends.keys()),
                "models": sorted(model_progression.keys()),
            },
        )
