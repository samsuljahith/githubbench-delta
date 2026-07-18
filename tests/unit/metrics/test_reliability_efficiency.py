"""Reliability and efficiency metric tests."""

from __future__ import annotations

from githubbench_delta.core.models import (
    AgentId,
    AgentResult,
    EvaluationResult,
    TaskOutput,
    TrialKey,
)

from .helpers import make_context, make_metric


def test_recovery_after_failure(app_config) -> None:
    m = make_metric("recovery_score", app_config)
    ctx = make_context(
        tool_names=["read_file", "read_file"],
        tool_failures=[True, False],
    )
    r = m.evaluate(ctx)
    assert r.score == 1.0


def test_recovery_no_failures(app_config) -> None:
    m = make_metric("recovery_score", app_config)
    ctx = make_context(tool_names=["read_file"])
    r = m.evaluate(ctx)
    assert r.score == 1.0


def test_calibration_aligned(app_config) -> None:
    m = make_metric("calibration", app_config)
    ctx = make_context(
        response="widgetcli/store.py add method",
        confidence=0.9,
    )
    r = m.evaluate(ctx)
    assert r.score >= 0.7
    assert not r.skipped


def test_calibration_missing_confidence_skip(app_config) -> None:
    m = make_metric("calibration", app_config)
    ctx = make_context(confidence=None)
    r = m.evaluate(ctx)
    assert r.skipped is True


def test_cross_trial_consistency_peers(app_config) -> None:
    m = make_metric("cross_trial_consistency", app_config)
    peer = AgentResult(
        agent_id=AgentId.CODEX,
        task_id="t1",
        output=TaskOutput(content="widgetcli/store.py defines WidgetStore.add"),
        success=True,
    )
    ctx = make_context(
        response="widgetcli/store.py defines WidgetStore.add",
        peer_results=[peer],
    )
    r = m.evaluate(ctx)
    assert r.score == 1.0


def test_cross_trial_skip_without_peers(app_config) -> None:
    m = make_metric("cross_trial_consistency", app_config)
    r = m.evaluate(make_context())
    assert r.skipped is True


def test_cross_trial_from_peer_evaluations(app_config) -> None:
    m = make_metric("cross_trial_consistency", app_config)
    trial = TrialKey(task_id="t1", agent_id=AgentId.CODEX)
    peers = [
        EvaluationResult(trial=trial, overall_score=0.8),
        EvaluationResult(trial=trial, overall_score=0.82),
    ]
    ctx = make_context(peer_evaluations=peers)
    # peer_results empty but peer_evaluations present
    ctx.peer_results = []
    r = m.evaluate(ctx)
    assert not r.skipped
    assert r.score > 0.5


def test_reproducibility_similar(app_config) -> None:
    m = make_metric("reproducibility", app_config)
    peer_ctx = make_context(tool_names=["search_repository", "read_file"])
    ctx = make_context(
        tool_names=["search_repository", "read_file"],
        peer_results=[peer_ctx.agent_result],
    )
    r = m.evaluate(ctx)
    assert r.score == 1.0


def test_cost_normalized_free_success(app_config) -> None:
    m = make_metric("cost_normalized_capability", app_config)
    ctx = make_context(
        response="widgetcli/store.py add",
        success=True,
        cost_usd=0.0,
    )
    r = m.evaluate(ctx)
    assert r.score > 0.5


def test_cost_normalized_expensive(app_config) -> None:
    m = make_metric("cost_normalized_capability", app_config)
    cheap = make_metric("cost_normalized_capability", app_config).evaluate(
        make_context(response="widgetcli/store.py add", success=True, cost_usd=0.0)
    )
    expensive = m.evaluate(
        make_context(response="widgetcli/store.py add", success=True, cost_usd=5.0)
    )
    assert expensive.score < cheap.score


def test_local_vs_hosted_parity(app_config) -> None:
    m = make_metric("local_vs_hosted_parity", app_config)
    local = make_context(
        agent_id=AgentId.MINICPM,
        success=True,
        response="ok answer with enough text",
    ).agent_result
    hosted = make_context(
        agent_id=AgentId.CLAUDE,
        success=True,
        response="ok answer with enough text",
    ).agent_result
    ctx = make_context(
        agent_id=AgentId.MINICPM,
        success=True,
        response="ok answer with enough text",
        peer_results=[hosted],
    )
    # ensure primary is local
    ctx.agent_result = local
    r = m.evaluate(ctx)
    assert not r.skipped
    assert r.score >= 0.8


def test_local_vs_hosted_skip(app_config) -> None:
    m = make_metric("local_vs_hosted_parity", app_config)
    r = m.evaluate(make_context(agent_id=AgentId.CODEX))
    assert r.skipped is True
