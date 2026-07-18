"""Repository fingerprints and local resolution helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from githubbench_delta.core.models import RepositoryRef

__all__ = [
    "RepositoryRef",
    "resolve_local_path",
    "compute_local_fingerprint",
    "fingerprint_repository",
    "clone_repository",
]


def resolve_local_path(ref: RepositoryRef, base: Path | None = None) -> Path | None:
    """Resolve ``local_path`` relative to ``base`` when not absolute."""

    if not ref.local_path:
        return None
    path = Path(ref.local_path)
    if not path.is_absolute() and base is not None:
        path = (base / path).resolve()
    return path


def compute_local_fingerprint(repo_path: Path) -> str:
    """Compute a stable sha256 fingerprint over relative paths and file sizes."""

    root = repo_path.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Repository path not found: {root}")
    digest = hashlib.sha256()
    skip = {".git", ".venv", "node_modules", "__pycache__"}
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        files.append(path)
    for path in files:
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def fingerprint_repository(ref: RepositoryRef, *, base: Path | None = None) -> str:
    """Fingerprint a repository ref (local tree, or url@commit when remote-only)."""

    local = resolve_local_path(ref, base)
    if local is not None and local.exists():
        return compute_local_fingerprint(local)
    key = f"{ref.url or ''}@{ref.commit_sha or ref.branch or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def clone_repository(ref: RepositoryRef, destination: Path) -> Path:
    """Clone a remote repository (not implemented in Phase 3).

    TODO(future): Implement shallow clone with commit pinning via GitPython.
    """

    raise NotImplementedError(
        "clone_repository is reserved for a future phase; "
        "use local snapshots under datasets/fixtures/ for now"
    )
