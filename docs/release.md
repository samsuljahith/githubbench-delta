# Release Guide

## Versioning

- **SemVer** (`MAJOR.MINOR.PATCH`)
- Keep [`pyproject.toml`](../pyproject.toml) `version` and [`src/githubbench_delta/__init__.py`](../src/githubbench_delta/__init__.py) `__version__` in sync
- Tag releases as `vX.Y.Z`

## Checklist

1. Update [CHANGELOG.md](../CHANGELOG.md): move `[Unreleased]` notes into `## [X.Y.Z] — YYYY-MM-DD`
2. Bump version in `pyproject.toml` and `__init__.py`
3. Ensure CI is green on `main`
4. `bash scripts/check_packaging.sh`
5. Commit release prep
6. Tag and push:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
7. GitHub Actions [release.yml](../.github/workflows/release.yml) builds artifacts and creates a GitHub Release

## Hotfix

Bump PATCH, document in CHANGELOG, tag immediately after CI green.
