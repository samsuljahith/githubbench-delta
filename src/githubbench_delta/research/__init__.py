"""Research execution platform — reproducibility-focused experiment orchestration.

Additive package: does not change metrics, evaluators, or experiment schemas.
Never fabricates statistical results; insufficient data → status flags only.
"""

from __future__ import annotations

from githubbench_delta.research.artifacts import ExperimentArtifactManager
from githubbench_delta.research.dashboard import ValidationDashboard
from githubbench_delta.research.models import (
    ExperimentManifest,
    PowerEstimate,
    ReadinessStatus,
    ResearchExperiment,
    ResearchHypothesis,
    ResearchProject,
    StatResult,
)
from githubbench_delta.research.plugins import experiment_plugin, register_experiment
from githubbench_delta.research.power import MDEEstimator, SampleSizeEstimator, VarianceEstimator
from githubbench_delta.research.publish import PublicationExporter
from githubbench_delta.research.registry import ExperimentRegistry
from githubbench_delta.research.repro import ReproducibilityPackage
from githubbench_delta.research.scheduler import ExperimentScheduler

__all__ = [
    "ExperimentArtifactManager",
    "ExperimentManifest",
    "ExperimentRegistry",
    "ExperimentScheduler",
    "MDEEstimator",
    "PowerEstimate",
    "PublicationExporter",
    "ReadinessStatus",
    "ReproducibilityPackage",
    "ResearchExperiment",
    "ResearchHypothesis",
    "ResearchProject",
    "SampleSizeEstimator",
    "StatResult",
    "ValidationDashboard",
    "VarianceEstimator",
    "experiment_plugin",
    "register_experiment",
]
