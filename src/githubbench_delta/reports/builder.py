"""ReportBuilder: orchestrate context → sections → charts → export."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.models import RunSummary
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.reports.charts_bridge import collect_charts
from githubbench_delta.reports.compare import compare_agents, compare_experiments
from githubbench_delta.reports.context import (
    document_from_run_summary,
    load_report_document,
    make_repository,
    resolve_output_dir,
)
from githubbench_delta.reports.export import ExportManager
from githubbench_delta.reports.models import ReportDocument, ReportRequest, ReportType
from githubbench_delta.reports.recommendations import (
    collect_warnings,
    generate_recommendations,
)
from githubbench_delta.reports.sections import SectionRegistry


class ReportBuilder:
    """Build and export publication reports from experiment artifacts."""

    def __init__(
        self,
        *,
        repo: ExperimentRepository | None = None,
        registry: SectionRegistry | None = None,
    ) -> None:
        self.repo = repo
        self.registry = registry or SectionRegistry()

    def build(self, request: ReportRequest) -> ReportDocument:
        repo = self.repo or make_repository(request)
        doc = load_report_document(repo, request)

        if request.baseline_id and request.candidate_id:
            doc.diff = compare_experiments(
                repo,
                request.baseline_id,
                request.candidate_id,
            )
        elif (
            request.report_type == ReportType.AGENT_COMPARISON
            and doc.experiment_ids
            and len(doc.metadata.get("agent_ids") or []) >= 2
        ):
            agents = list(doc.metadata["agent_ids"])
            doc.diff = compare_agents(repo, doc.experiment_ids[0], agents[0], agents[1])

        _, traj_notes = self._traj_warning_notes(repo, doc)
        doc.warnings = collect_warnings(doc, traj_notes)
        doc.recommendations = generate_recommendations(doc)

        doc.sections = self.registry.build_all(doc, repo)

        out_dir = resolve_output_dir(request)
        assets_dir = out_dir / "_assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        # Kaleido PNGs for PDF embedding; Markdown uses paths when PNGs exist.
        need_png = any(str(f) == "pdf" for f in request.formats)
        doc.charts = collect_charts(
            repo,
            doc,
            assets_dir=assets_dir,
            write_png=need_png,
        )
        return doc

    def build_from_run_summary(self, summary: RunSummary, request: ReportRequest) -> ReportDocument:
        doc = document_from_run_summary(summary, request)
        doc.warnings = collect_warnings(doc)
        if not doc.recommendations:
            doc.recommendations = generate_recommendations(doc)
        doc.sections = self.registry.build_all(doc, None)
        return doc

    def export(
        self,
        doc: ReportDocument,
        request: ReportRequest,
        *,
        preferred_name: str | None = None,
    ) -> list[Path]:
        output_dir = resolve_output_dir(request)
        exporter = ExportManager(template_dir=request.template_dir)
        return exporter.export(doc, request, output_dir=output_dir, preferred_name=preferred_name)

    def generate(self, request: ReportRequest) -> list[Path]:
        doc = self.build(request)
        return self.export(doc, request)

    @staticmethod
    def _traj_warning_notes(
        repo: ExperimentRepository, doc: ReportDocument
    ) -> tuple[int, list[str]]:
        notes: list[str] = []
        count = 0
        for eid in doc.experiment_ids:
            for item in repo.list_trajectories(eid)[:100]:
                detail = repo.get_trajectory(eid, item.unit_key)
                if not detail:
                    continue
                for w in detail.warnings or []:
                    notes.append(f"{item.unit_key}: {w}")
                    count += 1
        return count, notes
