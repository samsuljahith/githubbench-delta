"""Local-vs-Hosted Parity evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import AgentResult, MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import (
    build_result,
    evidence_confidence,
    skip_result,
)


def _role(result: AgentResult, run_metadata: dict) -> str | None:
    """Return 'local' or 'hosted' from metadata; fall back to agent_id labels."""

    meta = {**run_metadata, **result.metadata}
    role = meta.get("deployment_role") or meta.get("role")
    if role in {"local", "hosted"}:
        return str(role)
    # Label-only fallback: known local agent id string vs others
    aid = str(result.agent_id)
    if aid == "minicpm":
        return "local"
    if aid in {"claude", "codex"}:
        return "hosted"
    return None


def _capability(result: AgentResult) -> float:
    if result.success and (result.output.content or "").strip():
        return 1.0
    if result.success:
        return 0.7
    if (result.output.content or "").strip():
        return 0.3
    return 0.0


class LocalVsHostedParityMetric(BaseMetric):
    """Parity between local and hosted peer capability proxies."""

    id: str = "local_vs_hosted_parity"
    display_name: str = "Local-vs-Hosted Parity"
    requires_peer_runs: bool = True
    group: MetricGroup = MetricGroup.EFFICIENCY

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        tolerance = float(self._threshold("parity_tolerance", 0.2))
        cohort = [ctx.agent_result, *ctx.peer_results]
        local_scores: list[float] = []
        hosted_scores: list[float] = []
        for r in cohort:
            role = _role(r, ctx.run_metadata)
            cap = _capability(r)
            if role == "local":
                local_scores.append(cap)
            elif role == "hosted":
                hosted_scores.append(cap)

        if not local_scores or not hosted_scores:
            return skip_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                reason="Need both local and hosted peers (deployment_role or agent labels)",
                weight=self.config.weight,
                metric_version=self.config.version,
                strict_zero=self.config.strict,
            )

        local_mean = sum(local_scores) / len(local_scores)
        hosted_mean = sum(hosted_scores) / len(hosted_scores)
        delta = abs(local_mean - hosted_mean)
        # Perfect parity inside tolerance; otherwise 1 - delta.
        raw = 1.0 if delta <= tolerance else max(0.0, 1.0 - delta)

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(local_scores) + len(hosted_scores),
            expected_items=2,
        )
        improvements = []
        if delta > tolerance:
            improvements.append("Reduce capability gap between local and hosted deployments")
        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"local_mean={local_mean:.2f}, hosted_mean={hosted_mean:.2f}, "
                f"delta={delta:.2f}, tolerance={tolerance:.2f}"
            ),
            evidence=[
                {
                    "local_scores": local_scores,
                    "hosted_scores": hosted_scores,
                    "delta": delta,
                }
            ],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={
                "local_mean": local_mean,
                "hosted_mean": hosted_mean,
                "delta": delta,
                "tolerance": tolerance,
            },
        )
