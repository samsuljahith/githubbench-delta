"""Live per-patient case runs — synthetic patient chrome seeds a real experiment."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from githubbench_delta.api.facade import (
    FacadeEnvelope,
    build_assessment,
    build_evaluate,
    build_trust,
)
from githubbench_delta.api.synthetic import GeneratePatientsRequest, generate_patients_envelope
from githubbench_delta.core.config import load_config
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.pipeline.experiment import ExperimentRunner
from githubbench_delta.pipeline.models import ExperimentSpec

cases_router = APIRouter(tags=["cases"])

ALLOWED_CASE_AGENTS = frozenset({"minicpm", "claude", "codex"})

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
_inflight: dict[str, asyncio.Lock] = {}
_task_ids_cache: list[str] | None = None

AGENT_CATALOG: list[dict[str, str]] = [
    {
        "id": "minicpm",
        "label": "MiniCPM",
        "deployment": "local",
        "hint": "Local via Ollama. Prefer this if you want offline / no cloud keys.",
    },
    {
        "id": "claude",
        "label": "Claude",
        "deployment": "hosted",
        "hint": "Needs ANTHROPIC_API_KEY.",
    },
    {
        "id": "codex",
        "label": "Codex (OpenAI)",
        "deployment": "hosted",
        "hint": "Needs OPENAI_API_KEY + quota.",
    },
]


class SyntheticPatientPayload(BaseModel):
    id: str = Field(..., min_length=1)
    name: str | None = None
    age: int | None = None
    sex: str | None = None
    chief_complaint: str | None = None
    comorbidities: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    living_situation: str | None = None
    risk_profile: str | None = None


class CaseRunRequest(BaseModel):
    patient: SyntheticPatientPayload
    agent_id: str | None = None
    force: bool = False


class AgentCatalogEntry(BaseModel):
    id: str
    label: str
    deployment: Literal["local", "hosted"]
    hint: str


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _case_agent_default() -> str:
    return os.environ.get("GITHUBBENCH_CASE_AGENT", "minicpm").strip() or "minicpm"


def resolve_case_agent(requested: str | None) -> str | None:
    """Return a valid agent id, or None if the request is invalid."""

    if requested is not None and requested.strip():
        aid = requested.strip().lower()
        if aid not in ALLOWED_CASE_AGENTS:
            return None
        return aid
    fallback = _case_agent_default().lower()
    if fallback not in ALLOWED_CASE_AGENTS:
        return "minicpm"
    return fallback


def _case_dataset() -> Path:
    return Path(os.environ.get("GITHUBBENCH_CASE_DATASET", "datasets/v1")).expanduser()


def _cases_dir() -> Path:
    cfg = load_config()
    return Path(cfg.runtime.pipeline.results_dir).resolve().parent / "cases"


def _safe_patient_key(patient_id: str) -> str:
    cleaned = _SAFE_ID.sub("_", patient_id.strip())
    return cleaned or "unknown"


def _cache_path(patient_id: str, agent_id: str) -> Path:
    return _cases_dir() / f"{_safe_patient_key(patient_id)}__{_safe_patient_key(agent_id)}.json"


def _list_task_ids(dataset_path: Path) -> list[str]:
    global _task_ids_cache
    if _task_ids_cache is not None:
        return _task_ids_cache
    tasks_file = dataset_path / "tasks.jsonl"
    if not tasks_file.is_file():
        raise FileNotFoundError(f"Dataset tasks not found: {tasks_file}")
    ids: list[str] = []
    with tasks_file.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            tid = str(data.get("id") or "").strip()
            if tid:
                ids.append(tid)
    if not ids:
        raise ValueError(f"No task ids in {tasks_file}")
    _task_ids_cache = ids
    return ids


def task_id_for_patient(patient_id: str, task_ids: list[str]) -> str:
    digest = hashlib.sha256(patient_id.encode("utf-8")).hexdigest()
    return task_ids[int(digest, 16) % len(task_ids)]


def seed_for_patient(patient_id: str) -> int:
    digest = hashlib.sha256(f"seed:{patient_id}".encode()).hexdigest()
    return int(digest[:8], 16)


def _read_cache(patient_id: str, agent_id: str) -> dict[str, Any] | None:
    path = _cache_path(patient_id, agent_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("experiment_id"):
        return None
    return data


def _write_cache(patient_id: str, agent_id: str, payload: dict[str, Any]) -> None:
    path = _cache_path(patient_id, agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _delete_cache(patient_id: str, agent_id: str) -> None:
    path = _cache_path(patient_id, agent_id)
    if path.is_file():
        path.unlink()


def _lock_for(patient_id: str, agent_id: str) -> asyncio.Lock:
    key = f"{_safe_patient_key(patient_id)}::{_safe_patient_key(agent_id)}"
    lock = _inflight.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _inflight[key] = lock
    return lock


def _inspect_agent_run(experiment_id: str, *, agent_id: str) -> dict[str, Any]:
    """Return success/error + trajectory loop stats for the agent unit."""

    repo = ExperimentRepository()
    rows = repo.load_evaluations_raw(experiment_id)
    matched = [r for r in rows if str(r.get("agent_id", "")) == agent_id] or rows
    success = True
    error: str | None = None
    metrics: dict[str, Any] = {}
    if matched:
        summary = matched[0].get("agent_result_summary") or {}
        if isinstance(summary, dict):
            if summary.get("success") is False:
                success = False
            err = summary.get("error")
            if err:
                error = str(err)
                success = False

    step_count = 0
    tool_call_count = 0
    error_count = 0
    latency_ms = 0.0
    traj_path = repo.experiment_dir(experiment_id) / "trajectory.jsonl"
    if traj_path.is_file():
        with traj_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if agent_id and str(event.get("agent_id", "")) not in ("", agent_id):
                    continue
                ar = event.get("agent_result") or {}
                if isinstance(ar, dict):
                    if ar.get("success") is False:
                        success = False
                    if ar.get("error"):
                        error = str(ar.get("error"))
                        success = False
                    m = ar.get("metrics") or {}
                    if isinstance(m, dict):
                        metrics = m
                        tool_call_count = int(m.get("tool_call_count") or tool_call_count or 0)
                        error_count = int(m.get("error_count") or error_count or 0)
                        raw_lat = m.get("latency_ms")
                        if isinstance(raw_lat, (int, float)):
                            latency_ms = float(raw_lat)
                traj = event.get("trajectory") or {}
                steps = traj.get("steps") if isinstance(traj, dict) else None
                if isinstance(steps, list):
                    step_count = max(step_count, len(steps))
                    if not isinstance(metrics.get("tool_call_count"), (int, float)):
                        tool_call_count = sum(
                            1 for step in steps if isinstance(step, dict) and step.get("tool_call")
                        )
                break  # first matching unit

    if isinstance(metrics.get("tool_call_count"), (int, float)):
        tool_call_count = int(metrics["tool_call_count"])

    return {
        "success": success,
        "error": error,
        "step_count": step_count,
        "tool_call_count": tool_call_count,
        "error_count": error_count,
        "latency_ms": latency_ms,
    }


def _loop_engineering(
    *,
    inspect: dict[str, Any],
    evaluate_data: dict[str, Any] | None,
) -> dict[str, Any]:
    """Trajectory/tool-loop telemetry + all scored metrics (not a 5-key subset)."""

    step_count = int(inspect.get("step_count") or 0)
    tool_call_count = int(inspect.get("tool_call_count") or 0)
    related: list[dict[str, Any]] = []
    metrics = (evaluate_data or {}).get("metrics") or []
    if isinstance(metrics, list):
        for m in metrics:
            if not isinstance(m, dict):
                continue
            key = str(m.get("key") or "")
            if not key:
                continue
            entry: dict[str, Any] = {
                "key": key,
                "label": m.get("label") or key,
                "value": m.get("value"),
                "unit": m.get("unit"),
            }
            reasoning = str(m.get("reasoning") or "").strip()
            if reasoning:
                entry["reasoning"] = reasoning
            related.append(entry)
    summary = (
        f"Agent took {step_count} trajectory steps / {tool_call_count} tool calls before scoring"
    )
    return {
        "step_count": step_count,
        "tool_call_count": tool_call_count,
        "error_count": int(inspect.get("error_count") or 0),
        "latency_ms": float(inspect.get("latency_ms") or 0.0),
        "summary": summary,
        "related_metrics": related,
    }


def _envelope_from_experiment(
    experiment_id: str,
    *,
    agent_id: str,
    task_id: str,
    patient: SyntheticPatientPayload,
    cached: bool,
) -> FacadeEnvelope:
    inspect = _inspect_agent_run(experiment_id, agent_id=agent_id)
    if not inspect["success"]:
        detail = inspect.get("error") or "Agent run failed (provider/connection error)"
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=experiment_id,
            detail=str(detail),
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "cached": cached,
                "patient": patient.model_dump(),
                "loop_engineering": _loop_engineering(inspect=inspect, evaluate_data=None),
            },
        )

    assessment = build_assessment(experiment_id, agent_id=agent_id)
    evaluate = build_evaluate(experiment_id, agent_id=agent_id)
    trust = build_trust(experiment_id, agent_id=agent_id)

    if not (assessment.ok and evaluate.ok and trust.ok):
        detail = (
            assessment.detail
            or evaluate.detail
            or trust.detail
            or "Case experiment produced no evaluation scores"
        )
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=experiment_id,
            detail=detail,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "cached": cached,
                "patient": patient.model_dump(),
                "assessment": assessment.model_dump(),
                "evaluate": evaluate.model_dump(),
                "trust": trust.model_dump(),
            },
        )

    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=experiment_id,
        detail=None,
        data={
            "task_id": task_id,
            "agent_id": agent_id,
            "cached": cached,
            "patient": patient.model_dump(),
            "assessment": assessment.data,
            "evaluate": evaluate.data,
            "trust": trust.data,
            "loop_engineering": _loop_engineering(
                inspect=inspect,
                evaluate_data=evaluate.data if isinstance(evaluate.data, dict) else None,
            ),
            "provenance": (
                "Synthetic patient chrome only. Scores from live GitHubBench-Delta "
                "ExperimentRunner + deterministic evaluators (GitHub engineering tasks). "
                "One selected agent under test — not an LLM-as-judge."
            ),
        },
    )


async def _run_case_experiment(
    *,
    patient: SyntheticPatientPayload,
    task_id: str,
    agent_id: str,
    dataset_path: Path,
) -> str:
    dry_run = _env_bool("GITHUBBENCH_CASE_DRY_RUN", default=False)
    runner = ExperimentRunner()
    seed = seed_for_patient(patient.id)
    manifest = await runner.run(
        ExperimentSpec(
            dataset_path=dataset_path,
            task_ids=[task_id],
            agent_ids=[agent_id],
            trial_count=1,
            seed=seed,
            max_concurrency=1,
            resume=False,
            use_cache=True,
            dry_run=dry_run,
            name=f"case-{_safe_patient_key(patient.id)}-{_safe_patient_key(agent_id)}",
            metadata={
                "synthetic_patient": patient.model_dump(),
                "case_run": True,
                "case_agent": agent_id,
                "case_task_id": task_id,
            },
        )
    )
    return manifest.experiment_id


@cases_router.get("/cases/agents", response_model=list[AgentCatalogEntry])
def get_case_agents() -> list[AgentCatalogEntry]:
    """Catalog of agents available for the setup wizard (agent under test)."""

    return [AgentCatalogEntry.model_validate(row) for row in AGENT_CATALOG]


SCENARIO_TYPES = frozenset(
    {
        "complete",
        "missing_finding",
        "hallucination_risk",
        "contraindication",
        "incomplete",
    }
)


def _synthetic_fixtures_dir() -> Path:
    # Repo root / datasets / synthetic (relative to package ancestors).
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "datasets" / "synthetic"
        if candidate.is_dir():
            return candidate
    return Path("datasets/synthetic").resolve()


def load_synthetic_fixtures() -> list[dict[str, Any]]:
    """Load versioned fixture JSON files (one of each scenario_type)."""

    root = _synthetic_fixtures_dir()
    manifest_path = root / "manifest.json"
    files: list[str] = []
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = list(manifest.get("patients") or [])
        except (OSError, json.JSONDecodeError):
            files = []
    if not files:
        files = sorted(p.name for p in root.glob("patient_*.json"))

    rows: list[dict[str, Any]] = []
    for name in files:
        path = root / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        st = str(data.get("scenario_type") or "")
        if st not in SCENARIO_TYPES:
            continue
        rows.append(data)
    return rows


@cases_router.get("/cases/fixture-patients", response_model=FacadeEnvelope)
def get_fixture_patients() -> FacadeEnvelope:
    """Return fixed synthetic patient fixtures for reproducible demos (no Gemini)."""

    fixtures = load_synthetic_fixtures()
    if not fixtures:
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail="insufficient_data: no synthetic fixtures found under datasets/synthetic/",
            data=None,
        )
    patients = []
    for fx in fixtures:
        patient = dict(fx.get("patient") or {})
        if not patient.get("id"):
            patient["id"] = fx.get("id")
        patients.append(
            {
                "id": patient.get("id"),
                "name": patient.get("name") or fx.get("name"),
                "age": patient.get("age"),
                "sex": patient.get("sex"),
                "chief_complaint": patient.get("chief_complaint"),
                "comorbidities": patient.get("comorbidities") or [],
                "medications": patient.get("medications") or [],
                "living_situation": patient.get("living_situation"),
                "risk_profile": patient.get("risk_profile"),
                "scenario_type": fx.get("scenario_type"),
                "conversation": fx.get("conversation") or [],
                "conversation_text": fx.get("conversation_text"),
            }
        )
    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=None,
        detail=None,
        data={
            "source": "datasets/synthetic",
            "count": len(patients),
            "patients": patients,
        },
    )


@cases_router.post("/cases/generate-patients", response_model=FacadeEnvelope)
def post_generate_patients(body: GeneratePatientsRequest) -> FacadeEnvelope:
    """Generate synthetic patients via Gemini (chrome only)."""

    return generate_patients_envelope(body)


@cases_router.post("/cases/run", response_model=FacadeEnvelope)
async def post_case_run(body: CaseRunRequest) -> FacadeEnvelope:
    """Seed a real 1-unit experiment from a synthetic patient; return live scores."""

    patient = body.patient
    patient_id = patient.id.strip()
    if not patient_id:
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail="patient.id is required",
            data=None,
        )

    agent_id = resolve_case_agent(body.agent_id)
    if agent_id is None:
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail=(
                f"Invalid agent_id {body.agent_id!r}. "
                f"Allowed: {', '.join(sorted(ALLOWED_CASE_AGENTS))}"
            ),
            data=None,
        )

    try:
        dataset_path = _case_dataset()
        task_ids = _list_task_ids(dataset_path)
        task_id = task_id_for_patient(patient_id, task_ids)
    except Exception as exc:
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail=f"Case setup failed: {exc}",
            data=None,
        )

    async with _lock_for(patient_id, agent_id):
        if not body.force:
            cached = _read_cache(patient_id, agent_id)
            if cached:
                env = _envelope_from_experiment(
                    str(cached["experiment_id"]),
                    agent_id=str(cached.get("agent_id") or agent_id),
                    task_id=str(cached.get("task_id") or task_id),
                    patient=patient,
                    cached=True,
                )
                if env.ok:
                    return env
                # Failed cached run — drop cache and re-run
                _delete_cache(patient_id, agent_id)

        try:
            experiment_id = await _run_case_experiment(
                patient=patient,
                task_id=task_id,
                agent_id=agent_id,
                dataset_path=dataset_path,
            )
        except Exception as exc:
            return FacadeEnvelope(
                ok=False,
                status="insufficient_data",
                experiment_id=None,
                detail=f"Case experiment failed: {exc}",
                data={
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "patient": patient.model_dump(),
                },
            )

        env = _envelope_from_experiment(
            experiment_id,
            agent_id=agent_id,
            task_id=task_id,
            patient=patient,
            cached=False,
        )
        if env.ok:
            _write_cache(
                patient_id,
                agent_id,
                {
                    "patient_id": patient_id,
                    "experiment_id": experiment_id,
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )
        else:
            _delete_cache(patient_id, agent_id)
        return env
