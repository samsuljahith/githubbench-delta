"""Pytest fixtures for methodology metric tests."""

from __future__ import annotations

import pytest

from githubbench_delta.core.config import load_config


@pytest.fixture(scope="module")
def app_config():
    return load_config()
