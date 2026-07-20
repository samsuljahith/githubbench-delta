"""Cohort metrics and half-life estimation over BenchmarkHistory."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime

from githubbench_delta.observatory.decay import DecayModel
from githubbench_delta.observatory.models import (
    BenchmarkSnapshot,
    DecayCurve,
    DecayCurvePoint,
    HalfLifeEstimate,
)


def _cohort_key(ts: datetime) -> str:
    """Bucket snapshots that share the same experiment timestamp (second precision)."""

    return ts.astimezone().replace(microsecond=0).isoformat()


def cohort_series(
    snapshots: list[BenchmarkSnapshot],
) -> tuple[list[datetime], list[float], list[float], list[int]]:
    """Return parallel arrays: timestamps, differentiation D(t), saturation S(t), n_models."""

    by_t: dict[str, list[BenchmarkSnapshot]] = defaultdict(list)
    for snap in snapshots:
        by_t[_cohort_key(snap.timestamp)].append(snap)

    timestamps: list[datetime] = []
    diffs: list[float] = []
    sats: list[float] = []
    counts: list[int] = []
    for key in sorted(by_t.keys()):
        group = by_t[key]
        scores = [s.score for s in group]
        ts = group[0].timestamp
        timestamps.append(ts)
        if len(scores) == 1:
            diffs.append(0.0)
        elif len(scores) == 2:
            diffs.append(abs(scores[0] - scores[1]))
        else:
            diffs.append(float(statistics.pstdev(scores)))
        sats.append(float(sum(scores) / len(scores)))
        counts.append(len(scores))
    return timestamps, diffs, sats, counts


class HalfLifeEstimator:
    """Estimate benchmark differentiation half-life and usefulness trend."""

    def __init__(self, decay_model: DecayModel | None = None) -> None:
        self.decay_model = decay_model or DecayModel()

    def estimate(self, snapshots: list[BenchmarkSnapshot]) -> HalfLifeEstimate:
        notes: list[str] = []
        if not snapshots:
            empty = DecayCurve(lambda_per_day=0.0, d0=0.0, r_squared=0.0, points=[])
            return HalfLifeEstimate(
                half_life_days=None,
                confidence=0.0,
                decaying=False,
                decay_curve=empty,
                usefulness_trend="insufficient_data",
                notes=["No snapshots available."],
            )

        timestamps, diffs, sats, counts = cohort_series(snapshots)
        n_ts = len(timestamps)
        n_models = len({s.model for s in snapshots} | {s.agent_id for s in snapshots})

        if n_ts < 3:
            notes.append(
                f"Only {n_ts} distinct timestamp(s); need ≥3 for a reliable half-life fit."
            )
        if max(counts, default=0) < 2:
            notes.append(
                "Cohorts have fewer than 2 models; differentiation is underdetermined "
                "(saturation-only mode)."
            )

        curve = self.decay_model.fit(timestamps, diffs, saturation=sats)
        hl = self.decay_model.half_life_days(curve)
        decaying = curve.lambda_per_day > 1e-6 and hl is not None

        # Confidence: blend R², sample size, span, multi-model presence
        span_days = 0.0
        if n_ts >= 2:
            span_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0
        conf = 0.0
        conf += 0.45 * curve.r_squared
        conf += 0.25 * min(1.0, n_ts / 6.0)
        conf += 0.15 * min(1.0, span_days / 90.0)
        conf += 0.15 * (1.0 if max(counts, default=0) >= 2 else 0.0)
        if not decaying:
            conf *= 0.5
            notes.append("Non-positive decay rate — half-life undefined or infinite.")
        confidence = max(0.0, min(1.0, conf))

        # Usefulness trend from recent D and S slopes
        usefulness = self._usefulness_trend(diffs, sats)
        sat_series = [
            DecayCurvePoint(
                t_days=p.t_days,
                differentiation=p.differentiation,
                fitted=p.fitted,
                saturation=p.saturation,
                timestamp=p.timestamp,
            )
            for p in curve.points
        ]

        return HalfLifeEstimate(
            half_life_days=hl if decaying else None,
            confidence=confidence,
            decaying=decaying,
            decay_curve=curve,
            saturation_series=sat_series,
            usefulness_trend=usefulness,
            differentiation_series=list(curve.points),
            sample_timestamps=n_ts,
            sample_models=n_models,
            notes=notes,
            metadata={
                "span_days": span_days,
                "mean_saturation": float(sum(sats) / len(sats)) if sats else 0.0,
                "final_differentiation": diffs[-1] if diffs else 0.0,
                "lambda_per_day": curve.lambda_per_day,
            },
        )

    @staticmethod
    def _usefulness_trend(diffs: list[float], sats: list[float]) -> str:
        if len(diffs) < 2:
            return "insufficient_data"
        d_delta = diffs[-1] - diffs[0]
        s_delta = sats[-1] - sats[0]
        if s_delta > 0.05 and d_delta < -0.02:
            return "declining_usefulness"
        if d_delta < -0.05:
            return "losing_differentiation"
        if s_delta > 0.1:
            return "approaching_saturation"
        if abs(d_delta) < 0.02 and abs(s_delta) < 0.02:
            return "stable"
        if d_delta > 0.02:
            return "increasing_differentiation"
        return "mixed"

    @staticmethod
    def format_half_life(days: float | None) -> str:
        if days is None or not math.isfinite(days):
            return "undefined / non-decaying"
        if days >= 365:
            return f"{days / 365.0:.2f} years ({days:.1f} days)"
        return f"{days:.1f} days"
