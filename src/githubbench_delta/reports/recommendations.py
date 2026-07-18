"""Deterministic recommendation rules (no LLM)."""

from __future__ import annotations

from githubbench_delta.reports.models import DiffResult, ReportDocument

# Fixed thresholds for publication guidance.
OVERALL_LOW = 0.55
GROUP_LOW = 0.50
CONFIDENCE_LOW = 0.60
FAILURE_RATE_HIGH = 0.25
COST_HIGH = 0.05
LATENCY_HIGH_MS = 5_000.0
WARNING_DENSITY_HIGH = 0.3
REGRESSION_ABS = 0.05


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def generate_recommendations(doc: ReportDocument) -> list[str]:
    """Return ordered, stable recommendation strings from document aggregates."""

    recs: list[str] = []
    evals = doc.evaluations
    n = len(evals)
    if n == 0:
        recs.append("No evaluation rows found; verify experiment artifacts before publishing.")
        return recs

    overalls = [float(e["overall_score"]) for e in evals if e.get("overall_score") is not None]
    mean_overall = _mean(overalls)
    if mean_overall is not None and mean_overall < OVERALL_LOW:
        recs.append(
            f"Overall mean score is {mean_overall:.3f} (below {OVERALL_LOW}); "
            "prioritize correctness and task resolution improvements."
        )

    # Group scores from leaderboard / category
    group_acc: dict[str, list[float]] = {}
    for row in doc.leaderboard:
        for g, s in (row.get("group_scores") or {}).items():
            group_acc.setdefault(g, []).append(float(s))
    for g, vals in sorted(group_acc.items()):
        m = _mean(vals)
        if m is not None and m < GROUP_LOW:
            recs.append(
                f"Group '{g}' mean is {m:.3f} (below {GROUP_LOW}); "
                f"investigate {g}-related metrics and failure modes."
            )

    confs = [float(e["confidence_score"]) for e in evals if e.get("confidence_score") is not None]
    mean_conf = _mean(confs)
    if mean_conf is not None and mean_conf < CONFIDENCE_LOW:
        recs.append(
            f"Mean confidence is {mean_conf:.3f} (below {CONFIDENCE_LOW}); "
            "review calibration and evidence coverage."
        )

    successes = [e for e in evals if e.get("success") is True]
    fail_rate = 1.0 - (len(successes) / n)
    if fail_rate >= FAILURE_RATE_HIGH:
        recs.append(
            f"Failure rate is {fail_rate:.1%} (at/above {FAILURE_RATE_HIGH:.0%}); "
            "inspect failed units and safe_failure / recovery metrics."
        )

    costs = [float(e["cost_usd"]) for e in evals if e.get("cost_usd") is not None]
    mean_cost = _mean(costs)
    if mean_cost is not None and mean_cost >= COST_HIGH:
        recs.append(
            f"Mean cost is ${mean_cost:.4f} (at/above ${COST_HIGH:.2f}); "
            "consider tool economy and cost-normalized capability."
        )

    lats = [float(e["latency_ms"]) for e in evals if e.get("latency_ms") is not None]
    mean_lat = _mean(lats)
    if mean_lat is not None and mean_lat >= LATENCY_HIGH_MS:
        recs.append(
            f"Mean latency is {mean_lat:.0f} ms (at/above {LATENCY_HIGH_MS:.0f} ms); "
            "reduce unnecessary tool calls and long trajectories."
        )

    if doc.warnings:
        density = len(doc.warnings) / max(n, 1)
        if density >= WARNING_DENSITY_HIGH:
            recs.append(
                f"Warning density is high ({len(doc.warnings)} warnings / {n} evals); "
                "triage metric warnings before publication."
            )

    # Metric importance: call out weakest high-importance metrics
    weak = [
        m for m in doc.metric_stats if m.get("n", 0) > 0 and float(m.get("mean", 1.0)) < GROUP_LOW
    ]
    weak.sort(key=lambda m: float(m.get("importance", 0.0)), reverse=True)
    for m in weak[:3]:
        recs.append(
            f"Metric '{m['metric_id']}' mean is {float(m['mean']):.3f}; "
            "treat as a priority remediation target."
        )

    if doc.diff is not None:
        recs.extend(_recs_from_diff(doc.diff))

    if not recs:
        recs.append("Scores are within configured thresholds; no critical remediation flags.")
    return recs


def _recs_from_diff(diff: DiffResult) -> list[str]:
    out: list[str] = []
    regs = [d for d in diff.metric_deltas if d.is_regression]
    regs += [d for d in diff.task_deltas if d.is_regression]
    if diff.overall_delta and diff.overall_delta.is_regression:
        out.append(
            f"Overall score regressed vs {diff.baseline_id} (delta={diff.overall_delta.delta})."
        )
    if diff.cost_delta and diff.cost_delta.is_regression:
        out.append("Cost regressed versus baseline; review model/tool usage.")
    if diff.latency_delta and diff.latency_delta.is_regression:
        out.append("Latency regressed versus baseline; profile trajectory length.")
    if regs:
        keys = ", ".join(d.key for d in regs[:5])
        out.append(f"Detected regressions in: {keys}.")
    return out


def collect_warnings(doc: ReportDocument, traj_notes: list[str] | None = None) -> list[str]:
    """Aggregate warning strings from evaluations metadata and trajectory notes."""

    warnings: list[str] = []
    run = (doc.experiment_detail or {}).get("run") or {}
    for fu in run.get("failed_units") or []:
        if isinstance(fu, dict):
            warnings.append(f"Failed unit {fu.get('unit_key')}: {fu.get('error') or 'unknown'}")
        else:
            warnings.append(f"Failed unit: {fu}")
    for note in traj_notes or []:
        warnings.append(note)
    # Low-score unsuccessful trials
    for e in doc.evaluations:
        if e.get("success") is False:
            warnings.append(
                f"Unsuccessful trial {e.get('unit_key')} (score={e.get('overall_score')})"
            )
        elif e.get("overall_score") is not None and float(e["overall_score"]) < 0.3:
            warnings.append(f"Very low score on {e.get('unit_key')}: {e.get('overall_score')}")
    return warnings
