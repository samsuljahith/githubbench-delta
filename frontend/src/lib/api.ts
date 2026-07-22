/** Thin client for GitHubBench-Delta facade APIs. No business logic. */

export type FacadeStatus = "ok" | "insufficient_data";

export type FacadeEnvelope<T = Record<string, unknown>> = {
  ok: boolean;
  status: FacadeStatus;
  experiment_id?: string | null;
  detail?: string | null;
  data: T | null;
};

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

const DEFAULT_BASE = "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 30_000;

export function apiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || DEFAULT_BASE;
}

export function defaultExperimentId(): string {
  return (
    (import.meta.env.VITE_DEFAULT_EXPERIMENT_ID as string | undefined)?.trim() ||
    "exp_6afa2ce533ba4e0a"
  );
}

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = init ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${apiBaseUrl()}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(rest.body ? { "Content-Type": "application/json" } : {}),
        ...rest.headers,
      },
    });
    const text = await res.text();
    let json: unknown = null;
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        json = text;
      }
    }
    if (!res.ok) {
      const detail =
        typeof json === "object" && json && "detail" in json
          ? String((json as { detail: unknown }).detail)
          : res.statusText;
      throw new ApiError(detail || `HTTP ${res.status}`, res.status, json);
    }
    return json as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out", 408);
    }
    throw new ApiError(err instanceof Error ? err.message : "Network error", 0);
  } finally {
    clearTimeout(timer);
  }
}

export type AssessmentDomain = {
  domain: string;
  score: number;
  max: number;
  flag: "normal" | "watch" | "concern";
  note: string;
};

export type AssessmentData = {
  domains: AssessmentDomain[];
  subject: {
    id: string;
    name: string;
    agents?: string[];
    title?: string;
    synthetic?: boolean;
    source?: string;
  };
  method?: string;
};

export type EvalMetric = {
  key: string;
  label: string;
  value: number;
  target: number;
  unit: "%" | "score";
  description: string;
};

export type EvaluateData = {
  metrics: EvalMetric[];
  n_rows: number;
  agent_id?: string | null;
  source?: string;
};

export type TrustData = {
  overall: number;
  band: string;
  breakdown: { name: string; value: number }[];
  method?: string;
  n_rows?: number;
  agent_id?: string | null;
};

export type HealthResponse = { status: string; version: string };

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function postAssessment(experimentId?: string, agentId?: string) {
  return request<FacadeEnvelope<AssessmentData>>("/assessment", {
    method: "POST",
    body: JSON.stringify({
      experiment_id: experimentId ?? defaultExperimentId(),
      agent_id: agentId ?? null,
    }),
  });
}

export function postEvaluate(experimentId?: string, agentId?: string) {
  return request<FacadeEnvelope<EvaluateData>>("/evaluate", {
    method: "POST",
    body: JSON.stringify({
      experiment_id: experimentId ?? defaultExperimentId(),
      agent_id: agentId ?? null,
    }),
  });
}

export function postTrust(experimentId?: string, agentId?: string) {
  return request<FacadeEnvelope<TrustData>>("/trust", {
    method: "POST",
    body: JSON.stringify({
      experiment_id: experimentId ?? defaultExperimentId(),
      agent_id: agentId ?? null,
    }),
  });
}

export function postMemorization(experimentIds?: string[], twinsPath?: string) {
  return request<FacadeEnvelope<Record<string, unknown>>>("/memorization", {
    method: "POST",
    body: JSON.stringify({
      experiment_ids: experimentIds ?? [defaultExperimentId()],
      twins_path: twinsPath ?? null,
    }),
  });
}

export type CasePatientPayload = {
  id: string;
  name?: string;
  age?: number;
  sex?: string;
  chief_complaint?: string;
  comorbidities?: string[];
  medications?: string[];
  living_situation?: string;
  risk_profile?: string;
};

export type LoopEngineering = {
  step_count: number;
  tool_call_count: number;
  error_count: number;
  latency_ms: number;
  summary: string;
  related_metrics?: {
    key: string;
    label: string;
    value?: number;
    unit?: string;
  }[];
};

export type CaseRunData = {
  task_id: string;
  agent_id: string;
  cached: boolean;
  patient: CasePatientPayload;
  assessment: AssessmentData;
  evaluate: EvaluateData;
  trust: TrustData;
  loop_engineering?: LoopEngineering;
  provenance?: string;
};

