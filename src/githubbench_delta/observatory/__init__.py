"""Half-Life Observatory — longitudinal benchmark aging analysis."""

from __future__ import annotations

from githubbench_delta.observatory.decay import DecayModel
from githubbench_delta.observatory.export import ObservatoryExporter
from githubbench_delta.observatory.half_life import HalfLifeEstimator
from githubbench_delta.observatory.history import BenchmarkHistory
from githubbench_delta.observatory.ingest import ingest_experiments, snapshots_from_experiment
from githubbench_delta.observatory.models import (
    BenchmarkSnapshot,
    DecayCurve,
    HalfLifeEstimate,
    MetricSummary,
    RegressionEvent,
    TrendReport,
)
from githubbench_delta.observatory.regression import RegressionDetector
from githubbench_delta.observatory.trends import TrendAnalyzer

__all__ = [
    "BenchmarkHistory",
    "BenchmarkSnapshot",
    "DecayCurve",
    "DecayModel",
    "HalfLifeEstimate",
    "HalfLifeEstimator",
    "MetricSummary",
    "ObservatoryExporter",
    "RegressionDetector",
    "RegressionEvent",
    "TrendAnalyzer",
    "TrendReport",
    "ingest_experiments",
    "snapshots_from_experiment",
]
