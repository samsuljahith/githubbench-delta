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
