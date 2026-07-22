"""Experiment artifact manager — manifests, metadata, summaries."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from githubbench_delta.research.models import ExperimentManifest, ResearchExperiment

DEFAULT_RESEARCH_ROOT = Path("results/research")


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def _config_hash(experiment: ResearchExperiment) -> str:
    payload = experiment.model_dump(mode="json")
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _detect_hardware() -> dict[str, Any]:
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
    }
    # Optional CUDA / docker hints from env — never invent
    for key in ("CUDA_VISIBLE_DEVICES", "DOCKER_IMAGE", "HOSTNAME"):
        if key in os.environ:
            info[key.lower()] = os.environ[key]
    return info


def resolve_globs(globs: list[str], *, root: Path | None = None) -> list[str]:
    base = root or Path.cwd()
    found: list[str] = []
    for pattern in globs:
        for match in sorted(base.glob(pattern)):
            if match.is_file():
                found.append(str(match.relative_to(base) if match.is_relative_to(base) else match))
    return found


class ExperimentArtifactManager:
    """Write research experiment artifacts under results/research/<id>/<UTC>/."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or DEFAULT_RESEARCH_ROOT)

    def output_dir(self, experiment_id: str, *, stamp: str | None = None) -> Path:
        return self.root / experiment_id / (stamp or _utc_stamp())

    def write(
        self,
        experiment: ResearchExperiment,
        *,
        out_dir: Path | str | None = None,
        seed: int | None = None,
        agent_config: dict[str, Any] | None = None,
        extra_notes: list[str] | None = None,
        source_root: Path | None = None,
    ) -> Path:
        dest = Path(out_dir) if out_dir else self.output_dir(experiment.id)
        dest.mkdir(parents=True, exist_ok=True)

        sources = resolve_globs(experiment.artifact_globs, root=source_root or Path.cwd())
        notes = list(extra_notes or [])
        if not sources:
            notes.append("no source evaluation artifacts matched artifact_globs")
        notes.append("numeric publication claims omitted unless derived from real aggregates")

        manifest = ExperimentManifest(
            experiment_id=experiment.id,
            project=experiment.project,
            title=experiment.title,
            hypothesis=experiment.hypothesis,
            status=experiment.status,
            requires=experiment.requires,
            evidence_gap_ref=experiment.evidence_gap_ref,
            git_commit=_git_commit(),
            config_hash=_config_hash(experiment),
            source_artifacts=sources,
            notes=notes,
            metadata=dict(experiment.metadata),
        )
        (dest / "experiment_manifest.json").write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

        metadata: dict[str, Any] = {
            "seed": seed,
            "timestamp": datetime.now(UTC).isoformat(),
            "git_commit": manifest.git_commit,
            "config_hash": manifest.config_hash,
            "hardware": _detect_hardware(),
            "experiment_id": experiment.id,
            "status": experiment.status,
        }
        if agent_config:
            for key in ("model", "provider", "quantization", "agent_id"):
                if key in agent_config:
                    metadata[key] = agent_config[key]
            metadata["agent_config_keys"] = sorted(agent_config.keys())
        (dest / "experiment_metadata.json").write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding="utf-8",
        )

        summary = self._summary_md(experiment, manifest, sources)
        (dest / "experiment_summary.md").write_text(summary, encoding="utf-8")
        return dest

    def _summary_md(
        self,
        experiment: ResearchExperiment,
        manifest: ExperimentManifest,
        sources: list[str],
    ) -> str:
        lines = [
            f"# Research experiment: {experiment.id}",
            "",
            f"**Title:** {experiment.title}",
            f"**Project:** {experiment.project}",
            f"**Status:** {experiment.status}",
            f"**Evidence gap ref:** {experiment.evidence_gap_ref or '(none)'}",
            "",
            "## Hypothesis",
            "",
            f"- Statement: {experiment.hypothesis.statement}",
            f"- Null: {experiment.hypothesis.null or '(none)'}",
            "",
            "## Provenance",
            "",
            f"- Git commit: `{manifest.git_commit or 'unknown'}`",
            f"- Config hash: `{manifest.config_hash}`",
            "",
            "## Source evaluation artifacts",
            "",
        ]
        if sources:
            lines.extend(f"- `{s}`" for s in sources)
        else:
            lines.append("- *(none matched — no fabricated links)*")
        lines.extend(
            [
                "",
                "## Notes",
                "",
            ]
        )
        lines.extend(f"- {n}" for n in manifest.notes)
        lines.append("")
        return "\n".join(lines)
