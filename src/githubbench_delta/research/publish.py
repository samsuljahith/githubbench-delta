"""Publication exporters — only from real evaluation aggregate rows."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from githubbench_delta.research.artifacts import resolve_globs
from githubbench_delta.research.models import ResearchExperiment


def _load_aggregate_rows(paths: list[str], *, cwd: Path) -> list[dict[str, Any]]:
    """Extract agent/task aggregate rows from evaluation_results.json-like files.

    Never invent scores: if structure unknown or empty, return [].
    """

    rows: list[dict[str, Any]] = []
    for rel in paths:
        path = cwd / rel if not Path(rel).is_absolute() else Path(rel)
        if not path.is_file() or path.suffix != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rows.extend(_rows_from_payload(data, source=str(rel)))
    return rows


def _rows_from_payload(data: Any, *, source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(data, dict):
        # Common shapes: {"results": [...]}, {"agents": {...}}, flat list under known keys
        if "results" in data and isinstance(data["results"], list):
            for item in data["results"]:
                if isinstance(item, dict):
                    rows.append(_normalize_row(item, source=source))
        elif "agent_scores" in data and isinstance(data["agent_scores"], dict):
            for agent_id, score in data["agent_scores"].items():
                if isinstance(score, (int, float)):
                    rows.append(
                        {
                            "source": source,
                            "agent_id": str(agent_id),
                            "metric": "aggregate_score",
                            "value": float(score),
                        }
                    )
        elif "summary" in data and isinstance(data["summary"], dict):
            for key, val in data["summary"].items():
                if isinstance(val, (int, float)):
                    rows.append(
                        {
                            "source": source,
                            "agent_id": "",
                            "metric": str(key),
                            "value": float(val),
                        }
                    )
        # Nested per-agent metrics
        for key in ("by_agent", "agents"):
            block = data.get(key)
            if isinstance(block, dict):
                for agent_id, metrics in block.items():
                    if isinstance(metrics, dict):
                        for mk, mv in metrics.items():
                            if isinstance(mv, (int, float)):
                                rows.append(
                                    {
                                        "source": source,
                                        "agent_id": str(agent_id),
                                        "metric": str(mk),
                                        "value": float(mv),
                                    }
                                )
                    elif isinstance(metrics, (int, float)):
                        rows.append(
                            {
                                "source": source,
                                "agent_id": str(agent_id),
                                "metric": "score",
                                "value": float(metrics),
                            }
                        )
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                rows.append(_normalize_row(item, source=source))
    return [r for r in rows if r.get("value") is not None]


def _normalize_row(item: dict[str, Any], *, source: str) -> dict[str, Any]:
    agent = item.get("agent_id") or item.get("agent") or item.get("model") or ""
    metric = item.get("metric") or item.get("metric_name") or "score"
    value = item.get("value")
    if value is None:
        value = item.get("score")
    if value is None:
        value = item.get("mean")
    out: dict[str, Any] = {
        "source": source,
        "agent_id": str(agent),
        "metric": str(metric),
        "value": float(value) if isinstance(value, (int, float)) else None,
    }
    if "task_id" in item:
        out["task_id"] = item["task_id"]
    return out


class PublicationExporter:
    """Export publication_tables.csv/.tex and publication_figures.json from real rows only."""

    def export(
        self,
        experiment: ResearchExperiment,
        dest: Path | str,
        *,
        source_root: Path | None = None,
    ) -> dict[str, Path]:
        out = Path(dest)
        out.mkdir(parents=True, exist_ok=True)
        cwd = source_root or Path.cwd()
        matched = resolve_globs(experiment.artifact_globs, root=cwd)
        rows = _load_aggregate_rows(matched, cwd=cwd)

        csv_path = out / "publication_tables.csv"
        tex_path = out / "publication_tables.tex"
        fig_path = out / "publication_figures.json"

        fieldnames = ["source", "agent_id", "metric", "value", "task_id"]
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        tex_path.write_text(_rows_to_latex(rows, experiment_id=experiment.id), encoding="utf-8")

        figures: list[dict[str, Any]] = []
        if rows:
            figures.append(
                {
                    "type": "table_ref",
                    "title": f"{experiment.id} publication table",
                    "n_rows": len(rows),
                    "note": "Derived from matched evaluation aggregates only",
                }
            )
        fig_path.write_text(json.dumps(figures, indent=2), encoding="utf-8")

        return {
            "csv": csv_path,
            "tex": tex_path,
            "figures": fig_path,
            "n_rows": len(rows),  # type: ignore[dict-item]
        }


def _rows_to_latex(rows: list[dict[str, Any]], *, experiment_id: str) -> str:
    lines = [
        "% Auto-generated by githubbench research publish",
        f"% experiment: {experiment_id}",
        "% Empty table if no real aggregate rows were found (no fabricated numbers).",
        r"\begin{tabular}{lllr}",
        r"\hline",
        r"source & agent\_id & metric & value \\",
        r"\hline",
    ]
    if not rows:
        lines.append(r"\multicolumn{4}{c}{(no real aggregate rows)} \\")
    else:
        for row in rows:
            src = _tex_escape(str(row.get("source", "")))
            agent = _tex_escape(str(row.get("agent_id", "")))
            metric = _tex_escape(str(row.get("metric", "")))
            val = row.get("value")
            val_s = f"{val:.6g}" if isinstance(val, float) else ""
            lines.append(f"{src} & {agent} & {metric} & {val_s} \\\\")
    lines.extend([r"\hline", r"\end{tabular}", ""])
    return "\n".join(lines)


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )
