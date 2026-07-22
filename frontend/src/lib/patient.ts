/** Shared setup search-param helpers (agent + patient). */

import type { SyntheticPatient } from "@/lib/demo-data";
import { getSyntheticPatient } from "@/lib/syntheticStore";

export const ALLOWED_AGENTS = ["minicpm", "claude", "codex"] as const;
export type AllowedAgent = (typeof ALLOWED_AGENTS)[number];

export type SetupSearch = {
  agent?: AllowedAgent;
  patient?: string;
};

/** @deprecated Use SetupSearch */
export type PatientSearch = SetupSearch;

export function isAllowedAgent(value: unknown): value is AllowedAgent {
  return typeof value === "string" && (ALLOWED_AGENTS as readonly string[]).includes(value);
}

export function parseSetupSearch(search: Record<string, unknown>): SetupSearch {
  const out: SetupSearch = {};
  if (isAllowedAgent(search.agent)) {
    out.agent = search.agent;
  }
  if (typeof search.patient === "string" && search.patient.trim()) {
    out.patient = search.patient.trim();
  }
  return out;
}

/** @deprecated Use parseSetupSearch */
export const parsePatientSearch = parseSetupSearch;

/** Agent + Gemini patient id present in URL (patient may still be missing from store). */
export function isSetupComplete(search: SetupSearch): boolean {
  return Boolean(search.agent && search.patient);
}

/** True when the URL patient exists in the Gemini session cohort. */
export function hasGeminiPatient(search: SetupSearch): boolean {
  return Boolean(search.patient && getSyntheticPatient(search.patient));
}

/** Gemini session cohort only — never falls back to hardcoded demo patients. */
export function patientFromSearch(search: SetupSearch): SyntheticPatient | null {
  return getSyntheticPatient(search.patient) ?? null;
}

export function agentFromSearch(search: SetupSearch): AllowedAgent | undefined {
  return search.agent;
}

export function setupSearchLink(opts: {
  agent?: string | null;
  patient?: string | null;
}): SetupSearch {
  const out: SetupSearch = {};
  if (isAllowedAgent(opts.agent)) out.agent = opts.agent;
  if (opts.patient && opts.patient.trim()) out.patient = opts.patient.trim();
  return out;
}

/** Preserve agent when linking with a patient id. */
export function patientSearchLink(patientId: string, agent?: string | null): SetupSearch {
  return setupSearchLink({ agent, patient: patientId });
}

/** Dashboard section hashes for in-page navigation. */
export const DASHBOARD_SECTIONS = [
  { id: "conversation", label: "Conversation" },
  { id: "assessment", label: "Assessment" },
  { id: "evaluation", label: "Engineering" },
  { id: "healthcare", label: "Healthcare" },
  { id: "trust", label: "TrustScore" },
  { id: "benchmark", label: "Benchmark" },
  { id: "insights", label: "Research Insights" },
] as const;

export type DashboardSectionId = (typeof DASHBOARD_SECTIONS)[number]["id"];
