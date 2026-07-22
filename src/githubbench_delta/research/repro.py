"""Reproducibility package writer."""

from __future__ import annotations

import json
import platform
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

from githubbench_delta.research.models import ResearchExperiment


def _installed_distributions() -> list[str]:
    lines: list[str] = []
    try:
        dists = sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower())
    except Exception:
        return ["# could not enumerate distributions"]
    for dist in dists:
        name = dist.metadata["Name"]
        ver = dist.version
        if name:
            lines.append(f"{name}=={ver}")
    return lines


class ReproducibilityPackage:
    """Write environment / deps / config / seeds under ``repro/``."""

    def write(
        self,
        experiment: ResearchExperiment,
        dest: Path | str,
        *,
        seed: int | None = None,
        model_ids: list[str] | None = None,
        extra_config: dict[str, Any] | None = None,
    ) -> Path:
        repro_dir = Path(dest) / "repro"
        repro_dir.mkdir(parents=True, exist_ok=True)

        env = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "executable": sys.executable,
            "timestamp": datetime.now(UTC).isoformat(),
            "experiment_id": experiment.id,
        }
        (repro_dir / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")

        deps = _installed_distributions()
        (repro_dir / "dependencies.txt").write_text("\n".join(deps) + "\n", encoding="utf-8")

        snapshot = {
            "experiment": experiment.model_dump(mode="json"),
            "extra": extra_config or {},
        }
        (repro_dir / "config_snapshot.yaml").write_text(
            yaml.safe_dump(snapshot, sort_keys=False),
            encoding="utf-8",
        )

        seeds = {
            "seed": seed,
            "model_ids": list(model_ids or []),
            "note": "Only caller-provided seeds/model ids; nothing invented",
        }
        (repro_dir / "seeds.json").write_text(json.dumps(seeds, indent=2), encoding="utf-8")
        return repro_dir
