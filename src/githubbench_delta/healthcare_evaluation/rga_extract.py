"""LLM extraction of Rapid Geriatric Assessment fields from conversation transcript."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from githubbench_delta.healthcare_evaluation.models import (
    REQUIRED_RGA_FIELDS,
    ClinicalOutput,
    field_has_value,
)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


@dataclass(frozen=True)
class LlmEndpoint:
    provider: str  # "openai" | "minicpm"
    api_key: str
    base_url: str | None
    model: str


@dataclass
class ExtractResult:
    clinical_output: ClinicalOutput
    raw_text: str
    provider: str
    model: str
    detail: str | None = None
    ok: bool = True


def resolve_llm_endpoint() -> LlmEndpoint | None:
    """OpenAI if key set; else local MiniCPM OpenAI-compatible; else None."""

    openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip() or _env_from_config(
        "openai_api_key"
    )
    model_override = (os.environ.get("HEALTHCARE_ASSESS_MODEL") or "").strip()

    if openai_key:
        return LlmEndpoint(
            provider="openai",
            api_key=openai_key,
            base_url=None,
            model=model_override or "gpt-4o-mini",
        )

    base = (os.environ.get("MINICPM_BASE_URL") or "").strip() or _env_from_config(
        "minicpm_base_url"
    )
    if not base:
        return None

    key = (
        (os.environ.get("MINICPM_API_KEY") or "").strip()
        or _env_from_config("minicpm_api_key")
        or "ollama"
    )
    model = (
        model_override
        or (os.environ.get("MINICPM_MODEL") or "").strip()
        or _env_from_config("minicpm_model")
        or "minicpm"
    )
    return LlmEndpoint(
        provider="minicpm",
        api_key=key or "ollama",
        base_url=base,
        model=model,
    )


def _env_from_config(attr: str) -> str:
    try:
        from githubbench_delta.core.config import load_config

        env = load_config().env
        val = getattr(env, attr, None)
        return (val or "").strip() if isinstance(val, str) else ""
    except Exception:
        return ""


def build_rga_prompt(transcript: str) -> list[dict[str, str]]:
    fields_list = ", ".join(REQUIRED_RGA_FIELDS)
    system = (
        "You are a clinical documentation assistant. Extract a Rapid Geriatric Assessment "
        "(RGA) from the conversation transcript. Return ONLY valid JSON with keys: "
        f'"fields" (object with keys among: {fields_list}) and optional "narrative" (string). '
        "Use only information supported by the transcript. "
        "If a domain is not discussed, omit that key or use an empty string — never invent "
        "clinical findings, diagnoses, or scores. Not a substitute for clinician judgment."
    )
    user = (
        "Extract structured RGA fields from this transcript:\n\n"
        f"{transcript.strip()}\n\n"
        "Respond with JSON only."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_rga_json(raw_text: str) -> ClinicalOutput:
    """Parse model JSON into ClinicalOutput; keep only known RGA keys with values."""

    text = (raw_text or "").strip()
    if not text:
        return ClinicalOutput()

    data: dict[str, Any] | None = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = None

    if not isinstance(data, dict):
        return ClinicalOutput()

    raw_fields = data.get("fields")
    if not isinstance(raw_fields, dict):
        # Allow flat RGA keys at top level
        raw_fields = {k: data[k] for k in REQUIRED_RGA_FIELDS if k in data}

    fields: dict[str, Any] = {}
    for key in REQUIRED_RGA_FIELDS:
        if key not in raw_fields:
            continue
        val = raw_fields[key]
        if field_has_value(val):
            fields[key] = val

    narrative = data.get("narrative")
    if isinstance(narrative, str) and narrative.strip():
        narrative_out: str | None = narrative.strip()
    else:
        narrative_out = None

    return ClinicalOutput(fields=fields, narrative=narrative_out)


def call_chat_completions(
    endpoint: LlmEndpoint,
    messages: list[dict[str, str]],
    *,
    timeout_s: float = 90.0,
) -> str:
    """Sync chat.completions call (OpenAI or OpenAI-compatible)."""

    from openai import OpenAI

    kwargs: dict[str, Any] = {"api_key": endpoint.api_key}
    if endpoint.base_url:
        kwargs["base_url"] = endpoint.base_url
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=endpoint.model,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.2,
        max_tokens=2048,
        timeout=timeout_s,
    )
    content = resp.choices[0].message.content if resp.choices else None
    return (content or "").strip()


def extract_rga_from_transcript(
    transcript: str,
    *,
    llm_call: Any | None = None,
    endpoint: LlmEndpoint | None = None,
) -> ExtractResult:
    """
    Extract RGA ClinicalOutput from transcript via LLM.

    llm_call: optional injectable (messages, endpoint) -> str for tests.
    """

    text = (transcript or "").strip()
    if not text:
        return ExtractResult(
            clinical_output=ClinicalOutput(),
            raw_text="",
            provider="",
            model="",
            detail="insufficient_data: empty transcript — cannot extract RGA",
            ok=False,
        )

    ep = endpoint if endpoint is not None else resolve_llm_endpoint()
    if ep is None:
        return ExtractResult(
            clinical_output=ClinicalOutput(),
            raw_text="",
            provider="",
            model="",
            detail=(
                "insufficient_data: no LLM configured for healthcare assess "
                "(set OPENAI_API_KEY or MINICPM_BASE_URL)"
            ),
            ok=False,
        )

    messages = build_rga_prompt(text)
    call_fn = llm_call or (lambda msgs, e=ep: call_chat_completions(e, msgs))
    try:
        raw = call_fn(messages)
    except Exception as exc:  # noqa: BLE001
        return ExtractResult(
            clinical_output=ClinicalOutput(),
            raw_text="",
            provider=ep.provider,
            model=ep.model,
            detail=f"insufficient_data: RGA LLM call failed: {exc}",
            ok=False,
        )

    clinical = parse_rga_json(raw)
    if not clinical.fields and not (clinical.narrative and clinical.narrative.strip()):
        return ExtractResult(
            clinical_output=clinical,
            raw_text=raw,
            provider=ep.provider,
            model=ep.model,
            detail=(
                "insufficient_data: LLM returned no extractable RGA fields "
                "(incomplete output — not fabricated)"
            ),
            ok=False,
        )

    return ExtractResult(
        clinical_output=clinical,
        raw_text=raw,
        provider=ep.provider,
        model=ep.model,
        detail=None,
        ok=True,
    )
