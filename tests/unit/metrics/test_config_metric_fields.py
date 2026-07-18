"""Config fields for Phase 4 metric configuration."""

from __future__ import annotations

from githubbench_delta.core.config import (
    ConfidenceMode,
    MetricConfiguration,
    NormalizationStrategy,
    load_config,
)


def test_metrics_yaml_phase4_fields() -> None:
    cfg = load_config()
    for mid, ev in cfg.evaluators.items():
        assert isinstance(ev, MetricConfiguration)
        assert ev.version == "1.0.0"
        assert ev.normalization == NormalizationStrategy.CLAMP_01
        assert ev.confidence_mode == ConfidenceMode.EVIDENCE_COVERAGE
        assert isinstance(ev.strict, bool)
        assert mid == ev.id
