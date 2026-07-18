"""Manifest generation tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.datasets.factory import load_tasks
from githubbench_delta.datasets.manifest import (
    compute_content_hash,
    generate_manifest,
    load_dataset_metadata,
    write_manifest,
)


def test_manifest_counts_and_hash_stability() -> None:
    root = Path(__file__).resolve().parents[2]
    tasks = load_tasks(root / "datasets" / "v1" / "tasks.jsonl")
    meta = load_dataset_metadata(root / "datasets" / "v1" / "dataset.yaml")
    m1 = generate_manifest(tasks, metadata=meta)
    m2 = generate_manifest(tasks, metadata=meta)
    assert m1.task_count == 60
    assert m1.content_hash == m2.content_hash == compute_content_hash(tasks)
    assert sum(m1.category_counts.values()) == 60
    assert "python" in m1.language_counts


def test_write_manifest(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    tasks = load_tasks(root / "datasets" / "v1" / "tasks.jsonl")
    manifest = generate_manifest(tasks)
    path = write_manifest(manifest, tmp_path / "manifest.json")
    assert path.is_file()
    assert "content_hash" in path.read_text(encoding="utf-8")
