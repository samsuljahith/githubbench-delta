"""Registry auto-discovery and scheduler readiness tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.research.registry import ExperimentRegistry
from githubbench_delta.research.scheduler import ExperimentScheduler

ROOT = Path(__file__).resolve().parents[2]


def test_registry_loads_seed_experiments():
    reg = ExperimentRegistry(
        experiments_dir=ROOT / "configs/research/experiments",
        evidence_path=ROOT / "configs/research/evidence_registry.yaml",
        projects_path=ROOT / "configs/research/projects.yaml",
    )
    reg.reload()
    ids = {e.id for e in reg.list_experiments()}
    assert "E0a" in ids and "E1" in ids and "E10" in ids
    assert len(ids) >= 14  # E0a-d + E1-E10
    e1 = reg.get("E1")
    assert e1 is not None
    assert e1.status == "blocked"
    assert "T" in e1.requires.evidence_nodes
    nodes = {n.id for n in reg.evidence_nodes()}
    assert nodes >= {"T", "A", "C", "M", "F", "H", "L", "X", "W"}


def test_scheduler_marks_e0_runnable_and_e1_blocked():
    reg = ExperimentRegistry(
        experiments_dir=ROOT / "configs/research/experiments",
        evidence_path=ROOT / "configs/research/evidence_registry.yaml",
        projects_path=ROOT / "configs/research/projects.yaml",
    )
    reg.reload()
    sched = ExperimentScheduler(reg, workspace=ROOT)
    e0 = sched.status("E0a")
    e1 = sched.status("E1")
    assert e0 is not None and e0.status == "runnable"
    assert e1 is not None and e1.status == "blocked"
    assert "T" in e1.missing_evidence_nodes
