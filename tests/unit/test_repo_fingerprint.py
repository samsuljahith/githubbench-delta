"""Repository fingerprint tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from githubbench_delta.datasets.repositories import (
    RepositoryRef,
    clone_repository,
    compute_local_fingerprint,
    fingerprint_repository,
)


def test_local_fingerprint_stable() -> None:
    root = Path(__file__).resolve().parents[2]
    repo = root / "datasets" / "fixtures" / "mini_repo"
    a = compute_local_fingerprint(repo)
    b = compute_local_fingerprint(repo)
    assert a == b
    assert len(a) == 64

    ref = RepositoryRef(local_path=str(repo), url="https://example.com/mini_repo")
    assert fingerprint_repository(ref) == a


def test_clone_not_implemented(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError):
        clone_repository(RepositoryRef(url="https://example.com/r"), tmp_path / "r")
