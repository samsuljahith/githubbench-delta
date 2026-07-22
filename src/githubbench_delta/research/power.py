"""Power / sample-size estimators from pilot arrays (numpy only).

Never fabricate: empty pilot → insufficient_data.
Uses Normal approximations (z-based); document that t-based power
requires scipy and is intentionally omitted.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from githubbench_delta.research.models import PowerEstimate
from githubbench_delta.research.stats import _erfcinv


def _as_array(values: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float).ravel()


def _z_for_tail(p: float) -> float:
    """z such that P(Z > z) = p  ⇒  erfc(z/sqrt(2)) = 2p for one-sided...

    For two-sided alpha: z_{1-alpha/2} = sqrt(2) * erfcinv(alpha).
    For one-sided power beta: z_power = sqrt(2) * erfcinv(2*(1-power)).
    """

    return float(np.sqrt(2) * _erfcinv(p))


class VarianceEstimator:
    """Estimate variance from a pilot sample."""

    def estimate(self, values: Sequence[float] | np.ndarray) -> PowerEstimate:
        x = _as_array(values)
        n = int(x.size)
        if n < 2 or not np.isfinite(x).all():
            return PowerEstimate(
                ok=False,
                method="variance",
                notes=["insufficient_data", "need >= 2 finite pilot values"],
            )
        var = float(np.var(x, ddof=1))
        return PowerEstimate(
            ok=True,
            method="variance",
            variance=var,
            notes=[f"sample variance from n={n} pilot values"],
        )


class SampleSizeEstimator:
    """Two-sided one-sample / paired mean test sample size (Normal approx)."""

    def estimate(
        self,
        values: Sequence[float] | np.ndarray,
        *,
        alpha: float = 0.05,
        power: float = 0.8,
        mde: float | None = None,
    ) -> PowerEstimate:
        x = _as_array(values)
        if x.size < 2 or not np.isfinite(x).all():
            return PowerEstimate(
                ok=False,
                method="sample_size",
                alpha=alpha,
                power=power,
                mde=mde,
                notes=["insufficient_data", "need >= 2 finite pilot values"],
            )
        var_est = VarianceEstimator().estimate(x)
        if not var_est.ok or var_est.variance is None:
            return PowerEstimate(
                ok=False,
                method="sample_size",
                alpha=alpha,
                power=power,
                mde=mde,
                notes=["insufficient_data"],
            )
        sigma2 = var_est.variance
        if sigma2 <= 0:
            return PowerEstimate(
                ok=False,
                method="sample_size",
                alpha=alpha,
                power=power,
                variance=sigma2,
                mde=mde,
                notes=["insufficient_data", "zero pilot variance"],
            )
        if mde is None or mde <= 0:
            return PowerEstimate(
                ok=False,
                method="sample_size",
                alpha=alpha,
                power=power,
                variance=sigma2,
                mde=mde,
                notes=["insufficient_data", "positive mde required"],
            )
        z_a = _z_for_tail(alpha)  # two-sided: erfcinv(alpha) → z_{1-a/2}
        z_b = _z_for_tail(2 * (1 - power))  # one-sided power quantile
        n_req = int(np.ceil(((z_a + z_b) ** 2) * sigma2 / (mde**2)))
        n_req = max(n_req, 2)
        return PowerEstimate(
            ok=True,
            method="sample_size",
            n_required=n_req,
            mde=float(mde),
            variance=sigma2,
            alpha=alpha,
            power=power,
            notes=[
                "Normal approximation for two-sided one-sample/paired mean test",
                "t-based power not used (numpy-only; no scipy)",
            ],
        )


class MDEEstimator:
    """Minimum detectable effect for fixed n, alpha, power (Normal approx)."""

    def estimate(
        self,
        values: Sequence[float] | np.ndarray,
        *,
        n: int | None = None,
        alpha: float = 0.05,
        power: float = 0.8,
    ) -> PowerEstimate:
        x = _as_array(values)
        if x.size < 2 or not np.isfinite(x).all():
            return PowerEstimate(
                ok=False,
                method="mde",
                alpha=alpha,
                power=power,
                notes=["insufficient_data", "need >= 2 finite pilot values"],
            )
        var_est = VarianceEstimator().estimate(x)
        if not var_est.ok or var_est.variance is None or var_est.variance <= 0:
            return PowerEstimate(
                ok=False,
                method="mde",
                alpha=alpha,
                power=power,
                notes=["insufficient_data"],
            )
        sample_n = int(n) if n is not None else int(x.size)
        if sample_n < 2:
            return PowerEstimate(
                ok=False,
                method="mde",
                alpha=alpha,
                power=power,
                variance=var_est.variance,
                notes=["insufficient_data", "n must be >= 2"],
            )
        z_a = _z_for_tail(alpha)
        z_b = _z_for_tail(2 * (1 - power))
        mde = float((z_a + z_b) * np.sqrt(var_est.variance / sample_n))
        return PowerEstimate(
            ok=True,
            method="mde",
            n_required=sample_n,
            mde=mde,
            variance=var_est.variance,
            alpha=alpha,
            power=power,
            notes=[
                "Normal approximation MDE for two-sided one-sample/paired mean test",
            ],
        )
