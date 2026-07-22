"""MemorizationReportGenerator — JSON, Markdown, HTML dashboard."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from githubbench_delta.memorization.charts import figures_as_div_html, write_all_charts
from githubbench_delta.memorization.engine import MemorizationEngine
from githubbench_delta.memorization.models import MemorizationReport


def default_report_dir(base: Path | None = None) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = Path(base or "results/memorization/reports")
    return root / stamp


class MemorizationReportGenerator:
    """Write memorization_report.json, capability_breakdown.md, dashboard HTML."""

    def __init__(self, engine: MemorizationEngine | None = None) -> None:
        self.engine = engine or MemorizationEngine()

    def generate(
        self,
        experiment_ids: list[str],
        output_dir: Path | str | None = None,
        *,
        formats: set[str] | None = None,
        twins_path: Path | str | None = None,
        report: MemorizationReport | None = None,
    ) -> MemorizationReport:
        out = Path(output_dir) if output_dir else default_report_dir()
        out.mkdir(parents=True, exist_ok=True)
        fmts = formats or {"json", "markdown", "html"}
        analysis = report or self.engine.analyze(experiment_ids, twins_path=twins_path)
        artifacts: list[str] = []

        if "json" in fmts:
            path = out / "memorization_report.json"
            path.write_text(
                json.dumps(analysis.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )
            artifacts.append(path.name)

        if "markdown" in fmts:
            path = out / "capability_breakdown.md"
            path.write_text(self._render_markdown(analysis), encoding="utf-8")
            artifacts.append(path.name)

        if "html" in fmts:
            charts_dir = out / "charts"
            written = write_all_charts(analysis, charts_dir)
            artifacts.extend(f"charts/{p.name}" for p in written.values())
            dash = out / "memorization_dashboard.html"
            dash.write_text(self._render_dashboard(analysis), encoding="utf-8")
            artifacts.append(dash.name)

        analysis.output_dir = str(out)
        analysis.artifacts = artifacts
        return analysis

    def _render_markdown(self, report: MemorizationReport) -> str:
        lines = [
            "# Capability Breakdown (MDS)",
            "",
            "Memorization Discounted Scoring decomposes observed performance as "
            "**S_obs = G + L** (generalization + memorization lift).",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "|-------|------:|",
            f"| Mode | {report.mode} |",
            f"| Experiments | {', '.join(report.experiment_ids) or '—'} |",
            f"| Agents | {len(report.breakdowns)} |",
            f"| Generated | {report.generated_at.isoformat()} |",
            "",
            "## Per-agent capability",
            "",
            "| Agent | S_obs | G | L | S_disc | Mode | N |",
            "|-------|------:|--:|--:|-------:|------|--:|",
        ]
        for b in report.breakdowns:
            lines.append(
                f"| {b.agent_id} | {b.observed_score:.3f} | {b.generalization:.3f} | "
                f"{b.memorization_lift:.3f} | {b.discounted_score:.3f} | "
                f"{b.mode} | {b.n_tasks} |"
            )
        lines.append("")

        if report.posteriors:
            lines.extend(
                [
                    "## Posterior lift intervals",
                    "",
                    "| Agent | Mean L | Lower | Upper | Level |",
                    "|-------|-------:|------:|------:|------:|",
                ]
            )
            for p in report.posteriors:
                lines.append(
                    f"| {p.agent_id} | {p.mean:.3f} | {p.lower:.3f} | "
                    f"{p.upper:.3f} | {p.level:.2f} |"
                )
            lines.append("")

        if report.notes:
            lines.extend(["## Notes", ""])
            for n in report.notes:
                lines.append(f"- {n}")
            lines.append("")

        lines.extend(["## Assumptions", ""])
        for a in report.assumptions:
            lines.append(f"- {a}")
        lines.append("")

        lines.extend(
            [
                "## Limitations",
                "",
                "- Twin absence forces proxy mode with reduced confidence.",
                "- Beta–Binomial lift model is a convenience conjugate, not a causal MDS.",
                "- Prompt paraphrase twins may still share surface cues with parents.",
                "- Does not modify benchmark leaderboards or metric registry entries.",
                "",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_dashboard(self, report: MemorizationReport) -> str:
        divs = figures_as_div_html(report)
        rows = "".join(
            f"<tr><td>{b.agent_id}</td><td>{b.observed_score:.3f}</td>"
            f"<td>{b.generalization:.3f}</td><td>{b.memorization_lift:.3f}</td>"
            f"<td>{b.discounted_score:.3f}</td></tr>"
            for b in report.breakdowns
        )
        empty = "<tr><td colspan='5'>No agents</td></tr>"
        body = rows or empty
        exp = ", ".join(report.experiment_ids) or "—"
        return "\n".join(
            [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "<head>",
                '  <meta charset="utf-8"/>',
                '  <meta name="viewport" content="width=device-width, initial-scale=1"/>',
                "  <title>MDS Dashboard</title>",
                '  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>',
                "  <style>",
                "    :root { --bg:#f3f6f4; --ink:#1c2b24; --accent:#1f6f5b; --card:#fff; }",
                "    body { margin:0; font-family:'Source Serif 4','Georgia',serif;",
                "      background:linear-gradient(165deg,#dfece6 0%,var(--bg) 45%,#eef3ea 100%);",
                "      color:var(--ink); }",
                "    header { padding:2rem; border-bottom:1px solid #c5d6cd; }",
                "    header h1 { margin:0; font-size:1.8rem; color:var(--accent); }",
                "    main { display:grid; gap:1.25rem; padding:1.25rem 2rem 2.5rem; }",
                "    .chart { background:var(--card); border:1px solid #cfdcd4; padding:0.5rem; }",
                "    table { border-collapse:collapse; background:var(--card);",
                "      border:1px solid #cfdcd4; }",
                "    th,td { padding:0.5rem 0.75rem; border-bottom:1px solid #e3ebe6; }",
                "    th { background:#e7f0eb; text-align:left; }",
                "    @media (min-width:960px) {",
                "      main { grid-template-columns:1fr 1fr; }",
                "      .full { grid-column:1 / -1; }",
                "    }",
                "  </style>",
                "</head>",
                "<body>",
                "  <header>",
                "    <h1>Memorization Discounted Scoring</h1>",
                f"    <p>Post-processing decomposition S_obs = G + L (mode: {report.mode}).</p>",
                f"    <p>Experiments: {exp}</p>",
                "  </header>",
                "  <main>",
                '    <div class="full"><table>',
                "      <thead><tr><th>Agent</th><th>S_obs</th><th>G</th>"
                "<th>L</th><th>S_disc</th></tr></thead>",
                f"      <tbody>{body}</tbody>",
                "    </table></div>",
                f'    <div class="chart full">{divs.get("capability_vs_memorization", "")}</div>',
                f'    <div class="chart">{divs.get("twin_agreement", "")}</div>',
                f'    <div class="chart">{divs.get("lift_distribution", "")}</div>',
                f'    <div class="chart full">{divs.get("posterior_ci", "")}</div>',
                "  </main>",
                "</body>",
                "</html>",
                "",
            ]
        )
