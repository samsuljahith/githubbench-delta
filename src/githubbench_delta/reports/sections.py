"""SectionRegistry: map report types to ordered section builders."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.reports.models import (
    ReportDocument,
    ReportType,
    SectionId,
    SectionPayload,
)

SectionBuilder = Callable[[ReportDocument, ExperimentRepository | None], SectionPayload]


def _table(columns: list[str], rows: list[dict[str, Any]], name: str = "") -> dict[str, Any]:
    return {"name": name, "columns": columns, "rows": rows}


def section_experiment_metadata(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    exp = (doc.experiment_detail or {}).get("experiment") or {}
    run = (doc.experiment_detail or {}).get("run") or {}
    rows = [
        {
            "field": "experiment_id",
            "value": exp.get("experiment_id") or (doc.experiment_ids[:1] or [""])[0],
        },
        {"field": "name", "value": exp.get("name", "")},
        {"field": "status", "value": exp.get("status", "")},
        {"field": "run_id", "value": run.get("run_id", "")},
        {"field": "created_at", "value": exp.get("created_at", "")},
        {"field": "updated_at", "value": exp.get("updated_at", "")},
    ]
    return SectionPayload(
        id=SectionId.EXPERIMENT_METADATA.value,
        title="Experiment Metadata",
        summary="Identifiers and lifecycle timestamps for the evaluated experiment.",
        tables=[_table(["field", "value"], rows, "metadata")],
        stats={"experiment_ids": doc.experiment_ids},
    )


def section_dataset_summary(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    exp = (doc.experiment_detail or {}).get("experiment") or {}
    task_ids = exp.get("task_ids") or doc.metadata.get("task_ids") or []
    cats = Counter(t.get("category") or "unknown" for t in doc.tasks)
    rows = [
        {
            "field": "dataset_path",
            "value": exp.get("dataset_path") or doc.metadata.get("dataset_path"),
        },
        {"field": "task_count", "value": len(task_ids)},
        {"field": "dataset_version", "value": (doc.appendix or {}).get("dataset_version")},
        {"field": "categories", "value": dict(cats)},
    ]
    return SectionPayload(
        id=SectionId.DATASET_SUMMARY.value,
        title="Dataset Summary",
        summary="Task corpus coverage for this experiment.",
        tables=[_table(["field", "value"], rows, "dataset")],
        stats={"category_counts": dict(cats), "n_tasks": len(task_ids)},
    )


def section_agent_configuration(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    exp = (doc.experiment_detail or {}).get("experiment") or {}
    agents = exp.get("agent_ids") or doc.metadata.get("agent_ids") or []
    rows = [{"agent_id": a} for a in agents]
    snap = exp.get("config_snapshot") or {}
    return SectionPayload(
        id=SectionId.AGENT_CONFIGURATION.value,
        title="Agent Configuration",
        summary="Agents included in the evaluation.",
        tables=[_table(["agent_id"], rows, "agents")],
        stats={"config_snapshot_keys": list(snap.keys()) if isinstance(snap, dict) else []},
        notes=["Full agent config is taken from experiment config_snapshot when present."],
    )


def section_benchmark_configuration(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    exp = (doc.experiment_detail or {}).get("experiment") or {}
    rows = [
        {"field": "seed", "value": exp.get("seed")},
        {"field": "trial_count", "value": exp.get("trial_count")},
        {"field": "max_concurrency", "value": exp.get("max_concurrency")},
        {"field": "resume", "value": exp.get("resume")},
        {"field": "use_cache", "value": exp.get("use_cache")},
    ]
    return SectionPayload(
        id=SectionId.BENCHMARK_CONFIGURATION.value,
        title="Benchmark Configuration",
        summary="Run controls that affect reproducibility.",
        tables=[_table(["field", "value"], rows, "benchmark")],
    )


def section_evaluation_methodology(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    metrics = (doc.appendix or {}).get("methodology_metrics") or [
        {"metric_id": mid, "group": ""} for mid in METHODOLOGY_METRIC_IDS
    ]
    return SectionPayload(
        id=SectionId.EVALUATION_METHODOLOGY.value,
        title="Evaluation Methodology",
        summary=(
            "Scores are produced by 18 deterministic methodology metrics across "
            "correctness, trajectory, safety, grounding, reliability, and efficiency. "
            "No LLM judge is used."
        ),
        tables=[_table(["metric_id", "group"], metrics, "metrics")],
        chart_ids=[],
    )


def section_overall_results(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    rows = doc.leaderboard
    cols = [
        "agent_id",
        "overall_score",
        "confidence",
        "cost_usd",
        "latency_ms",
        "success_rate",
        "n_trials",
    ]
    return SectionPayload(
        id=SectionId.OVERALL_RESULTS.value,
        title="Overall Results",
        summary="Per-agent aggregate scores and operational means.",
        tables=[_table(cols, rows, "leaderboard")],
        chart_ids=["radar", "bars"],
        stats=doc.overview,
    )


def section_metric_breakdown(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    return SectionPayload(
        id=SectionId.METRIC_BREAKDOWN.value,
        title="18 Metric Breakdown",
        summary="Distribution statistics across the methodology metric suite.",
        tables=[
            _table(
                ["metric_id", "mean", "std", "min", "max", "n", "importance"],
                doc.metric_stats,
                "metric_stats",
            )
        ],
        chart_ids=["histogram", "importance", "corr_heatmap"],
    )


def section_category_scores(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    rows = [{"category": k, "mean_score": v} for k, v in sorted(doc.category_scores.items())]
    return SectionPayload(
        id=SectionId.CATEGORY_SCORES.value,
        title="Per-category Scores",
        summary="Mean overall score by task category.",
        tables=[_table(["category", "mean_score"], rows, "categories")],
        stats=dict(doc.category_scores),
    )


def section_task_performance(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    cols = [
        "task_id",
        "category",
        "difficulty",
        "language",
        "mean_score",
        "n_evals",
        "agents",
    ]
    return SectionPayload(
        id=SectionId.TASK_PERFORMANCE.value,
        title="Task Performance",
        summary="Per-task mean scores and coverage.",
        tables=[_table(cols, doc.tasks, "tasks")],
    )


def section_failure_analysis(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    failures = [
        e
        for e in doc.evaluations
        if e.get("success") is False
        or (e.get("overall_score") is not None and float(e["overall_score"]) < 0.4)
    ]
    cols = ["unit_key", "task_id", "agent_id", "overall_score", "success"]
    return SectionPayload(
        id=SectionId.FAILURE_ANALYSIS.value,
        title="Failure Analysis",
        summary="Unsuccessful or low-scoring evaluation units.",
        tables=[_table(cols, failures, "failures")],
        stats={"n_failures": len(failures)},
    )


def _traj_tool_stats(
    doc: ReportDocument, repo: ExperimentRepository | None
) -> tuple[dict[str, Any], Counter[str], list[str]]:
    stats: dict[str, Any] = {
        "n_trajectories": 0,
        "mean_steps": 0.0,
        "error_steps": 0,
        "warning_steps": 0,
    }
    tools: Counter[str] = Counter()
    notes: list[str] = []
    if repo is None or not doc.experiment_ids:
        return stats, tools, notes
    step_counts: list[int] = []
    for eid in doc.experiment_ids:
        items = repo.list_trajectories(eid)
        stats["n_trajectories"] += len(items)
        for item in items:
            step_counts.append(item.step_count)
            detail = repo.get_trajectory(eid, item.unit_key)
            if not detail:
                continue
            for w in detail.warnings or []:
                notes.append(f"{item.unit_key}: {w}")
            for step in detail.steps or []:
                kind = (step.get("kind") or "").lower()
                if kind == "error":
                    stats["error_steps"] += 1
                if kind == "warning":
                    stats["warning_steps"] += 1
                tc = step.get("tool_call") or {}
                name = tc.get("name")
                if name:
                    tools[str(name)] += 1
            for tc in detail.tool_calls or []:
                name = tc.get("name")
                if name:
                    tools[str(name)] += 1
    if step_counts:
        stats["mean_steps"] = sum(step_counts) / len(step_counts)
    return stats, tools, notes


def section_trajectory_summary(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    stats, _tools, notes = _traj_tool_stats(doc, repo)
    return SectionPayload(
        id=SectionId.TRAJECTORY_SUMMARY.value,
        title="Trajectory Summary",
        summary="Aggregate trajectory length and error/warning step counts.",
        stats=stats,
        notes=notes[:20],
        tables=[
            _table(
                ["metric", "value"],
                [{"metric": k, "value": v} for k, v in stats.items()],
                "trajectory",
            )
        ],
    )


def section_tool_usage(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    _stats, tools, _notes = _traj_tool_stats(doc, repo)
    rows = [{"tool": k, "count": v} for k, v in tools.most_common()]
    return SectionPayload(
        id=SectionId.TOOL_USAGE_SUMMARY.value,
        title="Tool Usage Summary",
        summary="Tool call frequencies from stored trajectories.",
        tables=[_table(["tool", "count"], rows, "tools")],
        stats={"unique_tools": len(tools)},
    )


def section_latency(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    vals = [float(e["latency_ms"]) for e in doc.evaluations if e.get("latency_ms") is not None]
    mean = sum(vals) / len(vals) if vals else None
    by_agent: dict[str, list[float]] = defaultdict(list)
    for e in doc.evaluations:
        if e.get("latency_ms") is not None:
            by_agent[e["agent_id"]].append(float(e["latency_ms"]))
    rows = [
        {"agent_id": a, "mean_latency_ms": sum(v) / len(v)} for a, v in sorted(by_agent.items())
    ]
    return SectionPayload(
        id=SectionId.LATENCY.value,
        title="Latency",
        summary="Mean latency from agent result metrics.",
        tables=[_table(["agent_id", "mean_latency_ms"], rows, "latency")],
        stats={"mean_latency_ms": mean, "n": len(vals)},
    )


def section_cost(doc: ReportDocument, repo: ExperimentRepository | None = None) -> SectionPayload:
    vals = [float(e["cost_usd"]) for e in doc.evaluations if e.get("cost_usd") is not None]
    mean = sum(vals) / len(vals) if vals else None
    by_agent: dict[str, list[float]] = defaultdict(list)
    for e in doc.evaluations:
        if e.get("cost_usd") is not None:
            by_agent[e["agent_id"]].append(float(e["cost_usd"]))
    rows = [{"agent_id": a, "mean_cost_usd": sum(v) / len(v)} for a, v in sorted(by_agent.items())]
    return SectionPayload(
        id=SectionId.COST.value,
        title="Cost",
        summary="Mean estimated cost from agent result metrics.",
        tables=[_table(["agent_id", "mean_cost_usd"], rows, "cost")],
        stats={"mean_cost_usd": mean, "n": len(vals)},
    )


def section_confidence(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    vals = [
        float(e["confidence_score"])
        for e in doc.evaluations
        if e.get("confidence_score") is not None
    ]
    mean = sum(vals) / len(vals) if vals else None
    return SectionPayload(
        id=SectionId.CONFIDENCE.value,
        title="Confidence",
        summary="Mean evaluator confidence across trials.",
        stats={"mean_confidence": mean, "n": len(vals)},
        tables=[
            _table(
                ["metric", "value"],
                [
                    {"metric": "mean_confidence", "value": mean},
                    {"metric": "n", "value": len(vals)},
                ],
                "confidence",
            )
        ],
    )


def section_warnings(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    rows = [{"warning": w} for w in doc.warnings]
    return SectionPayload(
        id=SectionId.WARNINGS.value,
        title="Warnings",
        summary="Aggregated warnings from runs, trajectories, and low scores.",
        tables=[_table(["warning"], rows, "warnings")],
        stats={"n_warnings": len(doc.warnings)},
    )


def section_recommendations(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    rows = [{"recommendation": r} for r in doc.recommendations]
    return SectionPayload(
        id=SectionId.RECOMMENDATIONS.value,
        title="Recommendations",
        summary="Deterministic remediation guidance from metric thresholds.",
        tables=[_table(["recommendation"], rows, "recommendations")],
    )


def section_appendix(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    appendix = doc.appendix or {}
    rows = [{"key": k, "value": v} for k, v in appendix.items() if k != "methodology_metrics"]
    return SectionPayload(
        id=SectionId.APPENDIX.value,
        title="Appendix",
        summary="Versions, artifact paths, and methodology catalog.",
        tables=[
            _table(["key", "value"], rows, "appendix"),
            _table(
                ["metric_id", "group"],
                appendix.get("methodology_metrics") or [],
                "methodology",
            ),
        ],
        stats=appendix,
    )


def section_diff(doc: ReportDocument, repo: ExperimentRepository | None = None) -> SectionPayload:
    diff = doc.diff
    if diff is None:
        return SectionPayload(
            id=SectionId.DIFF.value,
            title="Comparison",
            summary="No comparison context provided.",
            notes=["Provide baseline and candidate experiment ids."],
        )
    rows = []
    if diff.overall_delta:
        rows.append(diff.overall_delta.model_dump())
    rows.extend(d.model_dump() for d in diff.group_deltas)
    return SectionPayload(
        id=SectionId.DIFF.value,
        title="Comparison Diff",
        summary=f"{diff.baseline_id} vs {diff.candidate_id} ({diff.compare_kind})",
        tables=[
            _table(
                ["key", "baseline", "candidate", "delta", "relative", "is_regression"],
                rows,
                "diff",
            )
        ],
        notes=list(diff.notes),
        stats={
            "dataset_version_baseline": diff.dataset_version_baseline,
            "dataset_version_candidate": diff.dataset_version_candidate,
            "prompt_version_baseline": diff.prompt_version_baseline,
            "prompt_version_candidate": diff.prompt_version_candidate,
        },
    )


def section_regressions(
    doc: ReportDocument, repo: ExperimentRepository | None = None
) -> SectionPayload:
    diff = doc.diff
    if diff is None:
        return SectionPayload(
            id=SectionId.REGRESSIONS.value,
            title="Regressions",
            summary="No diff available.",
        )
    regs = [
        d.model_dump()
        for d in (
            list(diff.metric_deltas)
            + list(diff.task_deltas)
            + list(diff.trajectory_deltas)
            + ([diff.cost_delta] if diff.cost_delta else [])
            + ([diff.latency_delta] if diff.latency_delta else [])
            + ([diff.overall_delta] if diff.overall_delta else [])
        )
        if d and d.is_regression
    ]
    return SectionPayload(
        id=SectionId.REGRESSIONS.value,
        title="Regression Highlights",
        summary="Metric, task, cost, latency, and trajectory regressions.",
        tables=[
            _table(
                ["key", "baseline", "candidate", "delta", "relative", "is_regression"],
                regs,
                "regressions",
            )
        ],
        stats={"n_regressions": len(regs)},
    )


SECTION_BUILDERS: dict[str, SectionBuilder] = {
    SectionId.EXPERIMENT_METADATA.value: section_experiment_metadata,
    SectionId.DATASET_SUMMARY.value: section_dataset_summary,
    SectionId.AGENT_CONFIGURATION.value: section_agent_configuration,
    SectionId.BENCHMARK_CONFIGURATION.value: section_benchmark_configuration,
    SectionId.EVALUATION_METHODOLOGY.value: section_evaluation_methodology,
    SectionId.OVERALL_RESULTS.value: section_overall_results,
    SectionId.METRIC_BREAKDOWN.value: section_metric_breakdown,
    SectionId.CATEGORY_SCORES.value: section_category_scores,
    SectionId.TASK_PERFORMANCE.value: section_task_performance,
    SectionId.FAILURE_ANALYSIS.value: section_failure_analysis,
    SectionId.TRAJECTORY_SUMMARY.value: section_trajectory_summary,
    SectionId.TOOL_USAGE_SUMMARY.value: section_tool_usage,
    SectionId.LATENCY.value: section_latency,
    SectionId.COST.value: section_cost,
    SectionId.CONFIDENCE.value: section_confidence,
    SectionId.WARNINGS.value: section_warnings,
    SectionId.RECOMMENDATIONS.value: section_recommendations,
    SectionId.APPENDIX.value: section_appendix,
    SectionId.DIFF.value: section_diff,
    SectionId.REGRESSIONS.value: section_regressions,
}


REPORT_TYPE_SECTIONS: dict[ReportType, list[str]] = {
    ReportType.EXECUTIVE: [
        SectionId.EXPERIMENT_METADATA.value,
        SectionId.OVERALL_RESULTS.value,
        SectionId.RECOMMENDATIONS.value,
        SectionId.WARNINGS.value,
    ],
    ReportType.TECHNICAL: [
        SectionId.EXPERIMENT_METADATA.value,
        SectionId.DATASET_SUMMARY.value,
        SectionId.AGENT_CONFIGURATION.value,
        SectionId.BENCHMARK_CONFIGURATION.value,
        SectionId.EVALUATION_METHODOLOGY.value,
        SectionId.OVERALL_RESULTS.value,
        SectionId.METRIC_BREAKDOWN.value,
        SectionId.CATEGORY_SCORES.value,
        SectionId.TASK_PERFORMANCE.value,
        SectionId.FAILURE_ANALYSIS.value,
        SectionId.TRAJECTORY_SUMMARY.value,
        SectionId.TOOL_USAGE_SUMMARY.value,
        SectionId.LATENCY.value,
        SectionId.COST.value,
        SectionId.CONFIDENCE.value,
        SectionId.WARNINGS.value,
        SectionId.RECOMMENDATIONS.value,
        SectionId.APPENDIX.value,
    ],
    ReportType.EXPERIMENT: [
        SectionId.EXPERIMENT_METADATA.value,
        SectionId.DATASET_SUMMARY.value,
        SectionId.BENCHMARK_CONFIGURATION.value,
        SectionId.OVERALL_RESULTS.value,
        SectionId.TASK_PERFORMANCE.value,
        SectionId.FAILURE_ANALYSIS.value,
        SectionId.RECOMMENDATIONS.value,
        SectionId.APPENDIX.value,
    ],
    ReportType.AGENT_COMPARISON: [
        SectionId.EXPERIMENT_METADATA.value,
        SectionId.AGENT_CONFIGURATION.value,
        SectionId.OVERALL_RESULTS.value,
        SectionId.METRIC_BREAKDOWN.value,
        SectionId.LATENCY.value,
        SectionId.COST.value,
        SectionId.RECOMMENDATIONS.value,
    ],
    ReportType.METRIC: [
        SectionId.EVALUATION_METHODOLOGY.value,
        SectionId.METRIC_BREAKDOWN.value,
        SectionId.CATEGORY_SCORES.value,
        SectionId.CONFIDENCE.value,
        SectionId.RECOMMENDATIONS.value,
        SectionId.APPENDIX.value,
    ],
    ReportType.TASK_ANALYSIS: [
        SectionId.DATASET_SUMMARY.value,
        SectionId.TASK_PERFORMANCE.value,
        SectionId.CATEGORY_SCORES.value,
        SectionId.FAILURE_ANALYSIS.value,
        SectionId.RECOMMENDATIONS.value,
    ],
    ReportType.REGRESSION: [
        SectionId.EXPERIMENT_METADATA.value,
        SectionId.DIFF.value,
        SectionId.REGRESSIONS.value,
        SectionId.OVERALL_RESULTS.value,
        SectionId.RECOMMENDATIONS.value,
        SectionId.WARNINGS.value,
    ],
    ReportType.CI_SUMMARY: [
        SectionId.OVERALL_RESULTS.value,
        SectionId.REGRESSIONS.value,
        SectionId.WARNINGS.value,
        SectionId.RECOMMENDATIONS.value,
    ],
}


class SectionRegistry:
    """Build ordered sections for a report type."""

    def __init__(self, builders: dict[str, SectionBuilder] | None = None) -> None:
        self._builders = builders or SECTION_BUILDERS

    def section_ids_for(self, report_type: ReportType) -> list[str]:
        return list(
            REPORT_TYPE_SECTIONS.get(report_type, REPORT_TYPE_SECTIONS[ReportType.TECHNICAL])
        )

    def build_all(
        self,
        doc: ReportDocument,
        repo: ExperimentRepository | None = None,
    ) -> list[SectionPayload]:
        sections: list[SectionPayload] = []
        for sid in self.section_ids_for(doc.report_type):
            builder = self._builders.get(sid)
            if builder is None:
                continue
            sections.append(builder(doc, repo))
        return sections
