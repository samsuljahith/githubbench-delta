/** Session storage for synthetic patients (fixtures preferred; Gemini optional). */

import type { ScenarioType, SyntheticPatient, Turn } from "@/lib/demo-data";

const KEY = "elderwise_synthetic_cohort_v1";

export type StoredPatient = SyntheticPatient & {
  source?: "fixture" | "gemini" | "fallback";
  /** ISO timestamp when this patient was loaded/generated in the browser. */
  generatedAt?: string;
  batchId?: string;
};

type Cohort = {
  batchId?: string;
  patients: StoredPatient[];
  updatedAt: string;
};

function read(): Cohort {
  if (typeof sessionStorage === "undefined") {
    return { patients: [], updatedAt: "" };
  }
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return { patients: [], updatedAt: "" };
    const parsed = JSON.parse(raw) as Cohort;
    if (!parsed || !Array.isArray(parsed.patients)) return { patients: [], updatedAt: "" };
    return parsed;
  } catch {
    return { patients: [], updatedAt: "" };
  }
}

function write(cohort: Cohort): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(cohort));
}

export function getSyntheticCohort(): StoredPatient[] {
  return read().patients;
}

export function getSyntheticPatient(id?: string | null): StoredPatient | undefined {
  if (!id) return undefined;
  return read().patients.find((p) => p.id === id);
}

/** Replace the entire cohort (rare). Prefer appendSyntheticCohort for generate. */
export function saveSyntheticCohort(patients: StoredPatient[], batchId?: string): void {
  write({
    batchId,
    patients,
    updatedAt: new Date().toISOString(),
  });
}

/**
 * Merge new patients onto the existing cohort (3→6→9…).
 * Dedupes by id (newer wins). Newest patients are prepended.
 */
export function appendSyntheticCohort(patients: StoredPatient[], batchId?: string): void {
  const cohort = read();
  const byId = new Map<string, StoredPatient>();
  for (const p of cohort.patients) byId.set(p.id, p);
  for (const p of patients) {
    byId.set(p.id, { ...p, batchId: p.batchId || batchId });
  }
  // Preserve relative order: existing first (stable), then new ids that weren't present.
  const existingIds = new Set(cohort.patients.map((p) => p.id));
  const added = patients.filter((p) => !existingIds.has(p.id));
  const updatedExisting = cohort.patients.map((p) => byId.get(p.id)!);
  write({
    batchId: batchId || cohort.batchId,
    patients: [...added, ...updatedExisting],
    updatedAt: new Date().toISOString(),
  });
}

export function upsertSyntheticPatient(patient: StoredPatient): void {
  const cohort = read();
  const idx = cohort.patients.findIndex((p) => p.id === patient.id);
  if (idx >= 0) cohort.patients[idx] = patient;
  else cohort.patients.unshift(patient);
  cohort.updatedAt = new Date().toISOString();
  write(cohort);
}

/** Local calendar day key YYYY-MM-DD from ISO or Date. */
export function localDateKey(isoOrDate?: string | Date | null): string {
  const d = isoOrDate ? new Date(isoOrDate) : new Date();
  if (Number.isNaN(d.getTime())) {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  }
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Display DD/MM/YYYY from YYYY-MM-DD. */
export function formatDateKeyDisplay(dateKey: string): string {
  const [y, m, d] = dateKey.split("-");
  if (!y || !m || !d) return dateKey;
  return `${d}/${m}/${y}`;
}

export function groupCohortByDate(patients: StoredPatient[]): { dateKey: string; patients: StoredPatient[] }[] {
  const map = new Map<string, StoredPatient[]>();
  for (const p of patients) {
    const key = localDateKey(p.generatedAt);
    const list = map.get(key) || [];
    list.push(p);
    map.set(key, list);
  }
  return [...map.entries()]
    .sort(([a], [b]) => (a < b ? 1 : a > b ? -1 : 0))
    .map(([dateKey, rows]) => ({ dateKey, patients: rows }));
}

/** Map API snake_case patient → UI SyntheticPatient (fixtures or Gemini). */
export function apiPatientToUi(
  raw: {
    id: string;
    name?: string | null;
    age?: number | null;
    sex?: string | null;
    chief_complaint?: string | null;
    comorbidities?: string[];
    medications?: string[];
    living_situation?: string | null;
    risk_profile?: string | null;
    scenario_type?: string | null;
    conversation?: { role?: string; text?: string; t?: string }[];
    conversation_text?: string | null;
  },
  opts?: { batchId?: string; generatedAt?: string; source?: StoredPatient["source"] },
): StoredPatient {
  const sex = (raw.sex || "F").toUpperCase().startsWith("M") ? "M" : "F";
  const riskRaw = (raw.risk_profile || "Moderate").toString();
  const riskProfile =
    riskRaw === "Low" || riskRaw === "High" || riskRaw === "Moderate" ? riskRaw : "Moderate";
  const scenarioTypes: ScenarioType[] = [
    "complete",
    "missing_finding",
    "hallucination_risk",
    "contraindication",
    "incomplete",
  ];
  const scenarioType =
    typeof raw.scenario_type === "string" &&
    (scenarioTypes as string[]).includes(raw.scenario_type)
      ? (raw.scenario_type as ScenarioType)
      : undefined;
  const conversation: Turn[] | undefined = raw.conversation?.length
    ? raw.conversation.map((t, i) => ({
        role:
          t.role === "clinician" || t.role === "assistant" || t.role === "patient"
            ? t.role
            : "patient",
        text: String(t.text || ""),
        t: t.t || `00:${String(i * 10).padStart(2, "0")}`,
      }))
    : undefined;
  return {
    id: raw.id,
    name: raw.name || raw.id,
    age: typeof raw.age === "number" ? raw.age : 75,
    sex,
    chiefComplaint: raw.chief_complaint || "Synthetic case",
    comorbidities: raw.comorbidities || [],
    medications: raw.medications || [],
    livingSituation: raw.living_situation || "Unknown",
    riskProfile,
    source: opts?.source || "gemini",
    generatedAt: opts?.generatedAt || new Date().toISOString(),
    batchId: opts?.batchId,
    scenarioType,
    conversation,
    conversationText: raw.conversation_text || undefined,
  };
}
