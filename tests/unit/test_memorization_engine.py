"""Unit tests for MDS twins, estimator, Bayesian model, and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from githubbench_delta.cli import app as cli_app
from githubbench_delta.dashboard.schemas import EvaluationRow
from githubbench_delta.memorization.bayesian import BayesianDiscountModel
from githubbench_delta.memorization.decompose import CapabilityDecomposer
from githubbench_delta.memorization.engine import MemorizationEngine
from githubbench_delta.memorization.estimator import MemorizationEstimator
from githubbench_delta.memorization.models import TwinTaskSpec
from githubbench_delta.memorization.report import MemorizationReportGenerator
from githubbench_delta.memorization.twins import TwinTaskGenerator
from githubbench_delta.memorization.validate import TwinValidationError, TwinValidator

runner = CliRunner()


def _row(
    *,
    agent: str,
    task: str,
    score: float,
    metrics: dict[str, float] | None = None,
    experiment_id: str = "exp_mds",
) -> EvaluationRow:
    return EvaluationRow(
        experiment_id=experiment_id,
        run_id="r1",
        unit_key=f"{task}::{agent}::0",
        task_id=task,
        agent_id=agent,
        trial_index=0,
        overall_score=score,
        confidence_score=0.8,
        success=True,
        metric_scores=metrics
        or {
            "reproducibility": 0.9,
            "cross_trial_consistency": 0.85,
            "grounding_ratio": 0.7,
        },
    )


def test_twin_generator_distinct_prompt(tmp_path: Path) -> None:
    parent = {
        "id": "gb-demo-001",
        "title": "Find the module",
        "description": "Explain the design.",
        "input": {"prompt": "Find where WidgetStore.add is defined.", "files": []},
        "gold_answer": {"format": "text", "content": "store.py"},
        "repository": {"local_path": "datasets/fixtures/py_cli"},
        "metadata": {"extra": {"fixture": "py_cli"}},
    }
    path = tmp_path / "tasks.jsonl"
    path.write_text(json.dumps(parent) + "\n", encoding="utf-8")
    specs = TwinTaskGenerator().generate_from_dataset(path)
    assert len(specs) == 1
    assert specs[0].parent_task_id == "gb-demo-001"
    assert specs[0].id.endswith("__twin_para_01")
    assert specs[0].record["input"]["prompt"] != parent["input"]["prompt"]
    TwinValidator().validate_catalog(specs, parents={"gb-demo-001": parent})


def test_twin_validator_rejects_same_prompt() -> None:
    parent = {
        "id": "p1",
        "input": {"prompt": "Same prompt"},
        "gold_answer": {"content": "x"},
        "repository": {"url": "u"},
    }
    twin = TwinTaskSpec(
        id="p1__twin_para_01",
        parent_task_id="p1",
        record={
            "id": "p1__twin_para_01",
            "input": {"prompt": "Same prompt"},
            "gold_answer": {"content": "x"},
            "repository": {"url": "u"},
            "metadata": {"extra": {"parent_task_id": "p1"}},
        },
    )
    errs = TwinValidator().validate_spec(twin, parent=parent)
    assert any("differ" in e.lower() for e in errs)


def test_estimator_twin_mode_lift() -> None:
    rows = [
        _row(agent="minicpm", task="t1", score=0.80),
        _row(agent="minicpm", task="t1__twin_para_01", score=0.50),
        _row(agent="codex", task="t1", score=0.70),
        _row(agent="codex", task="t1__twin_para_01", score=0.65),
    ]
    specs = [
        TwinTaskSpec(
            id="t1__twin_para_01",
            parent_task_id="t1",
            record={"id": "t1__twin_para_01"},
        )
    ]
    lifts, mode, _notes = MemorizationEstimator().estimate(rows, twin_specs=specs)
    assert mode == "twin"
    by_agent = {x.agent_id: x for x in lifts}
    assert by_agent["minicpm"].mean_lift == pytest.approx(0.30, abs=1e-6)
    assert by_agent["codex"].mean_lift == pytest.approx(0.05, abs=1e-6)


def test_estimator_proxy_mode() -> None:
    rows = [
        _row(
            agent="minicpm",
            task="t1",
            score=0.55,
            metrics={
                "reproducibility": 0.2,
                "cross_trial_consistency": 0.2,
                "grounding_ratio": 0.2,
            },
        )
    ]
    lifts, mode, notes = MemorizationEstimator().estimate(rows)
    assert mode == "proxy"
    assert lifts[0].mean_lift > 0
    assert any("proxy" in n.lower() for n in notes)


def test_bayesian_posterior_shrinks_with_data() -> None:
    model = BayesianDiscountModel()
    priorish = model.fit_posterior([], agent_id="a", mean_obs=0.6)
    assert priorish.mean == pytest.approx(0.5, abs=1e-6)
    tight = model.fit_posterior([0.1, 0.1, 0.12, 0.08], agent_id="a", mean_obs=0.6)
    assert tight.mean < 0.3
    assert tight.lower <= tight.mean <= tight.upper
    assert tight.discounted_mean is not None


def test_decomposer_identity() -> None:
    rows = [
        _row(agent="a", task="t1", score=0.8),
        _row(agent="a", task="t1__twin_para_01", score=0.5),
    ]
    lifts, _, _ = MemorizationEstimator().estimate(
        rows,
        twin_specs=[TwinTaskSpec(id="t1__twin_para_01", parent_task_id="t1", record={})],
    )
    posts = [
        BayesianDiscountModel().fit_posterior(
            [p.lift for p in lifts[0].pairs],
            agent_id="a",
            mean_obs=lifts[0].mean_obs,
        )
    ]
    br = CapabilityDecomposer().decompose(lifts, posts)[0]
    assert br.observed_score == pytest.approx(0.8)
    assert abs(br.generalization + br.memorization_lift - br.observed_score) < 1e-6


def test_report_artifacts(tmp_path: Path) -> None:
    eid = "exp_mds_fix"
    exp = tmp_path / eid
    exp.mkdir()
    (exp / "experiment.json").write_text(
        json.dumps({"experiment_id": eid, "status": "completed"}),
        encoding="utf-8",
    )
    (exp / "evaluation_results.json").write_text(
        json.dumps(
            [
                {
                    "experiment_id": eid,
                    "run_id": "r1",
                    "unit_key": "t1::minicpm::0",
                    "task_id": "t1",
                    "agent_id": "minicpm",
                    "trial_index": 0,
                    "evaluation": {
                        "overall_score": 0.539,
                        "confidence_score": 0.7,
                        "group_scores": {},
                        "metric_results": {
                            "reproducibility": {"score": 0.4, "skipped": False},
                            "grounding_ratio": {"score": 0.58, "skipped": False},
                            "cross_trial_consistency": {"score": 0.5, "skipped": False},
                        },
                        "metadata": {},
                    },
                    "agent_result_summary": {"success": True},
                }
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    engine = MemorizationEngine(results_dir=tmp_path)
    report = MemorizationReportGenerator(engine=engine).generate(
        [eid], out, formats={"json", "markdown", "html"}
    )
    assert (out / "memorization_report.json").is_file()
    assert (out / "capability_breakdown.md").is_file()
    assert (out / "memorization_dashboard.html").is_file()
    assert report.mode == "proxy"


def test_cli_memorization_help() -> None:
    result = runner.invoke(cli_app, ["memorization", "--help"])
    assert result.exit_code == 0
    assert "analyze" in result.stdout
    assert "generate-twins" in result.stdout


def test_cli_generate_twins_and_analyze(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(
        json.dumps(
            {
                "id": "gb-x-001",
                "title": "Find the bug",
                "description": "Explain the failure.",
                "input": {"prompt": "Find the null pointer in main.", "files": []},
                "gold_answer": {"format": "text", "content": "main.py:10"},
                "repository": {"local_path": "x"},
                "metadata": {"extra": {}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    twins_out = tmp_path / "twins.jsonl"
    gen = runner.invoke(
        cli_app,
        ["memorization", "generate-twins", "--dataset", str(tasks), "-o", str(twins_out)],
    )
    assert gen.exit_code == 0, gen.stdout
    assert twins_out.is_file()

    eid = "exp_cli"
    exp = tmp_path / eid
    exp.mkdir()
    (exp / "experiment.json").write_text("{}", encoding="utf-8")
    (exp / "evaluation_results.json").write_text(
        json.dumps(
            [
                {
                    "experiment_id": eid,
                    "run_id": "r",
                    "unit_key": "gb-x-001::a::0",
                    "task_id": "gb-x-001",
                    "agent_id": "a",
                    "trial_index": 0,
                    "evaluation": {
                        "overall_score": 0.6,
                        "confidence_score": 0.7,
                        "group_scores": {},
                        "metric_results": {"reproducibility": {"score": 0.5, "skipped": False}},
                        "metadata": {},
                    },
                    "agent_result_summary": {"success": True},
                }
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "report"
    result = runner.invoke(
        cli_app,
        [
            "memorization",
            "analyze",
            "-e",
            eid,
            "--experiments-dir",
            str(tmp_path),
            "--twins-path",
            str(twins_out),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (out / "memorization_report.json").is_file()


def test_validator_raises_on_bad_catalog() -> None:
    parent = {
        "id": "p1",
        "input": {"prompt": "abc"},
        "gold_answer": {"c": 1},
        "repository": {"u": 1},
    }
    twin = TwinTaskSpec(
        id="p1__twin_para_01",
        parent_task_id="p1",
        record={
            "id": "p1__twin_para_01",
            "input": {"prompt": "abc"},
            "gold_answer": {"c": 1},
            "repository": {"u": 1},
            "metadata": {"extra": {"parent_task_id": "p1"}},
        },
    )
    with pytest.raises(TwinValidationError):
        TwinValidator().validate_catalog([twin], parents={"p1": parent})
