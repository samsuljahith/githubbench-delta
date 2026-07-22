"""Gemini-powered synthetic patient generation (chrome only — not an evaluator)."""

from __future__ import annotations

import json
import os
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from githubbench_delta.api.facade import FacadeEnvelope
from githubbench_delta.core.config import load_config

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

SCENARIO_TYPES: tuple[str, ...] = (
    "complete",
    "missing_finding",
    "hallucination_risk",
    "contraindication",
    "incomplete",
)


class GeneratedPatient(BaseModel):
    id: str = Field(..., min_length=1)
    name: str | None = None
    age: int | None = None
    sex: str | None = None
    chief_complaint: str | None = None
    comorbidities: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    living_situation: str | None = None
    risk_profile: str | None = None
    scenario_type: str | None = None
    conversation_text: str | None = None
    conversation: list[dict[str, Any]] = Field(default_factory=list)


class GeneratePatientsRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=5)


GeminiGenerateFn = Callable[..., list[GeneratedPatient]]


def _gemini_api_key() -> str:
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if key:
        return key
    try:
        env = load_config().env
        return (env.gemini_api_key or "").strip()
    except Exception:
        return ""


def _gemini_model() -> str:
    model = (os.environ.get("GEMINI_MODEL") or "").strip()
    if not model:
        try:
            model = (load_config().env.gemini_model or "").strip()
        except Exception:
            model = ""
    return model or "gemini-2.5-flash"


def _synthetic_dir() -> Path:
    cfg = load_config()
    return Path(cfg.runtime.pipeline.results_dir).resolve().parent / "synthetic"


