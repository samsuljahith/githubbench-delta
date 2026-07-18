"""Configuration loading tests."""

from __future__ import annotations

from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS, PEER_RUN_METRIC_IDS
from githubbench_delta.core.models import AgentId


def test_load_default_config(app_config) -> None:
    assert app_config.runtime.seed == 42
    assert app_config.runtime.trial_count == 3
    assert set(app_config.agents) == {a.value for a in AgentId}
    assert set(app_config.evaluators) == set(METHODOLOGY_METRIC_IDS)


def test_all_eighteen_evaluators_configured(app_config) -> None:
    assert len(app_config.evaluators) == 18
    for metric_id in METHODOLOGY_METRIC_IDS:
        cfg = app_config.evaluators[metric_id]
        assert cfg.id == metric_id
        assert cfg.weight >= 0.0
        assert cfg.enabled is True


def test_peer_run_flags(app_config) -> None:
    for metric_id in PEER_RUN_METRIC_IDS:
        assert app_config.evaluators[metric_id].requires_peer_runs is True
