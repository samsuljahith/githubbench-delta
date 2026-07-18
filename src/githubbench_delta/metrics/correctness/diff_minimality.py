"""Diff Minimality evaluator — GitHubBench-Delta methodology."""

from __future__ import annotations

from githubbench_delta.core.models import MetricGroup, MetricResult
from githubbench_delta.metrics.base import BaseMetric, MetricContext
from githubbench_delta.metrics.scoring import build_result, evidence_confidence


class DiffMinimalityMetric(BaseMetric):
    """Prefer minimal sufficient patches relative to configured budgets."""

    id: str = "diff_minimality"
    display_name: str = "Diff Minimality"
    group: MetricGroup = MetricGroup.CORRECTNESS

    def evaluate(self, ctx: MetricContext) -> MetricResult:
        max_files = float(self._threshold("max_changed_files", 20))
        max_lines = float(self._threshold("max_changed_lines", 500))
        diff = ctx.diff or ctx.diff_stats

        # Non-edit tasks with no diff are considered minimal.
        if diff is None or (
            not diff.changed_files and diff.insertions == 0 and diff.deletions == 0
        ):
            return build_result(
                metric_id=self.id,
                display_name=self.display_name,
                group=self.group,
                raw_score=1.0,
                weight=self.config.weight,
                normalization=self.config.normalization,
                confidence=0.7,
                reasoning="No diff produced; treated as minimal for this trial",
                evidence=[{"changed_files": 0, "changed_lines": 0}],
                suggested_improvements=[],
                metric_version=self.config.version,
                details={"no_diff": True},
            )

        files = list(diff.changed_files)
        justified = set(diff.justified_files or [])
        if ctx.task:
            justified |= set(ctx.task.files)
        unjustified = [f for f in files if f not in justified]
        lines = diff.insertions + diff.deletions

        file_ratio = min(1.0, len(files) / max_files) if max_files > 0 else 0.0
        line_ratio = min(1.0, lines / max_lines) if max_lines > 0 else 0.0
        unjust_penalty = min(0.4, 0.1 * len(unjustified))
        raw = 1.0 - 0.5 * file_ratio - 0.5 * line_ratio - unjust_penalty

        conf = evidence_confidence(
            self.config.confidence_mode,
            evidence_items=len(files) + (1 if lines else 0),
            expected_items=max(1, len(files)),
        )
        improvements = []
        if unjustified:
            improvements.append(f"Avoid touching unjustified files: {unjustified[:5]}")
        if file_ratio > 0.5 or line_ratio > 0.5:
            improvements.append("Reduce patch size toward the minimal sufficient change")

        return build_result(
            metric_id=self.id,
            display_name=self.display_name,
            group=self.group,
            raw_score=raw,
            weight=self.config.weight,
            normalization=self.config.normalization,
            confidence=conf,
            reasoning=(
                f"{len(files)} files / {lines} lines changed; "
                f"{len(unjustified)} unjustified; budgets files={max_files}, lines={max_lines}"
            ),
            evidence=[
                {
                    "changed_files": files,
                    "changed_lines": lines,
                    "unjustified": unjustified,
                }
            ],
            suggested_improvements=improvements,
            metric_version=self.config.version,
            details={
                "file_ratio": file_ratio,
                "line_ratio": line_ratio,
                "unjustified_count": len(unjustified),
            },
        )