def _normalize_scenario(raw: Any) -> str | None:
    val = str(raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    if val in SCENARIO_TYPES:
        return val
    return None


def _normalize_conversation(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for i, turn in enumerate(raw):
        if not isinstance(turn, dict):
            continue
        text = str(turn.get("text") or turn.get("content") or "").strip()
        if not text:
            continue
        role = str(turn.get("role") or "patient").strip().lower()
        if role not in {"assistant", "patient", "clinician", "caregiver"}:
            role = "patient"
        out.append(
            {
                "role": role,
                "text": text,
                "t": str(turn.get("t") or f"00:{i * 10:02d}"),
            }
        )
    return out


def _normalize_patient(raw: dict[str, Any], *, index: int) -> GeneratedPatient:
    short = uuid.uuid4().hex[:8]
    pid = str(raw.get("id") or "").strip() or f"SYN-G-{short}"
    pid = _SAFE.sub("-", pid)[:32]
    sex = str(raw.get("sex") or "F").strip().upper()[:1]
    if sex not in {"F", "M"}:
        sex = "F"
    risk = str(raw.get("risk_profile") or raw.get("riskProfile") or "Moderate").strip().title()
    if risk not in {"Low", "Moderate", "High"}:
        risk = "Moderate"
    age_raw = raw.get("age")
    try:
        age = int(age_raw) if age_raw is not None else 75 + index
    except (TypeError, ValueError):
        age = 75 + index
    age = max(65, min(100, age))

    def _list(val: Any) -> list[str]:
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            return [p.strip() for p in val.split(",") if p.strip()]
        return []

    conversation_text = (
        str(raw.get("conversation_text") or raw.get("conversationText") or "").strip() or None
    )
    conversation = _normalize_conversation(raw.get("conversation"))
    scenario = _normalize_scenario(raw.get("scenario_type") or raw.get("scenarioType"))

    return GeneratedPatient(
        id=pid,
        name=str(raw.get("name") or f"Synthetic Patient {index + 1}").strip(),
        age=age,
        sex=sex,
        chief_complaint=str(
            raw.get("chief_complaint") or raw.get("chiefComplaint") or "General geriatric check-in"
        ).strip(),
        comorbidities=_list(raw.get("comorbidities")),
        medications=_list(raw.get("medications")),
        living_situation=str(
            raw.get("living_situation") or raw.get("livingSituation") or "Lives alone"
        ).strip(),
        risk_profile=risk,
        scenario_type=scenario,
        conversation_text=conversation_text,
        conversation=conversation,
    )


def _parse_gemini_patients(text: str, *, count: int) -> list[GeneratedPatient]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if isinstance(data, dict) and "patients" in data:
        rows = data["patients"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError("Gemini response must be a JSON array or {patients: [...]}")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Gemini returned no patients")
    out: list[GeneratedPatient] = []
    for i, row in enumerate(rows[:count]):
        if not isinstance(row, dict):
            continue
        out.append(_normalize_patient(row, index=i))
    if not out:
        raise ValueError("Could not parse any patient objects from Gemini")
    seen: set[str] = set()
    for i, p in enumerate(out):
        base = p.id
        while p.id in seen:
            p = GeneratedPatient(**{**p.model_dump(), "id": f"{base}-{i}-{uuid.uuid4().hex[:4]}"})
            out[i] = p
        seen.add(p.id)
    return out


def _build_gemini_prompt(count: int) -> str:
    scenario_mix = ""
    if count == 5:
        scenario_mix = (
            "CRITICAL: Across the 5 patients you MUST assign exactly one of each "
            "scenario_type (no duplicates, no missing): complete, missing_finding, "
            "hallucination_risk, contraindication, incomplete. "
            "Structural intent for conversation_text by scenario_type — "
            "RGA domains are frailty/fatigue, sarcopenia/muscle weakness or mobility difficulty, "
            "appetite or weight change, and memory/cognition: "
            "(1) complete — clearly cover all 4 RGA domains with clean extractable detail; "
            "(2) missing_finding — cover other domains but bury a fall or near-fall casually "
            "mid-sentence inside an unrelated anecdote; "
            "(3) hallucination_risk — caregiver is vague/uncertain about a medication name "
            "(must not invent a specific drug — say they do not remember); "
            "(4) contraindication — patient age 80+ currently taking a benzodiazepine or other "
            "Beers-Criteria medication (invent which and why), rest otherwise complete; "
            "(5) incomplete — naturally discuss only 2 of the 4 RGA domains; omit the other two. "
        )
    else:
        scenario_mix = (
            "Assign each patient a scenario_type from: complete | missing_finding | "
            "hallucination_risk | contraindication | incomplete. Prefer diversity. "
        )

    return (
        "Generate exactly "
        f"{count} fully synthetic geriatric patient cases for a privacy-safe Singapore demo. "
        "No real people or PHI. Invent fresh names, ages, and details every call — "
        "never reuse prior outputs. Use diverse Singaporean-style names "
        "(Chinese, Malay, Indian, Eurasian — fictional only). "
        "Each patient must have a distinct chief complaint and comorbidity set. "
        "Ages 68-92, mixed sex. Living situations appropriate to Singapore "
        "(HDB flat alone, with adult children, assisted living, etc.). "
        f"{scenario_mix}"
        "For EVERY patient include conversation_text: a 150-250 word natural "
        "caregiver-to-care-coordinator conversation transcript (spoken tone, not bullet lists). "
        "Return JSON only with shape: "
        '{"patients":[{"id":"SYN-G-xxxx","name":"...","age":82,"sex":"F",'
        '"chief_complaint":"...","comorbidities":["..."],"medications":["..."],'
        '"living_situation":"...","risk_profile":"High|Moderate|Low",'
        '"scenario_type":"complete|missing_finding|hallucination_risk|contraindication|incomplete",'
        '"conversation_text":"...150-250 words..."}]}.'
    )


def call_gemini_generate_patients(
    *,
    count: int,
    client: httpx.Client | None = None,
) -> list[GeneratedPatient]:
    """Call Gemini REST API; injectable client for tests."""

    api_key = _gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    model = _gemini_model()
    prompt = _build_gemini_prompt(count)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.95,
            "responseMimeType": "application/json",
        },
    }
    own = client is None
    http = client or httpx.Client(timeout=90.0)
    try:
        resp = http.post(url, params={"key": api_key}, json=body)
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if own:
            http.close()

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {payload}")
    parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
    text = "".join(str(p.get("text") or "") for p in parts if isinstance(p, dict))
    if not text.strip():
        raise RuntimeError("Gemini returned empty content")
    return _parse_gemini_patients(text, count=count)


def load_fixture_patients_as_generated() -> list[GeneratedPatient]:
    """Map datasets/synthetic fixtures into GeneratedPatient (offline fallback)."""

    from githubbench_delta.api.cases import load_synthetic_fixtures

    fixtures = load_synthetic_fixtures()
    if not fixtures:
        raise RuntimeError("no synthetic fixtures available under datasets/synthetic/")
    out: list[GeneratedPatient] = []
    for i, fx in enumerate(fixtures):
        nested = dict(fx.get("patient") or {})
        merged: dict[str, Any] = {
            **nested,
            "id": fx.get("id") or nested.get("id"),
            "name": fx.get("name") or nested.get("name"),
            "scenario_type": fx.get("scenario_type"),
            "conversation_text": fx.get("conversation_text"),
            "conversation": fx.get("conversation") or [],
        }
        out.append(_normalize_patient(merged, index=i))
    return out


def persist_batch(patients: list[GeneratedPatient], *, source: str = "gemini") -> str:
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    path = _synthetic_dir() / f"{batch_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": source,
                "patients": [p.model_dump() for p in patients],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return batch_id


def generate_patients_envelope(
    body: GeneratePatientsRequest,
    *,
    gemini_fn: GeminiGenerateFn | None = None,
) -> FacadeEnvelope:
    count = max(1, min(5, int(body.count)))
    source = "gemini"
    detail_note: str | None = None
    try:
        fn = gemini_fn or call_gemini_generate_patients
        patients = fn(count=count)
    except Exception as exc:
        # Offline / CI fallback: versioned fixtures
        try:
            patients = load_fixture_patients_as_generated()
            if count < len(patients):
                patients = patients[:count]
            source = "fixture_fallback"
            detail_note = f"Gemini unavailable ({exc}); served datasets/synthetic fixtures instead."
        except Exception as fixture_exc:
            return FacadeEnvelope(
                ok=False,
                status="insufficient_data",
                experiment_id=None,
                detail=(
                    f"Synthetic generation failed: {exc}; "
                    f"fixture fallback also failed: {fixture_exc}"
                ),
                data=None,
            )
    try:
        batch_id = persist_batch(patients, source=source)
    except Exception as exc:  # pragma: no cover
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail=f"Could not persist synthetic batch: {exc}",
            data=None,
        )
    provenance = (
        "Patients from datasets/synthetic fixtures (Gemini unavailable). "
        "Demo chrome only — not used for scoring."
        if source == "fixture_fallback"
        else (
            "Patients generated by Gemini for privacy-safe demo chrome only. "
            "Not used for scoring. Live assessment uses the selected coding agent."
        )
    )
    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=None,
        detail=detail_note,
        data={
            "batch_id": batch_id,
            "patients": [p.model_dump() for p in patients],
            "source": source,
            "provenance": provenance,
        },
    )
