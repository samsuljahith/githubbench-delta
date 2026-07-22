"""Artifact / publish / dashboard smoke tests — no fabricated numbers."""

from __future__ import annotations

import json
from pathlib import Path

from githubbench_delta.research.artifacts import ExperimentArtifactManager
from githubbench_delta.research.dashboard import ValidationDashboard
from githubbench_delta.research.publish import PublicationExporter
from githubbench_delta.research.registry import ExperimentRegistry
from githubbench_delta.research.repro import ReproducibilityPackage

ROOT = Path(__file__).resolve().parents[2]


def _reg() -> ExperimentRegistry:
    reg = ExperimentRegistry(
        experiments_dir=ROOT / "configs/research/experiments",
        evidence_path=ROOT / "configs/research/evidence_registry.yaml",
        projects_path=ROOT / "configs/research/projects.yaml",
    )
    reg.reload()
    return reg


def test_artifact_writer_fields(tmp_path: Path):
    reg = _reg()
    exp = reg.get("E1")
    assert exp is not None
    dest = ExperimentArtifactManager(tmp_path).write(exp, out_dir=tmp_path / "E1", seed=7)
    manifest = json.loads((dest / "experiment_manifest.json").read_text(encoding="utf-8"))
    meta = json.loads((dest / "experiment_metadata.json").read_text(encoding="utf-8"))
    assert manifest["experiment_id"] == "E1"
    assert manifest["config_hash"]
    assert "hypothesis" in manifest
    assert meta["seed"] == 7
    assert "hardware" in meta
    assert (dest / "experiment_summary.md").is_file()
    ReproducibilityPackage().write(exp, dest, seed=7)
    assert (dest / "repro" / "environment.json").is_file()
    assert (dest / "repro" / "dependencies.txt").is_file()
    assert (dest / "repro" / "seeds.json").is_file()


def test_publish_empty_when_no_aggregates(tmp_path: Path):
    reg = _reg()
    exp = reg.get("E1")
    assert exp is not None
    # Point globs at empty dir so no fabricated rows
    exp.artifact_globs = ["does/not/exist/**/*.json"]
    paths = PublicationExporter().export(exp, tmp_path, source_root=tmp_path)
    assert paths["n_rows"] == 0
    csv_text = Path(paths["csv"]).read_text(encoding="utf-8")
    assert csv_text.strip().startswith("source,")
    assert len(csv_text.strip().splitlines()) == 1  # header only
    figs = json.loads(Path(paths["figures"]).read_text(encoding="utf-8"))
    assert figs == []


def test_dashboard_html(tmp_path: Path):
    reg = _reg()
    html = ValidationDashboard(reg, workspace=ROOT).build_html()
    assert "Research Validation Report" in html
    assert "never fabricates" in html.lower() or "Honesty rule" in html
    assert "E1" in html and "E0a" in html
    out = ValidationDashboard(reg, workspace=ROOT).write(tmp_path / "validation_report.html")
    assert out.is_file()
