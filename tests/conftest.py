"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from githubbench_delta.core.config import clear_config_cache, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs"


@pytest.fixture
def config_dir() -> Path:
    return CONFIG_DIR


@pytest.fixture
def app_config(config_dir: Path):
    clear_config_cache()
    return load_config(config_dir)
