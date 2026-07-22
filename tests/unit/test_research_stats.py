"""Unit tests for research stats engine — insufficient_data guards and determinism."""

from __future__ import annotations

import numpy as np

from githubbench_delta.research import stats


def test_bootstrap_insufficient():
    r = stats.bootstrap_ci([])
    assert r.ok is False
    assert "insufficient_data" in r.notes
    assert r.p_value is None
    assert r.ci_low is None


def test_bootstrap_determinism():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    a = stats.bootstrap_ci(x, n_boot=500, seed=42)
    b = stats.bootstrap_ci(x, n_boot=500, seed=42)
    assert a.ok and b.ok
    assert a.ci_low == b.ci_low
    assert a.ci_high == b.ci_high
    assert a.statistic == b.statistic


def test_paired_bootstrap_length_mismatch():
    r = stats.paired_bootstrap([1, 2], [1])
    assert r.ok is False
    assert "insufficient_data" in r.notes


def test_wilcoxon_insufficient():
    r = stats.wilcoxon_signed_rank([1, 2, 3], [1.1, 2.1, 3.1])
    assert r.ok is False
    assert "insufficient_data" in r.notes


def test_wilcoxon_ok_on_enough_pairs():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 20)
    b = a + 0.5
    r = stats.wilcoxon_signed_rank(a, b)
    assert r.ok is True
    assert r.p_value is not None
    assert 0 <= r.p_value <= 1


def test_mann_whitney_insufficient():
    r = stats.mann_whitney_u([1, 2], [3, 4])
    assert r.ok is False


def test_bh_fdr_empty():
    assert stats.bh_fdr([]) == []


def test_bh_fdr_known():
    # Classic: p = [0.01, 0.04, 0.03, 0.50] alpha=0.05
    # ordered 0.01, 0.03, 0.04, 0.50; thresh 0.0125, 0.025, 0.0375, 0.05
    # only 0.01 rejects under strict BH for this set at 0.05?
    # 0.01 <= 0.0125 yes; 0.03 > 0.025 no → only first
    out = stats.bh_fdr([0.01, 0.04, 0.03, 0.50], alpha=0.05)
    assert len(out) == 4
    by_idx = {row["index"]: row for row in out}
    assert by_idx[0]["reject"] is True
    assert by_idx[3]["reject"] is False
    assert all("p_adjusted" in row for row in out)


def test_permutation_insufficient():
    r = stats.permutation_test([], [1])
    assert r.ok is False


def test_mcnemar_insufficient():
    r = stats.mcnemar_test(discordant=(0, 0))
    assert r.ok is False
    assert "insufficient_data" in r.notes


def test_mcnemar_ok():
    r = stats.mcnemar_test(discordant=(10, 2))
    assert r.ok is True
    assert r.p_value is not None


def test_cliffs_and_cohens():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [2.0, 3.0, 4.0, 5.0]
    d = stats.cliffs_delta(a, b)
    assert d.ok and d.effect_size is not None
    c = stats.cohens_d(a, b, paired=True)
    assert c.ok and c.effect_size is not None


def test_mean_ci_insufficient():
    r = stats.mean_ci_normal([1.0])
    assert r.ok is False
