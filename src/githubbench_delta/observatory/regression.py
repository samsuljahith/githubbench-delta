"""Detect sudden regressions in differentiation or saturation."""

from __future__ import annotations

import statistics

from githubbench_delta.observatory.half_life import cohort_series
from githubbench_delta.observatory.models import BenchmarkSnapshot, RegressionEvent


class RegressionDetector:
    """Flag abrupt drops in differentiation or spikes in mean score (saturation)."""

    def __init__(
        self,
        *,
        z_threshold: float = 2.0,
        min_abs_diff_drop: float = 0.05,
        min_abs_sat_rise: float = 0.08,
    ) -> None:
        self.z_threshold = z_threshold
        self.min_abs_diff_drop = min_abs_diff_drop
        self.min_abs_sat_rise = min_abs_sat_rise

    def detect(self, snapshots: list[BenchmarkSnapshot]) -> list[RegressionEvent]:
        timestamps, diffs, sats, _ = cohort_series(snapshots)
        if len(timestamps) < 3:
            return []

        events: list[RegressionEvent] = []
        d_deltas = [diffs[i] - diffs[i - 1] for i in range(1, len(diffs))]
        s_deltas = [sats[i] - sats[i - 1] for i in range(1, len(sats))]

        d_std = statistics.pstdev(d_deltas) if len(d_deltas) > 1 else 0.0
        s_std = statistics.pstdev(s_deltas) if len(s_deltas) > 1 else 0.0
        d_mean = statistics.fmean(d_deltas) if d_deltas else 0.0
        s_mean = statistics.fmean(s_deltas) if s_deltas else 0.0

        for i, delta in enumerate(d_deltas):
            z = (delta - d_mean) / d_std if d_std > 1e-12 else 0.0
            if delta <= -self.min_abs_diff_drop and (z <= -self.z_threshold or d_std < 1e-12):
                events.append(
                    RegressionEvent(
                        timestamp=timestamps[i + 1],
                        kind="differentiation_drop",
                        severity=abs(z) if d_std > 1e-12 else abs(delta) / self.min_abs_diff_drop,
                        message=(
                            f"Differentiation fell from {diffs[i]:.4f} to {diffs[i + 1]:.4f} "
                            f"(Δ={delta:.4f})"
                        ),
                        before=diffs[i],
                        after=diffs[i + 1],
                        metadata={"z": z},
                    )
                )

        for i, delta in enumerate(s_deltas):
            z = (delta - s_mean) / s_std if s_std > 1e-12 else 0.0
            if delta >= self.min_abs_sat_rise and (z >= self.z_threshold or s_std < 1e-12):
                events.append(
                    RegressionEvent(
                        timestamp=timestamps[i + 1],
                        kind="saturation_spike",
                        severity=abs(z) if s_std > 1e-12 else abs(delta) / self.min_abs_sat_rise,
                        message=(
                            f"Mean score rose from {sats[i]:.4f} to {sats[i + 1]:.4f} "
                            f"(Δ={delta:.4f}) — possible saturation"
                        ),
                        before=sats[i],
                        after=sats[i + 1],
                        metadata={"z": z},
                    )
                )

        events.sort(key=lambda e: e.timestamp)
        return events
