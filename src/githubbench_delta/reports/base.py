"""Report format enums and thin ReportGenerator façade over ReportBuilder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path

from githubbench_delta.core.models import RunSummary
from githubbench_delta.reports.models import ReportType


class ReportFormat(StrEnum):
    """Supported report output formats."""

    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"


class ReportGenerator(ABC):
    """Generate evaluation reports from a RunSummary (compatibility API)."""

    format: ReportFormat

    @abstractmethod
    def generate(self, summary: RunSummary, output_path: Path) -> Path:
        """Write a report for ``summary`` to ``output_path`` and return the path."""


def _generate_from_summary(
    summary: RunSummary,
    output_path: Path,
    fmt: ReportFormat,
) -> Path:
    from githubbench_delta.reports.builder import ReportBuilder
    from githubbench_delta.reports.models import BrandConfig, ReportRequest

    exp_id = str(summary.metadata.get("experiment_id") or summary.run_id)
    request = ReportRequest(
        experiment_ids=[exp_id] if exp_id else [],
        report_type=ReportType.TECHNICAL,
        formats=[fmt.value],
        output_dir=output_path.parent if output_path.suffix else output_path,
        brand=BrandConfig(),
    )
    builder = ReportBuilder()
    # Prefer RunSummary adapter when artifacts are unavailable.
    doc = builder.build_from_run_summary(summary, request)
    paths = builder.export(doc, request, preferred_name=output_path.stem)
    if not paths:
        raise RuntimeError(f"Failed to export {fmt.value} report")
    # If caller gave an exact file path, rename/move first export.
    written = paths[0]
    if output_path.suffix and written != output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        written.replace(output_path)
        return output_path
    return written


class HTMLReportGenerator(ReportGenerator):
    """HTML report generator."""

    format = ReportFormat.HTML

    def generate(self, summary: RunSummary, output_path: Path) -> Path:
        return _generate_from_summary(summary, output_path, ReportFormat.HTML)


class MarkdownReportGenerator(ReportGenerator):
    """Markdown report generator."""

    format = ReportFormat.MARKDOWN

    def generate(self, summary: RunSummary, output_path: Path) -> Path:
        return _generate_from_summary(summary, output_path, ReportFormat.MARKDOWN)


class JSONReportGenerator(ReportGenerator):
    """JSON report generator."""

    format = ReportFormat.JSON

    def generate(self, summary: RunSummary, output_path: Path) -> Path:
        return _generate_from_summary(summary, output_path, ReportFormat.JSON)


class CSVReportGenerator(ReportGenerator):
    """CSV report generator."""

    format = ReportFormat.CSV

    def generate(self, summary: RunSummary, output_path: Path) -> Path:
        return _generate_from_summary(summary, output_path, ReportFormat.CSV)


class PDFReportGenerator(ReportGenerator):
    """PDF report generator."""

    format = ReportFormat.PDF

    def generate(self, summary: RunSummary, output_path: Path) -> Path:
        return _generate_from_summary(summary, output_path, ReportFormat.PDF)
