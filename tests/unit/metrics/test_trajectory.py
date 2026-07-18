"""Trajectory metric tests."""

from __future__ import annotations

from githubbench_delta.core.models import ExpectedToolCall

from .helpers import make_context, make_metric


def test_tool_economy_f1_positive(app_config) -> None:
    m = make_metric("tool_economy", app_config)
    ctx = make_context(
        expected_tools=[
            ExpectedToolCall(name="search_repository"),
            ExpectedToolCall(name="read_file"),
        ],
        tool_names=["search_repository", "read_file"],
    )
    r = m.evaluate(ctx)
    assert r.score == 1.0


def test_tool_economy_budget_mode(app_config) -> None:
    m = make_metric("tool_economy", app_config)
    ctx = make_context(tool_names=["read_file"] * 5, success=True)
    r = m.evaluate(ctx)
    assert 0.0 < r.score <= 1.0


def test_unnecessary_tool_calls_duplicates(app_config) -> None:
    m = make_metric("unnecessary_tool_calls", app_config)
    ctx = make_context(
        expected_tools=[ExpectedToolCall(name="read_file")],
        tool_names=["read_file", "read_file", "search_repository"],
    )
    r = m.evaluate(ctx)
    assert r.score < 1.0
    assert r.details["unnecessary_ratio"] > 0


def test_unnecessary_clean(app_config) -> None:
    m = make_metric("unnecessary_tool_calls", app_config)
    ctx = make_context(
        expected_tools=[
            ExpectedToolCall(name="search_repository"),
            ExpectedToolCall(name="read_file"),
        ],
        tool_names=["search_repository", "read_file"],
    )
    r = m.evaluate(ctx)
    assert r.score >= 0.9


def test_planning_quality_lcs(app_config) -> None:
    m = make_metric("planning_quality", app_config)
    ctx = make_context(
        expected_tools=[
            ExpectedToolCall(name="search_repository"),
            ExpectedToolCall(name="read_file"),
            ExpectedToolCall(name="list_files"),
        ],
        tool_names=["search_repository", "read_file", "list_files"],
    )
    r = m.evaluate(ctx)
    assert r.score == 1.0


def test_planning_quality_reordered(app_config) -> None:
    m = make_metric("planning_quality", app_config)
    ctx = make_context(
        expected_tools=[
            ExpectedToolCall(name="search_repository"),
            ExpectedToolCall(name="read_file"),
        ],
        tool_names=["read_file", "search_repository"],
    )
    r = m.evaluate(ctx)
    assert 0.0 < r.score < 1.0
