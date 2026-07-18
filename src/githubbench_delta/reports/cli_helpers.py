"""CLI argument parsing helpers for report commands."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.config import load_config
from githubbench_delta.reports.base import ReportFormat
from githubbench_delta.reports.models import BrandConfig, ReportRequest, ReportType


def parse_report_type(value: str) -> ReportType:
    try:
        return ReportType(value)
    except ValueError as exc:
        valid = ", ".join(t.value for t in ReportType)
        raise ValueError(f"Unknown report type {value!r}. Choose from: {valid}") from exc


def parse_formats(values: list[str]) -> list[str]:
    out: list[str] = []
    for v in values:
        try:
            out.append(ReportFormat(v).value)
        except ValueError as exc:
            valid = ", ".join(f.value for f in ReportFormat)
            raise ValueError(f"Unknown format {v!r}. Choose from: {valid}") from exc
    return out or [ReportFormat.MARKDOWN.value]


def build_request(
    *,
    experiment: list[str] | None = None,
    report_type: str = "technical",
    formats: list[str] | None = None,
    output: Path | None = None,
    template_dir: Path | None = None,
    baseline: str | None = None,
    candidate: str | None = None,
    agent: str | None = None,
    results_dir: Path | None = None,
) -> ReportRequest:
    cfg = load_config()
    exp_ids = list(experiment or [])
    if baseline and baseline not in exp_ids:
        exp_ids.append(baseline)
    if candidate and candidate not in exp_ids:
        exp_ids.append(candidate)
    return ReportRequest(
        experiment_ids=exp_ids,
        report_type=parse_report_type(report_type),
        formats=parse_formats(formats or ["markdown"]),
        output_dir=output or Path(cfg.runtime.paths.reports),
        template_dir=template_dir,
        brand=BrandConfig(),
        baseline_id=baseline,
        candidate_id=candidate,
        agent_id=agent,
        results_dir=results_dir or Path(cfg.runtime.pipeline.results_dir),
        sqlite_path=Path(cfg.runtime.storage.sqlite_path),
    )