const CASE_RUN_TIMEOUT_MS = 180_000;

export function patientToCasePayload(p: {
  id: string;
  name: string;
  age: number;
  sex: string;
  chiefComplaint: string;
  comorbidities: string[];
  medications: string[];
  livingSituation: string;
  riskProfile: string;
}): CasePatientPayload {
  return {
    id: p.id,
    name: p.name,
    age: p.age,
    sex: p.sex,
    chief_complaint: p.chiefComplaint,
    comorbidities: p.comorbidities,
    medications: p.medications,
    living_situation: p.livingSituation,
    risk_profile: p.riskProfile,
  };
}

export function postCaseRun(
  patient: CasePatientPayload,
  opts?: { force?: boolean; agentId?: string | null },
) {
  return request<FacadeEnvelope<CaseRunData>>("/cases/run", {
    method: "POST",
    timeoutMs: CASE_RUN_TIMEOUT_MS,
    body: JSON.stringify({
      patient,
      agent_id: opts?.agentId ?? null,
      force: opts?.force ?? false,
    }),
  });
}

export type CaseAgentInfo = {
  id: string;
  label: string;
  deployment: "local" | "hosted";
  hint: string;
};

export function getCaseAgents(): Promise<CaseAgentInfo[]> {
  return request<CaseAgentInfo[]>("/cases/agents");
}

export type GeneratePatientsData = {
  batch_id: string;
  patients: CasePatientPayload[];
  source: string;
  provenance?: string;
};

export function postGeneratePatients(count = 3) {
  return request<FacadeEnvelope<GeneratePatientsData>>("/cases/generate-patients", {
    method: "POST",
    timeoutMs: 90_000,
    body: JSON.stringify({ count }),
  });
}

export type FixturePatientRow = CasePatientPayload & {
  scenario_type?: string;
  conversation?: { role?: string; text?: string; t?: string }[];
  conversation_text?: string | null;
};

export type FixturePatientsData = {
  source: string;
  count: number;
  patients: FixturePatientRow[];
};

/** Fixed datasets/synthetic fixtures for reproducible demos. */
export function getFixturePatients() {
  return request<FacadeEnvelope<FixturePatientsData>>("/cases/fixture-patients");
}

/* --- Healthcare Evaluation Layer (clinical evidence; not the 18 engineering metrics) --- */

export type ReviewStatus = "pending" | "approved" | "needs_review";

export type CompletenessResult = {
  present_fields: string[];
  missing_fields: string[];
  completeness_ratio: number | null;
  detail?: string | null;
};

export type CriticalFinding = {
  finding_id: string;
  severity: "warning" | "info";
  evidence_span: string;
  message: string;
};

export type SafetyWarning = {
  rule_id: string;
  message: string;
  evidence_span?: string | null;
};

export type HealthcareReport = {
  report_id: string;
  created_at: string;
  review_status: ReviewStatus;
  patient?: CasePatientPayload | null;
  completeness?: CompletenessResult | null;
  critical_findings: CriticalFinding[];
  safety_warnings: SafetyWarning[];
  provenance?: string;
  insufficient_data: boolean;
  detail?: string | null;
};

export type HealthcareEvaluateData = {
  report_id: string;
  report: HealthcareReport;
  assessment_id?: string;
  assessment?: Record<string, unknown>;
};

export type HealthcareAssessRequest = {
  patient?: CasePatientPayload | null;
  transcript?: string | null;
  conversation?: { role?: string; text?: string; content?: string }[] | null;
};

const HEALTHCARE_ASSESS_TIMEOUT_MS = 120_000;

/** Live LLM RGA extract + evaluate — not patient-chrome placeholders. */
export function postHealthcareAssess(body: HealthcareAssessRequest) {
  return request<FacadeEnvelope<HealthcareEvaluateData>>("/healthcare/assess", {
    method: "POST",
    timeoutMs: HEALTHCARE_ASSESS_TIMEOUT_MS,
    body: JSON.stringify(body),
  });
}

export function getHealthcareReport(reportId: string) {
  return request<FacadeEnvelope<HealthcareEvaluateData>>(
    `/healthcare/report/${encodeURIComponent(reportId)}`,
  );
}
