"""Validation dashboard HTML from registry + evidence + readiness."""

from __future__ import annotations

import html
from pathlib import Path

from githubbench_delta.research.registry import ExperimentRegistry
from githubbench_delta.research.scheduler import ExperimentScheduler


def _esc(s: object) -> str:
    return html.escape(str(s), quote=True)


class ValidationDashboard:
    """Build validation_report.html — never fabricates statistical claims."""

    def __init__(
        self,
        registry: ExperimentRegistry | None = None,
        *,
        workspace: Path | None = None,
    ) -> None:
        self.registry = registry or ExperimentRegistry.load_default()
        self.workspace = workspace or Path.cwd()
        self.scheduler = ExperimentScheduler(self.registry, workspace=self.workspace)

    def build_html(self) -> str:
        statuses = {s.experiment_id: s for s in self.scheduler.all_statuses()}
        experiments = self.registry.list_experiments()
        evidence = self.registry.evidence_nodes()

        runnable = [e for e in experiments if statuses[e.id].status == "runnable"]
        blocked = [e for e in experiments if statuses[e.id].status == "blocked"]
        pending = [e for e in experiments if statuses[e.id].status == "pending_data"]
        completed = [e for e in experiments if statuses[e.id].status == "completed"]

        parts = [
            "<!DOCTYPE html>",
            '<html lang="en"><head><meta charset="utf-8"/>',
            "<title>Research Validation Report</title>",
            "<style>",
            "body{font-family:ui-sans-serif,system-ui,sans-serif;margin:2rem;line-height:1.45;color:#1a1a1a;}",
            "h1,h2{margin-top:1.6rem;} table{border-collapse:collapse;width:100%;margin:0.8rem 0;}",
            "th,td{border:1px solid #ccc;padding:0.4rem 0.6rem;text-align:left;vertical-align:top;}",
            "th{background:#f4f4f4;} .status-runnable{color:#0a7;} .status-blocked{color:#a20;}",
            ".status-pending_data{color:#a60;} .status-completed{color:#06a;}",
            ".note{color:#555;font-size:0.92rem;} .banner{background:#fff8e6;border:1px solid #e6d8a8;padding:0.8rem;}",
            "</style></head><body>",
            "<h1>Research Validation Report</h1>",
            '<p class="banner"><strong>Honesty rule:</strong> this dashboard never fabricates '
            "scores, p-values, CIs, or publication tables. Missing evidence → "
            "<code>insufficient_data</code> / blocked — no numeric claims.</p>",
            f"<p>Experiments loaded: {len(experiments)}. "
            f"Runnable: {len(runnable)}. Blocked: {len(blocked)}. "
            f"Pending: {len(pending)}. Completed: {len(completed)}.</p>",
        ]

        parts.append("<h2>Evidence registry</h2>")
        parts.append("<table><tr><th>ID</th><th>Title</th><th>Status</th><th>Unlocks</th><th>Description</th></tr>")
        for node in evidence:
            parts.append(
                "<tr>"
                f"<td>{_esc(node.id)}</td>"
                f"<td>{_esc(node.title)}</td>"
                f"<td class='status-{_esc(node.status)}'>{_esc(node.status)}</td>"
                f"<td>{_esc(', '.join(node.unlocks))}</td>"
                f"<td>{_esc(node.description)}</td>"
                "</tr>"
            )
        parts.append("</table>")

        def _section(title: str, items: list) -> None:
            parts.append(f"<h2>{_esc(title)}</h2>")
            if not items:
                parts.append("<p class='note'>(none)</p>")
                return
            parts.append(
                "<table><tr><th>ID</th><th>Title</th><th>Status</th>"
                "<th>Missing evidence</th><th>Publication ready</th><th>Notes</th></tr>"
            )
            for exp in items:
                st = statuses[exp.id]
                missing = (
                    [f"node:{n}" for n in st.missing_evidence_nodes]
                    + [f"data:{d}" for d in st.missing_datasets]
                    + [f"run:{r}" for r in st.missing_benchmark_runs]
                    + [f"ann:{a}" for a in st.missing_human_annotations]
                    + [f"base:{b}" for b in st.missing_baselines]
                )
                parts.append(
                    "<tr>"
                    f"<td>{_esc(exp.id)}</td>"
                    f"<td>{_esc(exp.title)}</td>"
                    f"<td class='status-{_esc(st.status)}'>{_esc(st.status)}</td>"
                    f"<td>{_esc('; '.join(missing) if missing else '—')}</td>"
                    f"<td>{'yes' if st.publication_ready else 'no'}</td>"
                    f"<td class='note'>{_esc('; '.join(st.notes))}</td>"
                    "</tr>"
                )
            parts.append("</table>")

        _section("Completed / runnable (limited claims)", completed + runnable)
        _section("Blocked experiments", blocked)
        _section("Pending datasets / runs", pending)

        parts.extend(
            [
                "<h2>Statistical readiness</h2>",
                "<p class='note'>Confirmatory statistics require caller-provided pilot arrays "
                "and adequate <code>n</code>. This dashboard does not invent p-values. "
                "Use <code>githubbench research power --pilot-json …</code> when pilots exist.</p>",
                "<h2>Publication readiness</h2>",
                "<p class='note'>Publication tables/figures are emitted only from real evaluation "
                "aggregates via <code>githubbench research publish</code>. Empty CSV/TeX when "
                "no rows match.</p>",
                "<h2>Pending datasets (from requires)</h2>",
            ]
        )
        pending_ds = sorted(
            {
                d
                for e in experiments
                for d in statuses[e.id].missing_datasets
            }
        )
        if pending_ds:
            parts.append("<ul>")
            parts.extend(f"<li>{_esc(d)}</li>" for d in pending_ds)
            parts.append("</ul>")
        else:
            parts.append("<p class='note'>No missing dataset names flagged (or only runnable demos).</p>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def write(self, out_path: Path | str) -> Path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.build_html(), encoding="utf-8")
        return path
