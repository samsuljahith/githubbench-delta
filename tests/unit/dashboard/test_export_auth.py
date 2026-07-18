"""Export serialization and auth stub tests."""

from __future__ import annotations

import asyncio
import json

from githubbench_delta.dashboard.auth import get_current_principal
from githubbench_delta.dashboard.export import export, export_csv, export_json, export_markdown
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.dashboard.schemas import Principal


def test_export_formats(repo: ExperimentRepository) -> None:
    js = export_json(repo, experiment_id="exp_test001")
    data = json.loads(js)
    assert "leaderboard" in data
    assert data["experiment"]["experiment"]["experiment_id"] == "exp_test001"
    csv_body = export_csv(repo, experiment_id="exp_test001")
    assert "agent_id" in csv_body.splitlines()[0]
    assert "codex" in csv_body
    md = export_markdown(repo, experiment_id="exp_test001")
    assert "# GitHubBench-Delta Export" in md
    assert "Leaderboard" in md
    media, body = export("json", repo)
    assert media == "application/json"
    assert body


def test_auth_stub_anonymous() -> None:
    principal = asyncio.run(get_current_principal())
    assert isinstance(principal, Principal)
    assert principal.authenticated is False
    assert principal.subject == "anonymous"
