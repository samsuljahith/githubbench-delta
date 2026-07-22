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


class GeneratePatientsRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=5)


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
    prompt = (
        "Generate exactly "
        f"{count} fully synthetic geriatric patient cases for a privacy-safe Singapore demo. "
        "No real people or PHI. Use diverse Singaporean-style names "
        "(Chinese, Malay, Indian, Eurasian given names + family names — fictional only). "
        "Each patient must have a distinct chief complaint and comorbidity set "
        "(e.g. falls, T2DM, CKD, atrial fibrillation, COPD, mild dementia, heart failure, "
        "osteoarthritis, depression after bereavement — do not repeat profiles in this batch). "
        "Ages 68-92, mixed sex. Living situations appropriate to Singapore "
        "(HDB flat alone, with adult children, assisted living, etc.). "
        "Return JSON only with shape: "
        '{"patients":[{"id":"SYN-G-xxxx","name":"...","age":82,"sex":"F",'
        '"chief_complaint":"...","comorbidities":["..."],"medications":["..."],'
        '"living_situation":"...","risk_profile":"High|Moderate|Low"}]}.'
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "responseMimeType": "application/json",
        },
    }
    own = client is None
    http = client or httpx.Client(timeout=60.0)
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


def persist_batch(patients: list[GeneratedPatient]) -> str:
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    path = _synthetic_dir() / f"{batch_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "batch_id": batch_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "gemini",
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
    try:
        fn = gemini_fn or call_gemini_generate_patients
        patients = fn(count=count)
    except Exception as exc:
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail=f"Synthetic generation failed: {exc}",
            data=None,
        )
    try:
        batch_id = persist_batch(patients)
    except Exception as exc:  # pragma: no cover
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=None,
            detail=f"Could not persist synthetic batch: {exc}",
            data=None,
        )
    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=None,
        detail=None,
        data={
            "batch_id": batch_id,
            "patients": [p.model_dump() for p in patients],
            "source": "gemini",
            "provenance": (
                "Patients generated by Gemini for privacy-safe demo chrome only. "
                "Not used for scoring. Live assessment uses the selected coding agent."
            ),
        },
    )
