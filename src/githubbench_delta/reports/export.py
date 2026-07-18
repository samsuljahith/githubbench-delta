"""ExportManager: write Markdown / HTML / PDF / JSON / CSV reports."""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

from githubbench_delta.reports.assets import AssetManager
from githubbench_delta.reports.base import ReportFormat
from githubbench_delta.reports.models import ReportDocument, ReportRequest
from githubbench_delta.reports.templates_engine import TemplateEngine

logger = logging.getLogger(__name__)


def weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False


class ExportManager:
    """Serialize a ReportDocument to one or more formats on disk."""

    def __init__(
        self,
        *,
        template_dir: Path | None = None,
    ) -> None:
        self.template_engine = TemplateEngine(template_dir)

    def export(
        self,
        doc: ReportDocument,
        request: ReportRequest,
        *,
        output_dir: Path,
        preferred_name: str | None = None,
    ) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        assets = AssetManager(output_dir, brand=doc.brand)
        assets.prepare()
        asset_ctx = assets.context()

        stem = preferred_name or self._default_stem(doc, request)
        written: list[Path] = []
        formats = [
            ReportFormat(f) if not isinstance(f, ReportFormat) else f for f in request.formats
        ]

        for fmt in formats:
            if fmt == ReportFormat.JSON:
                path = output_dir / f"{stem}.json"
                path.write_text(
                    json.dumps(doc.model_dump(mode="json"), indent=2) + "\n",
                    encoding="utf-8",
                )
                written.append(path)
            elif fmt == ReportFormat.CSV:
                path = output_dir / f"{stem}.csv"
                path.write_text(self._to_csv(doc), encoding="utf-8")
                written.append(path)
            elif fmt == ReportFormat.MARKDOWN:
                path = output_dir / f"{stem}.md"
                body = self.template_engine.render(doc, fmt="markdown", asset_context=asset_ctx)
                path.write_text(body, encoding="utf-8")
                written.append(path)
            elif fmt == ReportFormat.HTML:
                path = output_dir / f"{stem}.html"
                body = self.template_engine.render(
                    doc, fmt="html", asset_context=asset_ctx, print_mode=False
                )
                path.write_text(body, encoding="utf-8")
                written.append(path)
            elif fmt == ReportFormat.PDF:
                path = self._export_pdf(doc, output_dir, stem, asset_ctx)
                if path is not None:
                    written.append(path)
            else:
                logger.warning("Unsupported format: %s", fmt)
        return written

    def _export_pdf(
        self,
        doc: ReportDocument,
        output_dir: Path,
        stem: str,
        asset_ctx: dict,
    ) -> Path | None:
        if not weasyprint_available():
            logger.warning("WeasyPrint unavailable; skipping PDF export")
            return None
        try:
            from weasyprint import HTML

            html_body = self.template_engine.render(
                doc, fmt="pdf", asset_context=asset_ctx, print_mode=True
            )
            # Write intermediate HTML for debugging / base_url resolution
            html_path = output_dir / f"{stem}.print.html"
            html_path.write_text(html_body, encoding="utf-8")
            pdf_path = output_dir / f"{stem}.pdf"
            HTML(filename=str(html_path), base_url=str(output_dir.resolve())).write_pdf(
                str(pdf_path)
            )
            return pdf_path
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF export failed: %s", exc)
            return None

    @staticmethod
    def _default_stem(doc: ReportDocument, request: ReportRequest) -> str:
        if request.baseline_id and request.candidate_id:
            return f"{request.baseline_id}_vs_{request.candidate_id}_{doc.report_type.value}"
        eid = doc.experiment_ids[0] if doc.experiment_ids else "report"
        return f"{eid}_{doc.report_type.value}"

    @staticmethod
    def _to_csv(doc: ReportDocument) -> str:
        buf = io.StringIO()
        if doc.report_type.value in {"task_analysis"} and doc.tasks:
            fieldnames = [
                "task_id",
                "category",
                "difficulty",
                "language",
                "mean_score",
                "n_evals",
            ]
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in doc.tasks:
                writer.writerow(row)
        elif doc.leaderboard and doc.report_type.value in {
            "executive",
            "agent_comparison",
            "ci_summary",
        }:
            fieldnames = [
                "agent_id",
                "overall_score",
                "confidence",
                "cost_usd",
                "latency_ms",
                "success_rate",
                "n_trials",
            ]
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in doc.leaderboard:
                writer.writerow(row)
        else:
            fieldnames = [
                "experiment_id",
                "task_id",
                "agent_id",
                "trial_index",
                "overall_score",
                "confidence_score",
                "success",
                "category",
                "latency_ms",
                "cost_usd",
            ]
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in doc.evaluations:
                writer.writerow(row)
        return buf.getvalue()
