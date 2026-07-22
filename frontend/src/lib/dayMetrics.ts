/** Day-level live metric aggregates (sessionStorage). Never fabricates scores. */

import { patientToCasePayload, postCaseRun, type EvalMetric } from "@/lib/api";
import { formatDateKeyDisplay, type StoredPatient } from "@/lib/syntheticStore";

const KEY = "elderwise_day_metrics_v1";

export type DayMetricSnapshot = {
  agentId: string;
  dateKey: string;
  evaluatedAt: string;
  patientCount: number;
  okCount: number;
  failCount: number;
  meanTrust: number | null;
  meanMetrics: { key: string; label: string; value: number; unit: string }[];
  perPatient: {
    patientId: string;
    ok: boolean;
    trust?: number;
    detail?: string;
  }[];
};

type Store = {
  days: Record<string, DayMetricSnapshot>;
};

function storageKey(agentId: string, dateKey: string): string {
  return `${agentId}::${dateKey}`;
}

function readStore(): Store {
  if (typeof sessionStorage === "undefined") return { days: {} };
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return { days: {} };
    const parsed = JSON.parse(raw) as Store;
    if (!parsed || typeof parsed.days !== "object") return { days: {} };
    return parsed;
  } catch {
    return { days: {} };
  }
}

function writeStore(store: Store): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(KEY, JSON.stringify(store));
}

export function getDayMetrics(agentId: string, dateKey: string): DayMetricSnapshot | undefined {
  return readStore().days[storageKey(agentId, dateKey)];
}

export function listDayMetricsForAgent(agentId: string): DayMetricSnapshot[] {
  const store = readStore();
  return Object.values(store.days)
    .filter((d) => d.agentId === agentId)
    .sort((a, b) => (a.dateKey < b.dateKey ? 1 : -1));
}

export function saveDayMetrics(snap: DayMetricSnapshot): void {
  const store = readStore();
  store.days[storageKey(snap.agentId, snap.dateKey)] = snap;
  writeStore(store);
}

function mean(nums: number[]): number | null {
  if (!nums.length) return null;
  return Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10;
}

function aggregateMetrics(metricLists: EvalMetric[][]): DayMetricSnapshot["meanMetrics"] {
  const buckets = new Map<string, { label: string; unit: string; values: number[] }>();
  for (const list of metricLists) {
    for (const m of list) {
      const b = buckets.get(m.key) || { label: m.label, unit: m.unit, values: [] };
      b.values.push(m.value);
      buckets.set(m.key, b);
    }
  }
  return [...buckets.entries()].map(([key, b]) => ({
    key,
    label: b.label,
    unit: b.unit,
    value: mean(b.values) ?? 0,
  }));
}

export type DayEvalProgress = {
  done: number;
  total: number;
  currentPatientId?: string;
};

/**
 * Run live case evaluation for each patient on a day (prefer cache).
 * Aggregates only successful live payloads — never invents scores.
 */
export async function evaluateDayPatients(
  patients: StoredPatient[],
  agentId: string,
  dateKey: string,
  opts?: {
    force?: boolean;
    onProgress?: (p: DayEvalProgress) => void;
  },
): Promise<DayMetricSnapshot> {
  const force = opts?.force ?? false;
  const trusts: number[] = [];
  const metricLists: EvalMetric[][] = [];
  const perPatient: DayMetricSnapshot["perPatient"] = [];
  let okCount = 0;
  let failCount = 0;

  for (let i = 0; i < patients.length; i++) {
    const p = patients[i];
    opts?.onProgress?.({ done: i, total: patients.length, currentPatientId: p.id });
    try {
      const env = await postCaseRun(patientToCasePayload(p), { agentId, force });
      if (!env.ok || !env.data?.trust || !env.data.evaluate?.metrics?.length) {
        failCount += 1;
        perPatient.push({
          patientId: p.id,
          ok: false,
          detail: env.detail || "insufficient_data",
        });
        continue;
      }
      okCount += 1;
      trusts.push(env.data.trust.overall);
      metricLists.push(env.data.evaluate.metrics);
      perPatient.push({
        patientId: p.id,
        ok: true,
        trust: env.data.trust.overall,
      });
    } catch (err: unknown) {
      failCount += 1;
      perPatient.push({
        patientId: p.id,
        ok: false,
        detail: err instanceof Error ? err.message : "Request failed",
      });
    }
  }

  opts?.onProgress?.({ done: patients.length, total: patients.length });

  const snap: DayMetricSnapshot = {
    agentId,
    dateKey,
    evaluatedAt: new Date().toISOString(),
    patientCount: patients.length,
    okCount,
    failCount,
    meanTrust: mean(trusts),
    meanMetrics: aggregateMetrics(metricLists),
    perPatient,
  };
  saveDayMetrics(snap);
  return snap;
}

export type DayCompare = {
  dayA: DayMetricSnapshot;
  dayB: DayMetricSnapshot;
  trustDelta: number | null;
  sentence: string;
};

export function compareDayMetrics(dayA: DayMetricSnapshot, dayB: DayMetricSnapshot): DayCompare {
  const a = dayA.meanTrust;
  const b = dayB.meanTrust;
  let trustDelta: number | null = null;
  let sentence: string;
  if (a == null || b == null) {
    sentence =
      "Need successful live TrustScores on both days before comparing — evaluate each day first.";
  } else {
    trustDelta = Math.round((b - a) * 10) / 10;
    if (trustDelta > 0) {
      sentence = `${formatDateKeyDisplay(dayB.dateKey)} performed better than ${formatDateKeyDisplay(dayA.dateKey)}: mean TrustScore +${trustDelta} (${b} vs ${a}).`;
    } else if (trustDelta < 0) {
      sentence = `${formatDateKeyDisplay(dayB.dateKey)} scored lower than ${formatDateKeyDisplay(dayA.dateKey)}: mean TrustScore ${trustDelta} (${b} vs ${a}).`;
    } else {
      sentence = `${formatDateKeyDisplay(dayB.dateKey)} and ${formatDateKeyDisplay(dayA.dateKey)} have the same mean TrustScore (${a}).`;
    }
  }
  return { dayA, dayB, trustDelta, sentence };
}
