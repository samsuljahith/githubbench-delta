#!/usr/bin/env python3
"""Build datasets/v1/tasks.jsonl from curated author modules and refresh manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORS = ROOT / "datasets" / "v1" / "authors"
sys.path.insert(0, str(AUTHORS))
sys.path.insert(0, str(ROOT / "src"))

from corpus import all_tasks  # noqa: E402

from githubbench_delta.datasets.factory import load_tasks  # noqa: E402
from githubbench_delta.datasets.manifest import (  # noqa: E402
    generate_manifest,
    load_dataset_metadata,
    write_manifest,
)
from githubbench_delta.datasets.validators import CorpusQualityValidator  # noqa: E402


def main() -> None:
    records = all_tasks()
    out = ROOT / "datasets" / "v1" / "tasks.jsonl"
    with out.open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} tasks to {out}")

    tasks = load_tasks(out)
    meta = load_dataset_metadata(ROOT / "datasets" / "v1" / "dataset.yaml")
    CorpusQualityValidator(base_path=ROOT).validate(tasks, metadata=meta)
    manifest = generate_manifest(tasks, metadata=meta)
    write_manifest(manifest, ROOT / "datasets" / "v1" / "manifest.json")
    print(
        f"Manifest OK: count={manifest.task_count} hash={manifest.content_hash[:16]}…"
    )


if __name__ == "__main__":
    main()
