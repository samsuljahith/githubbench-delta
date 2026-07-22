"""Unit tests for research power estimators."""

from __future__ import annotations

from githubbench_delta.research.power import MDEEstimator, SampleSizeEstimator, VarianceEstimator


def test_variance_insufficient():
    r = VarianceEstimator().estimate([])
    assert r.ok is False
    assert "insufficient_data" in r.notes


def test_sample_size_insufficient_no_mde():
    r = SampleSizeEstimator().estimate([1.0, 2.0, 3.0], mde=None)
    assert r.ok is False
    assert "insufficient_data" in r.notes


def test_sample_size_ok():
    r = SampleSizeEstimator().estimate([1.0, 1.2, 0.9, 1.1, 1.05], alpha=0.05, power=0.8, mde=0.5)
    assert r.ok is True
    assert r.n_required is not None and r.n_required >= 2


def test_mde_insufficient():
    r = MDEEstimator().estimate([1.0])
    assert r.ok is False


def test_mde_ok():
    r = MDEEstimator().estimate([1.0, 1.1, 0.9, 1.05, 0.95], n=30)
    assert r.ok is True
    assert r.mde is not None and r.mde > 0
