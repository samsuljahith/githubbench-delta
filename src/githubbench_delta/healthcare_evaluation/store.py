"""Persist healthcare reports under results/healthcare/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from githubbench_delta.core.config import load_config
from githubbench_delta.healthcare_evaluation.models import HealthcareReport


def healthcare_dir() -> Path:
    cfg = load_config()
    path = Path(cfg.runtime.pipeline.results_dir).resolve() / "healthcare"
    path.mkdir(parents=True, exist_ok=True)
    return path


def assessments_dir() -> Path:
    path = healthcare_dir() / "assessments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_report(report: HealthcareReport) -> Path:
    path = healthcare_dir() / f"{report.report_id}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_report(report_id: str) -> HealthcareReport | None:
    path = healthcare_dir() / f"{report_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return HealthcareReport.model_validate(data)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def save_assessment(assessment: dict[str, Any]) -> Path:
    aid = str(assessment.get("assessment_id") or "unknown")
    path = assessments_dir() / f"{aid}.json"
    path.write_text(json.dumps(assessment, indent=2), encoding="utf-8")
    return path


def load_assessment(assessment_id: str) -> dict[str, Any] | None:
    path = assessments_dir() / f"{assessment_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None
