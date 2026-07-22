"""Numpy-only statistical helpers for research experiments.

No scipy. Rank tests use Normal approximations with continuity correction.
Never fabricate: when n is below method minimum, return ok=False with
notes=["insufficient_data"] and null numeric fields.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from githubbench_delta.research.models import StatResult

# Method minimum sample sizes (conservative)
_MIN_BOOTSTRAP = 2
_MIN_PAIRED = 2
_MIN_PERMUTATION = 2
_MIN_WILCOXON = 6
_MIN_MANN_WHITNEY = 3
_MIN_MCNEMAR = 1  # needs discordant pairs; checked separately
_MIN_EFFECT = 2


def _as_array(values: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float).ravel()


def _insufficient(method: str, n: int, extra: str | None = None) -> StatResult:
    notes = ["insufficient_data"]
    if extra:
        notes.append(extra)
    return StatResult(ok=False, method=method, n=n, notes=notes)


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(seed)


def bootstrap_ci(
    values: Sequence[float] | np.ndarray,
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int | None = 0,
    statistic: str = "mean",
) -> StatResult:
    """Percentile bootstrap CI for mean or median."""

    x = _as_array(values)
    n = int(x.size)
    if n < _MIN_BOOTSTRAP or not np.isfinite(x).all():
        return _insufficient("bootstrap_ci", n)

    def _stat(a: np.ndarray) -> float:
        return float(np.mean(a) if statistic == "mean" else np.median(a))

    rng = _rng(seed)
    boots = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = rng.choice(x, size=n, replace=True)
        boots[i] = _stat(sample)
    lo = float(np.quantile(boots, alpha / 2))
    hi = float(np.quantile(boots, 1 - alpha / 2))
    return StatResult(
        ok=True,
        method="bootstrap_ci",
        n=n,
        statistic=_stat(x),
        ci_low=lo,
        ci_high=hi,
        notes=[f"percentile bootstrap; statistic={statistic}"],
        metadata={"n_boot": n_boot, "alpha": alpha, "seed": seed},
    )


def paired_bootstrap(
    a: Sequence[float] | np.ndarray,
    b: Sequence[float] | np.ndarray,
    *,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int | None = 0,
) -> StatResult:
    """Bootstrap CI on mean paired difference (a - b)."""

    x = _as_array(a)
    y = _as_array(b)
    if x.size != y.size:
        return StatResult(
            ok=False,
            method="paired_bootstrap",
            n=0,
            notes=["insufficient_data", "paired arrays must have equal length"],
        )
    n = int(x.size)
    if n < _MIN_PAIRED:
        return _insufficient("paired_bootstrap", n)
    d = x - y
    rng = _rng(seed)
    boots = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots[i] = float(np.mean(d[idx]))
    lo = float(np.quantile(boots, alpha / 2))
    hi = float(np.quantile(boots, 1 - alpha / 2))
    return StatResult(
        ok=True,
        method="paired_bootstrap",
        n=n,
        statistic=float(np.mean(d)),
        ci_low=lo,
        ci_high=hi,
        notes=["percentile bootstrap on paired differences"],
        metadata={"n_boot": n_boot, "alpha": alpha, "seed": seed},
    )


def permutation_test(
    a: Sequence[float] | np.ndarray,
    b: Sequence[float] | np.ndarray,
    *,
    n_perm: int = 5000,
    seed: int | None = 0,
) -> StatResult:
    """Two-sample permutation test on difference of means."""

    x = _as_array(a)
    y = _as_array(b)
    n_x, n_y = int(x.size), int(y.size)
    n = n_x + n_y
    if n_x < 1 or n_y < 1 or n < _MIN_PERMUTATION:
        return _insufficient("permutation_test", n)
    obs = float(np.mean(x) - np.mean(y))
    pooled = np.concatenate([x, y])
    rng = _rng(seed)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        diff = float(np.mean(pooled[:n_x]) - np.mean(pooled[n_x:]))
        if abs(diff) >= abs(obs):
            count += 1
    p = (count + 1) / (n_perm + 1)
    return StatResult(
        ok=True,
        method="permutation_test",
        n=n,
        statistic=obs,
        p_value=float(p),
        notes=["two-sided mean-difference permutation test"],
        metadata={"n_perm": n_perm, "seed": seed, "n_a": n_x, "n_b": n_y},
    )


def _normal_sf(z: float) -> float:
    """Survival function 1-Phi(z) via math.erfc (stdlib; no scipy)."""

    return float(0.5 * math.erfc(z / math.sqrt(2.0)))


def wilcoxon_signed_rank(
    a: Sequence[float] | np.ndarray,
    b: Sequence[float] | np.ndarray | None = None,
    *,
    seed: int | None = None,  # unused; kept for API uniformity
) -> StatResult:
    """Wilcoxon signed-rank with Normal + continuity correction approximation.

    Exact combinatorial tables are unavailable without scipy; approximation
    is documented and used when n >= 6 after dropping zeros.
    """

    del seed
    x = _as_array(a)
    if b is not None:
        y = _as_array(b)
        if x.size != y.size:
            return StatResult(
                ok=False,
                method="wilcoxon",
                n=0,
                notes=["insufficient_data", "paired arrays must have equal length"],
            )
        d = x - y
    else:
        d = x
    d = d[d != 0]
    n = int(d.size)
    if n < _MIN_WILCOXON:
        return _insufficient(
            "wilcoxon",
            n,
            f"need >= {_MIN_WILCOXON} non-zero paired differences for Normal approximation",
        )
    ranks = _rankdata(np.abs(d))
    w_plus = float(np.sum(ranks[d > 0]))
    expected = n * (n + 1) / 4.0
    variance = n * (n + 1) * (2 * n + 1) / 24.0
    # continuity correction toward expected
    z = (w_plus - expected - 0.5 * np.sign(w_plus - expected)) / np.sqrt(variance)
    p = 2 * min(_normal_sf(abs(z)), 1 - _normal_sf(abs(z)))
    p = min(1.0, max(0.0, float(p)))
    return StatResult(
        ok=True,
        method="wilcoxon",
        n=n,
        statistic=w_plus,
        p_value=p,
        notes=[
            "Normal approximation with continuity correction (no scipy exact tables)",
        ],
        metadata={"z": float(z)},
    )


def _rankdata(values: np.ndarray) -> np.ndarray:
    """Average ranks for ties (1-based)."""

    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=float)
    sorted_vals = values[order]
    i = 0
    while i < values.size:
        j = i + 1
        while j < values.size and sorted_vals[j] == sorted_vals[i]:
            j += 1
        avg = 0.5 * (i + 1 + j)  # 1-based average of [i+1 .. j]
        ranks[order[i:j]] = avg
        i = j
    return ranks


def mann_whitney_u(
    a: Sequence[float] | np.ndarray,
    b: Sequence[float] | np.ndarray,
) -> StatResult:
    """Mann–Whitney U with Normal + continuity correction approximation."""

    x = _as_array(a)
    y = _as_array(b)
    n1, n2 = int(x.size), int(y.size)
    if n1 < _MIN_MANN_WHITNEY or n2 < _MIN_MANN_WHITNEY:
        return _insufficient(
            "mann_whitney",
            n1 + n2,
            f"need >= {_MIN_MANN_WHITNEY} observations per group",
        )
    combined = np.concatenate([x, y])
    ranks = _rankdata(combined)
    r1 = float(np.sum(ranks[:n1]))
    u1 = r1 - n1 * (n1 + 1) / 2.0
    u2 = n1 * n2 - u1
    u = min(u1, u2)
    mu = n1 * n2 / 2.0
    sigma = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    z = (u - mu + 0.5) / sigma  # continuity correction toward mu
    p = 2 * _normal_sf(abs(z))
    p = min(1.0, max(0.0, float(p)))
    return StatResult(
        ok=True,
        method="mann_whitney",
        n=n1 + n2,
        statistic=float(u),
        p_value=p,
        notes=[
            "Normal approximation with continuity correction (no scipy exact tables)",
        ],
        metadata={"n_a": n1, "n_b": n2, "z": float(z)},
    )


def mcnemar_test(
    b: Sequence[bool] | np.ndarray | None = None,
    c: Sequence[bool] | np.ndarray | None = None,
    *,
    discordant: tuple[int, int] | None = None,
) -> StatResult:
    """McNemar test on paired binary outcomes.

    Pass either paired boolean arrays (True=success) or discordant counts
    (n01, n10) via ``discordant``.
    """

    if discordant is not None:
        n01, n10 = int(discordant[0]), int(discordant[1])
    else:
        if b is None or c is None:
            return _insufficient("mcnemar", 0, "need paired arrays or discordant counts")
        x = np.asarray(b, dtype=bool).ravel()
        y = np.asarray(c, dtype=bool).ravel()
        if x.size != y.size or x.size == 0:
            return _insufficient("mcnemar", int(x.size), "paired arrays must match")
        n01 = int(np.sum(~x & y))
        n10 = int(np.sum(x & ~y))
    n_disc = n01 + n10
    if n_disc < _MIN_MCNEMAR:
        return _insufficient("mcnemar", n_disc, "need at least one discordant pair")
    # Continuity-corrected chi-square / Normal approximation
    chi2 = (abs(n01 - n10) - 1) ** 2 / n_disc if n_disc > 0 else 0.0
    # P(chi^2_1 > chi2) ≈ erfc(sqrt(chi2/2))
    p = float(math.erfc(math.sqrt(chi2 / 2.0))) if chi2 > 0 else 1.0
    return StatResult(
        ok=True,
        method="mcnemar",
        n=n_disc,
        statistic=float(chi2),
        p_value=min(1.0, max(0.0, p)),
        notes=["continuity-corrected McNemar Normal/chi-square approximation"],
        metadata={"n01": n01, "n10": n10},
    )


def bh_fdr(
    p_values: Sequence[float] | np.ndarray,
    *,
    alpha: float = 0.05,
) -> list[dict[str, float | bool | int]]:
    """Benjamini–Hochberg FDR. Empty input → empty output. No fabricated p-values."""

    p = _as_array(p_values)
    if p.size == 0:
        return []
    if not np.isfinite(p).all() or np.any(p < 0) or np.any(p > 1):
        raise ValueError("p_values must be finite and in [0, 1]")
    m = int(p.size)
    order = np.argsort(p)
    ranked = p[order]
    thresh = alpha * (np.arange(1, m + 1) / m)
    # largest k with p_(k) <= thresh_k
    below = ranked <= thresh
    if not np.any(below):
        reject = np.zeros(m, dtype=bool)
    else:
        k_max = int(np.max(np.where(below)[0]))
        reject = np.zeros(m, dtype=bool)
        reject[order[: k_max + 1]] = True
    # adjusted p-values (step-up)
    adj = np.empty(m, dtype=float)
    adj[order[-1]] = ranked[-1]
    for i in range(m - 2, -1, -1):
        adj[order[i]] = min(adj[order[i + 1]], ranked[i] * m / (i + 1))
    adj = np.clip(adj, 0.0, 1.0)
    return [
        {
            "index": int(i),
            "p_value": float(p[i]),
            "p_adjusted": float(adj[i]),
            "reject": bool(reject[i]),
        }
        for i in range(m)
    ]


def cohens_d(
    a: Sequence[float] | np.ndarray,
    b: Sequence[float] | np.ndarray | None = None,
    *,
    paired: bool = False,
) -> StatResult:
    """Cohen's d (independent or paired)."""

    x = _as_array(a)
    if paired or b is not None:
        if b is None:
            d = x
        else:
            y = _as_array(b)
            if x.size != y.size:
                return _insufficient("cohens_d", 0, "paired arrays must match")
            d = x - y
        n = int(d.size)
        if n < _MIN_EFFECT:
            return _insufficient("cohens_d", n)
        sd = float(np.std(d, ddof=1))
        if sd == 0:
            return StatResult(
                ok=True,
                method="cohens_d_paired",
                n=n,
                effect_size=0.0,
                statistic=float(np.mean(d)),
                notes=["zero variance; effect size 0"],
            )
        es = float(np.mean(d) / sd)
        return StatResult(
            ok=True,
            method="cohens_d_paired",
            n=n,
            effect_size=es,
            statistic=float(np.mean(d)),
            notes=["paired Cohen's d = mean(diff)/sd(diff)"],
        )
    n = int(x.size)
    if n < _MIN_EFFECT:
        return _insufficient("cohens_d", n)
    # one-sample vs 0
    sd = float(np.std(x, ddof=1))
    if sd == 0:
        return StatResult(ok=True, method="cohens_d", n=n, effect_size=0.0, notes=["zero variance"])
    return StatResult(
        ok=True,
        method="cohens_d",
        n=n,
        effect_size=float(np.mean(x) / sd),
        statistic=float(np.mean(x)),
        notes=["one-sample Cohen's d vs 0"],
    )


