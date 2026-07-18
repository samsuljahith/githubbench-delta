"""Correctness metric tests."""

from __future__ import annotations

from githubbench_delta.core.models import DiffStats, GoldAnswer

from .helpers import make_context, make_metric


def test_task_resolution_positive(app_config) -> None:
    m = make_metric("task_resolution", app_config)
    ctx = make_context(
        response="See widgetcli/store.py method add for storing widgets",
    )
    r = m.evaluate(ctx)
    assert r.score >= 0.7
    assert r.reasoning
    assert r.metric_version == "1.0.0"


def test_task_resolution_negative(app_config) -> None:
    m = make_metric("task_resolution", app_config)
    ctx = make_context(response="I have no idea")
    r = m.evaluate(ctx)
    assert r.score < 0.4


def test_task_resolution_alternate_gold(app_config) -> None:
    m = make_metric("task_resolution", app_config)
    ctx = make_context(
        response="use alternative path foo.py::bar",
        gold=GoldAnswer(content="missing", acceptance_criteria=["zzz"]),
        alternate_golds=[GoldAnswer(content="foo.py::bar", acceptance_criteria=["foo.py", "bar"])],
    )
    r = m.evaluate(ctx)
    assert r.score >= 0.6


def test_task_resolution_no_gold_skip(app_config) -> None:
    m = make_metric("task_resolution", app_config)
    ctx = make_context()
    ctx.gold_answer = None
    ctx.alternate_gold_answers = []
    r = m.evaluate(ctx)
    assert r.skipped is True


def test_engineering_usefulness_vacuous(app_config) -> None:
    m = make_metric("engineering_usefulness", app_config)
    ctx = make_context(response="ok", success=True)
    r = m.evaluate(ctx)
    assert r.score < 0.7
    assert (
        any(
            "substantive" in s.lower() or "vacuous" in str(r.evidence).lower()
            for s in r.suggested_improvements
        )
        or r.score < 0.8
    )


def test_engineering_usefulness_positive(app_config) -> None:
    m = make_metric("engineering_usefulness", app_config)
    ctx = make_context(
        response="Fixed the bug in widgetcli/store.py by validating add()",
        success=True,
    )
    r = m.evaluate(ctx)
    assert r.score >= 0.7


def test_diff_minimality_small(app_config) -> None:
    m = make_metric("diff_minimality", app_config)
    ctx = make_context(
        diff=DiffStats(
            changed_files=["widgetcli/store.py"],
            insertions=5,
            deletions=1,
            justified_files=["widgetcli/store.py"],
        ),
        task_files=["widgetcli/store.py"],
    )
    r = m.evaluate(ctx)
    assert r.score >= 0.85


def test_diff_minimality_bloated(app_config) -> None:
    m = make_metric("diff_minimality", app_config)
    files = [f"f{i}.py" for i in range(25)]
    ctx = make_context(
        diff=DiffStats(
            changed_files=files,
            insertions=400,
            deletions=200,
            justified_files=["f0.py"],
        ),
        task_files=["f0.py"],
    )
    r = m.evaluate(ctx)
    assert r.score < 0.3


def test_diff_minimality_no_diff(app_config) -> None:
    m = make_metric("diff_minimality", app_config)
    ctx = make_context(diff=None)
    r = m.evaluate(ctx)
    assert r.score == 1.0
