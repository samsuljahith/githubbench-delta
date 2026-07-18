"""BenchmarkRunner tests."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.benchmark.runner import BenchmarkRunner
from githubbench_delta.benchmark.sampling import sample_deterministic


def test_runner_full_batch_single_and_seed() -> None:
    root = Path(__file__).resolve().parents[2]
    runner = BenchmarkRunner(base_path=root, validate=True)
    catalog = runner.load_dataset(root / "datasets" / "v1")
    assert len(catalog) == 60

    full_a = [t.id for t in runner.full(seed=7)]
    full_b = [t.id for t in runner.full(seed=7)]
    assert full_a == full_b
    assert full_a != [t.id for t in runner.full(seed=8)]

    batch = runner.batch(n=3, seed=1)
    assert len(batch) == 3
    assert [t.id for t in batch] == [t.id for t in sample_deterministic(catalog.all(), 3, 1)]

    one = runner.single("gb-bug-fix-001")
    assert one.category.value == "bug_fix"
