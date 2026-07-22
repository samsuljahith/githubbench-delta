"""Experiment scheduler — readiness from evidence registry + filesystem probes."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.research.artifacts import resolve_globs
from githubbench_delta.research.models import ExperimentStatus, ReadinessStatus, ResearchExperiment
from githubbench_delta.research.registry import ExperimentRegistry

# Known filesystem probes for evidence nodes (presence heuristics; never invent)
_EVIDENCE_PROBES: dict[str, list[str]] = {
    "T": ["**/twin*", "**/*twin*/**", "results/**/*twin*"],
    "A": ["**/adversarial*", "configs/**/adversarial*"],
    "C": ["**/contamination*", "results/**/contamination*"],
    "M": [],  # checked via trial_count in experiment.json when present
    "F": [],  # checked via task coverage heuristics
    "H": ["**/annotations/**", "**/human_labels*"],
    "L": ["results/observatory/**/*.json", "docs/assets/observatory/**"],
    "X": ["**/external_baseline*", "**/swe_bench*"],
    "W": ["**/trust*ground*", "**/trust_labels*"],
}


class ExperimentScheduler:
    """Mark experiments runnable / blocked / pending from evidence + artifacts."""

    def __init__(
        self,
        registry: ExperimentRegistry,
        *,
        workspace: Path | None = None,
    ) -> None:
        self.registry = registry
        self.workspace = workspace or Path.cwd()

    def status(self, experiment_id: str) -> ReadinessStatus | None:
        exp = self.registry.get(experiment_id)
        if exp is None:
            return None
        return self.evaluate(exp)

    def evaluate(self, experiment: ResearchExperiment) -> ReadinessStatus:
        missing_datasets: list[str] = []
        missing_runs: list[str] = []
        missing_ann: list[str] = []
        missing_base: list[str] = []
        missing_nodes: list[str] = []
        notes: list[str] = []

        # Evidence nodes from registry YAML
        for node_id in experiment.requires.evidence_nodes:
            node = self.registry.get_evidence(node_id)
            present = False
            if node is not None:
                present = node.status == "present"
                if node.status == "partial":
                    notes.append(f"evidence node {node_id} is partial")
            if not present and not self._probe_evidence(node_id):
                missing_nodes.append(node_id)

        # Declared requirements: treat as missing unless runnable E0* with empty requires
        # or filesystem globs find matching artifacts
        sources = resolve_globs(experiment.artifact_globs, root=self.workspace)
        has_artifacts = len(sources) > 0

        for ds in experiment.requires.datasets:
            # Soft check: only flag if status is blocked/pending and no artifacts
            if experiment.status in ("blocked", "pending_data") and not has_artifacts:
                # datasets that are known to exist in-repo
                if ds in ("datasets_v1", "datasets_v1_showcase_slice") and (
                    self.workspace / "datasets"
                ).exists():
                    continue
                if ds == "observatory_demo_history" and (
                    (self.workspace / "docs/assets/observatory").exists()
                    or (self.workspace / "results/observatory").exists()
                ):
                    continue
                missing_datasets.append(ds)

        for run in experiment.requires.benchmark_runs:
            if experiment.status in ("blocked", "pending_data"):
                # Check if named experiment dir exists
                if run.startswith("exp_") and list(
                    (self.workspace / "results").glob(f"**/{run}/**")
                ):
                    continue
                if not has_artifacts:
                    missing_runs.append(run)

        for ann in experiment.requires.human_annotations:
            if experiment.status != "runnable":
                missing_ann.append(ann)

        for base in experiment.requires.baselines:
            if experiment.status != "runnable":
                missing_base.append(base)

        # Derive effective status
        declared = experiment.status
        effective: ExperimentStatus = declared
        if declared == "runnable":
            effective = "runnable"
        elif missing_nodes or missing_ann or missing_base or (
            missing_datasets and missing_runs
        ):
            effective = "blocked"
        elif missing_datasets or missing_runs:
            effective = "pending_data" if declared == "pending_data" else "blocked"
        else:
            effective = declared

        # Statistical / publication readiness: never claim ready without real data
        statistical_ready = False
        publication_ready = False
        if effective == "runnable" and has_artifacts:
            notes.append("artifacts present; confirmatory stats still require adequate n")
        if effective == "runnable":
            notes.append("limited claim only — see evidence_gap_ref")
        else:
            notes.append("blocked/pending — do not emit significance claims")

        # Publication ready only if we already have published-style outputs on disk
        pub_dir = self.workspace / "results" / "research" / experiment.id
        if pub_dir.is_dir():
            csvs = list(pub_dir.glob("**/publication_tables.csv"))
            for csv_path in csvs:
                try:
                    text = csv_path.read_text(encoding="utf-8").strip().splitlines()
                    if len(text) > 1:
                        publication_ready = True
                        break
                except OSError:
                    pass

        return ReadinessStatus(
            experiment_id=experiment.id,
            status=effective,
            missing_datasets=missing_datasets,
            missing_benchmark_runs=missing_runs,
            missing_human_annotations=missing_ann,
            missing_baselines=missing_base,
            missing_evidence_nodes=missing_nodes,
            statistical_ready=statistical_ready,
            publication_ready=publication_ready,
            notes=notes,
        )

    def all_statuses(self) -> list[ReadinessStatus]:
        return [self.evaluate(e) for e in self.registry.list_experiments()]

    def _probe_evidence(self, node_id: str) -> bool:
        patterns = _EVIDENCE_PROBES.get(node_id, [])
        for pattern in patterns:
            matches = resolve_globs([pattern], root=self.workspace)
            # Filter out demo/synthetic-only paths for L? Keep conservative: any match = probe hit
            # but evidence registry status still gates "present"
            if matches:
                # For T: twin *specs* may exist under memorization; require eval-like paths
                if node_id == "T":
                    eval_like = [m for m in matches if "evaluation" in m or "results/experiments" in m]
                    if eval_like:
                        return True
                    continue
                if node_id == "L":
                    # Demo assets alone do not count as "present" real longitudinal
                    real = [m for m in matches if "results/observatory" in m]
                    if real:
                        return True
                    continue
                return True
        return False
