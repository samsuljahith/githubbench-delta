#!/usr/bin/env bash
# Build wheel + sdist and verify console script in an isolated environment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Checking LICENSE and Apache-2.0 metadata"
test -f LICENSE
grep -q 'Apache-2.0' pyproject.toml

echo "==> Building distributions"
rm -rf dist
uv build

WHEEL="$(ls dist/*.whl | head -n1)"
SDIST="$(ls dist/*.tar.gz | head -n1)"
echo "Wheel: $WHEEL"
echo "Sdist: $SDIST"

echo "==> Isolated install smoke"
TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

uv venv "$TMP/venv"
# shellcheck disable=SC1091
source "$TMP/venv/bin/activate"
uv pip install "$WHEEL"
githubbench version
python -c "import githubbench_delta; print(githubbench_delta.__version__)"
echo "==> Packaging OK"
