"""MDS helper and Bayesian edge-case tests."""

from __future__ import annotations

from githubbench_delta.memorization.bayesian import BayesianDiscountModel, _norm_ppf
from githubbench_delta.memorization.helpers import clamp01, normalize_prompt


def test_clamp_and_normalize() -> None:
    assert clamp01(1.5) == 1.0
    assert clamp01(-0.1) == 0.0
    assert normalize_prompt("  Hello   World ") == "hello world"


def test_norm_ppf_median() -> None:
    assert abs(_norm_ppf(0.5)) < 1e-3


def test_bayesian_interval_ordering() -> None:
    post = BayesianDiscountModel().fit_posterior(
        [0.4, 0.5, 0.6], agent_id="x", mean_obs=0.7, level=0.9
    )
    assert post.lower <= post.mean <= post.upper
    assert post.discounted_lower is not None
    assert post.discounted_upper is not None
    assert post.discounted_lower <= post.discounted_mean <= post.discounted_upper