def cliffs_delta(
    a: Sequence[float] | np.ndarray,
    b: Sequence[float] | np.ndarray,
) -> StatResult:
    """Cliff's delta effect size."""

    x = _as_array(a)
    y = _as_array(b)
    n1, n2 = int(x.size), int(y.size)
    if n1 < 1 or n2 < 1:
        return _insufficient("cliffs_delta", n1 + n2)
    # Efficient pairwise comparison via broadcasting for moderate n
    gt = 0
    lt = 0
    for xi in x:
        gt += int(np.sum(xi > y))
        lt += int(np.sum(xi < y))
    delta = (gt - lt) / (n1 * n2)
    return StatResult(
        ok=True,
        method="cliffs_delta",
        n=n1 + n2,
        effect_size=float(delta),
        notes=["Cliff's delta in [-1, 1]"],
        metadata={"n_a": n1, "n_b": n2},
    )


def mean_ci_normal(
    values: Sequence[float] | np.ndarray,
    *,
    alpha: float = 0.05,
) -> StatResult:
    """Normal-approximation CI for the mean (z-based; no t from scipy)."""

    x = _as_array(values)
    n = int(x.size)
    if n < 2:
        return _insufficient("mean_ci_normal", n)
    mean = float(np.mean(x))
    se = float(np.std(x, ddof=1) / np.sqrt(n))
    # z_{1-alpha/2} ≈ 1.95996398454 for alpha=0.05; compute via erfcinv
    z = float(np.sqrt(2) * _erfcinv(alpha))
    return StatResult(
        ok=True,
        method="mean_ci_normal",
        n=n,
        statistic=mean,
        ci_low=mean - z * se,
        ci_high=mean + z * se,
        notes=["Normal z-interval (no Student-t; numpy-only)"],
        metadata={"alpha": alpha, "se": se, "z": z},
    )


def _erfcinv(y: float) -> float:
    """Inverse complementary error function for two-tailed z from alpha."""

    # For two-sided CI: P(|Z|>z)=alpha ⇒ erfc(z/sqrt(2))=alpha ⇒ z=sqrt(2)*erfcinv(alpha)
    # Use binary search on math.erfc
    lo, hi = 0.0, 10.0
    target = y
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        val = float(math.erfc(mid))
        if val > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
