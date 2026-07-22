"""MDS engine — orchestrate twin load, estimation, Bayesian discount, decompose."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.memorization.bayesian import BayesianDiscountModel
from githubbench_delta.memorization.decompose import CapabilityDecomposer
from githubbench_delta.memorization.estimator import MemorizationEstimator
from githubbench_delta.memorization.models import MemorizationReport, TwinTaskSpec
from githubbench_delta.memorization.validate import TwinValidator

ASSUMPTIONS: list[str] = [
    "Observed score decomposes as S_obs = G + L (generalization + memorization lift).",
    "When twin scores exist: L = max(0, S_obs - S_twin) and G = S_obs - L.",
    "When twins are absent: proxy L from (1 - consistency/grounding metrics) × 0.5.",
    "BayesianDiscountModel uses a Beta(1,1) prior with fractional lift updates.",
    "MDS is post-processing only; it does not modify benchmark metrics or artifacts.",
    "This model does not causally identify memorization — twin agreement is correlational.",
]


class MemorizationEngine:
    """Load experiment rows and produce a MemorizationReport."""

    def __init__(
        self,
        *,
        results_dir: Path | str | None = None,
        estimator: MemorizationEstimator | None = None,
        bayesian: BayesianDiscountModel | None = None,
        decomposer: CapabilityDecomposer | None = None,
        validator: TwinValidator | None = None,
    ) -> None:
        self.repo = ExperimentRepository(results_dir=results_dir)
        self.estimator = estimator or MemorizationEstimator()
        self.bayesian = bayesian or BayesianDiscountModel()
        self.decomposer = decomposer or CapabilityDecomposer()
        self.validator = validator or TwinValidator()

    def analyze(
        self,
        experiment_ids: list[str],
        *,
        twins_path: Path | str | None = None,
        twin_specs: list[TwinTaskSpec] | None = None,
    ) -> MemorizationReport:
        notes: list[str] = []
        specs = list(twin_specs or [])
        if twins_path is not None:
            loaded = self.validator.load_twins_jsonl(twins_path)
            specs.extend(loaded)
            notes.append(f"Loaded {len(loaded)} twin specs from {twins_path}.")

        rows = []
        for eid in experiment_ids:
            found = self.repo.evaluation_rows(eid)
            if not found:
                notes.append(f"No evaluation rows for {eid}.")
            rows.extend(found)

        lifts, mode, est_notes = self.estimator.estimate(rows, twin_specs=specs)
        notes.extend(est_notes)

        posteriors = []
        for lift in lifts:
            sample = [p.lift for p in lift.pairs]
            # In proxy mode, also down-weight by duplicating prior (already scaled lifts)
            posteriors.append(
                self.bayesian.fit_posterior(
                    sample,
                    agent_id=lift.agent_id,
                    mean_obs=lift.mean_obs,
                )
            )

        breakdowns = self.decomposer.decompose(lifts, posteriors)
        overall_mode = mode
        if lifts and all(x.mode == "proxy" for x in lifts):
            overall_mode = "proxy"
        elif lifts and any(x.mode == "twin" for x in lifts):
            overall_mode = "twin"

        return MemorizationReport(
            experiment_ids=list(experiment_ids),
            mode=overall_mode,
            lifts=lifts,
            breakdowns=breakdowns,
            posteriors=posteriors,
            twin_specs=specs,
            notes=notes,
            assumptions=list(ASSUMPTIONS),
            metadata={
                "n_rows": len(rows),
                "n_agents": len(lifts),
                "n_twin_specs": len(specs),
            },
        )
