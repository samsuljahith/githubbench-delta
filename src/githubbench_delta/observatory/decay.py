"""Exponential decay model for benchmark differentiation."""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np

from githubbench_delta.observatory.models import DecayCurve, DecayCurvePoint


class DecayModel:
    """Fit ``D(t) ≈ D0 * exp(-λ t)`` via log-linear least squares."""

    def fit(
        self,
        timestamps: list[datetime],
        differentiation: list[float],
        *,
        saturation: list[float] | None = None,
    ) -> DecayCurve:
        if len(timestamps) != len(differentiation):
            raise ValueError("timestamps and differentiation must have equal length")
        if len(timestamps) < 2:
            return DecayCurve(lambda_per_day=0.0, d0=0.0, r_squared=0.0, points=[])

        order = sorted(range(len(timestamps)), key=lambda i: timestamps[i])
        ts = [timestamps[i] for i in order]
        d_vals = [max(float(differentiation[i]), 1e-12) for i in order]
        sat = [float(saturation[i]) for i in order] if saturation else [None] * len(order)

        t0 = ts[0]
        t_days = np.array([(t - t0).total_seconds() / 86400.0 for t in ts], dtype=float)
        y = np.log(np.array(d_vals, dtype=float))

        # Linear regression: y = a + b t  =>  D0=exp(a), lambda=-b
        if np.allclose(t_days, t_days[0]):
            d0 = float(np.exp(y.mean()))
            curve = DecayCurve(lambda_per_day=0.0, d0=d0, r_squared=0.0, points=[])
        else:
            b, a = np.polyfit(t_days, y, 1)
            d0 = float(math.exp(a))
            lam = float(-b)
            y_hat = a + b * t_days
            ss_res = float(np.sum((y - y_hat) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 0.0 if ss_tot <= 1e-15 else max(0.0, min(1.0, 1.0 - ss_res / ss_tot))
            curve = DecayCurve(lambda_per_day=lam, d0=d0, r_squared=r2, points=[])

        points: list[DecayCurvePoint] = []
        for i, t in enumerate(ts):
            td = float(t_days[i])
            fitted = float(curve.d0 * math.exp(-curve.lambda_per_day * td))
            points.append(
                DecayCurvePoint(
                    t_days=td,
                    differentiation=float(d_vals[i]),
                    fitted=fitted,
                    saturation=sat[i],
                    timestamp=t,
                )
            )
        curve.points = points
        return curve

    def half_life_days(self, curve: DecayCurve) -> float | None:
        if curve.lambda_per_day <= 1e-12:
            return None
        return math.log(2.0) / curve.lambda_per_day
