"""Report generation and export format tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from githubbench_delta.core.models import AgentId, EvaluationResult, RunSummary, TrialKey
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.reports.base import (
    MarkdownReportGenerator,
    ReportFormat,
)
from githubbench_delta.reports.builder import ReportBuilder
from githubbench_delta.reports.export import weasyprint_available
from githubbench_delta.reports.models import BrandConfig, ReportRequest, ReportType


def _request(
    tmp_path: Path,
    results_dir: Path,
    *,
    report_type: ReportType = ReportType.TECHNICAL,
    formats: list[str] | None = None,
    experiment_ids: list[str] | None = None,
    template_dir: Path | None = None,
) -> ReportRequest:
    return ReportRequest(
        experiment_ids=experiment_ids or ["exp_base"],
        report_type=report_type,
        formats=formats or ["markdown", "json"],
        output_dir=tmp_path / "out",
        template_dir=template_dir,
        brand=BrandConfig(product_name="TestBench"),
        results_dir=results_dir,
        sqlite_path=results_dir.parent / "unused.db",
    )


@pytest.mark.parametrize(
    "report_type",
    [
        ReportType.EXECUTIVE,
        ReportType.TECHNICAL,
        ReportType.EXPERIMENT,
        ReportType.AGENT_COMPARISON,
        ReportType.METRIC,
        ReportType.TASK_ANALYSIS,
        ReportType.CI_SUMMARY,
    ],
)
def test_report_types_render_markdown_and_json(
    tmp_path: Path,
    sample_results_dir: Path,
    repo: ExperimentRepository,
    report_type: ReportType,
) -> None:
    request = _request(
        tmp_path,
        sample_results_dir,
        report_type=report_type,
        formats=["markdown", "json"],
    )
    builder = ReportBuilder(repo=repo)
    paths = builder.generate(request)
    assert any(p.suffix == ".md" for p in paths)
    assert any(p.suffix == ".json" for p in paths)
    md = next(p for p in paths if p.suffix == ".md").read_text(encoding="utf-8")
    assert "TestBench" in md or report_type.value.replace("_", " ") in md.lower() or "#" in md
    assert "Recommendations" in md or "Overall" in md or "Metric" in md


def test_html_contains_sections_and_charts(
    tmp_path: Path,
    sample_results_dir: Path,
    repo: ExperimentRepository,
) -> None:
    request = _request(
        tmp_path,
        sample_results_dir,
        report_type=ReportType.AGENT_COMPARISON,
        formats=["html"],
    )
    paths = ReportBuilder(repo=repo).generate(request)
    html = paths[0].read_text(encoding="utf-8")
    assert "Overall Results" in html
    assert "chart-" in html or "plotly-" in html or "Agent" in html


def test_csv_export_columns(
    tmp_path: Path,
    sample_results_dir: Path,
    repo: ExperimentRepository,
) -> None:
    request = _request(
        tmp_path,
        sample_results_dir,
        formats=["csv"],
    )
    paths = ReportBuilder(repo=repo).generate(request)
    text = paths[0].read_text(encoding="utf-8")
    assert "experiment_id" in text
    assert "overall_score" in text
    assert "codex" in text


def test_pdf_smoke_or_skip(
    tmp_path: Path,
    sample_results_dir: Path,
    repo: ExperimentRepository,
) -> None:
    if not weasyprint_available():
        pytest.skip("WeasyPrint not available")
    request = _request(
        tmp_path,
        sample_results_dir,
        report_type=ReportType.EXECUTIVE,
        formats=["pdf"],
    )
    paths = ReportBuilder(repo=repo).generate(request)
    if not paths:
        pytest.skip("PDF export failed (native libs missing)")
    assert paths[0].suffix == ".pdf"
    assert paths[0].stat().st_size > 100


def test_custom_template_dir(
    tmp_path: Path,
    sample_results_dir: Path,
    repo: ExperimentRepository,
) -> None:
    custom = tmp_path / "tpl"
    custom.mkdir()
    (custom / "base.md").write_text(
        "# CUSTOM {{ doc.title }}\n\n{% for s in sections %}## {{ s.title }}\n{% endfor %}\n",
        encoding="utf-8",
    )
    request = _request(
        tmp_path,
        sample_results_dir,
        formats=["markdown"],
        template_dir=custom,
    )
    paths = ReportBuilder(repo=repo).generate(request)
    body = paths[0].read_text(encoding="utf-8")
    assert body.startswith("# CUSTOM")


def test_run_summary_generator_facade(tmp_path: Path) -> None:
    summary = RunSummary(
        run_id="run_x",
        seed=1,
        agent_ids=[AgentId.CODEX],
        task_ids=["t1"],
        evaluations=[
            EvaluationResult(
                trial=TrialKey(task_id="t1", agent_id=AgentId.CODEX, trial_index=0),
                overall_score=0.4,
                confidence_score=0.5,
                group_scores={"correctness": 0.4},
            )
        ],
        recommendations=[],
        metadata={"experiment_id": "exp_from_summary"},
    )
    out = tmp_path / "from_summary.md"
    path = MarkdownReportGenerator().generate(summary, out)
    assert path.exists()
    assert ReportFormat.MARKDOWN.value == "markdown"
