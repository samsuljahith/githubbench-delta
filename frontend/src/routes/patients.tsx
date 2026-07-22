import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { AppLayout, PageHeader, SyntheticBadge } from "@/components/AppLayout";
import { ErrorBlock, LoadingBlock } from "@/components/ApiStates";
import {
  compareDayMetrics,
  evaluateDayPatients,
  getDayMetrics,
  type DayEvalProgress,
  type DayMetricSnapshot,
} from "@/lib/dayMetrics";
import { parseSetupSearch, patientSearchLink, setupSearchLink } from "@/lib/patient";
import {
  formatDateKeyDisplay,
  getSyntheticCohort,
  groupCohortByDate,
  type StoredPatient,
} from "@/lib/syntheticStore";
import {
  ArrowRight,
  BarChart3,
  GitCompare,
  Play,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

export const Route = createFileRoute("/patients")({
  validateSearch: parseSetupSearch,
  head: () => ({
    meta: [
      { title: "Synthetic Patients · ElderWise" },
      {
        name: "description",
        content:
          "Gemini cohort grouped by day — evaluate all patients for a day and compare day-over-day metrics.",
      },
    ],
  }),
  component: PatientsPage,
});

const riskAccent: Record<string, string> = {
  High: "from-destructive/80 to-destructive/40",
  Moderate: "from-warning/80 to-warning/40",
  Low: "from-success/80 to-success/40",
};

const riskColor: Record<string, string> = {
  High: "text-destructive bg-destructive/10 border-destructive/30",
  Moderate: "text-warning bg-warning/10 border-warning/30",
  Low: "text-success bg-success/10 border-success/30",
};

function PatientsPage() {
  const search = Route.useSearch();
  const selectedId = search.patient;
  const agentId = search.agent;
  const [cohort, setCohort] = useState<StoredPatient[]>([]);
  const [daySnaps, setDaySnaps] = useState<Record<string, DayMetricSnapshot>>({});
  const [evaluatingDate, setEvaluatingDate] = useState<string | null>(null);
  const [progress, setProgress] = useState<DayEvalProgress | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [compareA, setCompareA] = useState<string>("");
  const [compareB, setCompareB] = useState<string>("");

  const refresh = () => {
    const rows = getSyntheticCohort();
    setCohort(rows);
    if (!agentId) {
      setDaySnaps({});
      return;
    }
    const groups = groupCohortByDate(rows);
    const next: Record<string, DayMetricSnapshot> = {};
    for (const g of groups) {
      const snap = getDayMetrics(agentId, g.dateKey);
      if (snap) next[g.dateKey] = snap;
    }
    setDaySnaps(next);
  };

  useEffect(() => {
    refresh();
  }, [agentId]);

  const groups = useMemo(() => groupCohortByDate(cohort), [cohort]);

  useEffect(() => {
    if (groups.length >= 2) {
      if (!compareB) setCompareB(groups[0].dateKey);
      if (!compareA) setCompareA(groups[1]?.dateKey || groups[0].dateKey);
    } else if (groups.length === 1) {
      if (!compareB) setCompareB(groups[0].dateKey);
      if (!compareA) setCompareA(groups[0].dateKey);
    }
  }, [groups, compareA, compareB]);

  const runDay = async (dateKey: string, force = false) => {
    if (!agentId) return;
    const group = groups.find((g) => g.dateKey === dateKey);
    if (!group?.patients.length) return;
    setEvaluatingDate(dateKey);
    setEvalError(null);
    setProgress({ done: 0, total: group.patients.length });
    try {
      const snap = await evaluateDayPatients(group.patients, agentId, dateKey, {
        force,
        onProgress: setProgress,
      });
      setDaySnaps((prev) => ({ ...prev, [dateKey]: snap }));
    } catch (err: unknown) {
      setEvalError(err instanceof Error ? err.message : "Day evaluation failed");
    } finally {
      setEvaluatingDate(null);
      setProgress(null);
    }
  };

  const snapA = agentId && compareA ? daySnaps[compareA] || getDayMetrics(agentId, compareA) : undefined;
  const snapB = agentId && compareB ? daySnaps[compareB] || getDayMetrics(agentId, compareB) : undefined;
  const comparison =
    snapA && snapB && compareA !== compareB ? compareDayMetrics(snapA, snapB) : null;

  return (
    <AppLayout>
      <PageHeader
        eyebrow="Cohort"
        title="Synthetic Patients"
        description="Generate appends patients (3→6→9…). Grouped by generation day — evaluate a whole day, then compare day-over-day live metrics."
        actions={
          <Link
            to="/setup"
            search={setupSearchLink({ agent: agentId, patient: selectedId })}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium lowercase text-primary hover:bg-secondary"
          >
            <Sparkles className="h-3.5 w-3.5" /> generate more / setup
          </Link>
        }
      />

      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-warning/30 bg-warning/5 p-4 text-sm">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <div>
          <div className="font-medium text-foreground">
            All records marked SYNTHETIC · {cohort.length} in session
          </div>
          <div className="text-xs text-muted-foreground">
            Agent under test: {agentId || "(complete Setup)"}. Day scores come only from live
            POST /cases/run — never invented.
          </div>
        </div>
      </div>

      {cohort.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center">
          <p className="text-sm text-muted-foreground">No Gemini cohort in this session yet.</p>
          <Link
            to="/setup"
            search={setupSearchLink({ agent: agentId })}
            className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-primary px-5 py-2.5 text-sm font-medium lowercase text-primary-foreground"
          >
            go to setup <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <>
          {/* Compare panel */}
          {groups.length >= 1 && (
            <div className="glass-card mb-8 rounded-2xl p-5">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <GitCompare className="h-4 w-4 text-primary" />
                Compare days
              </div>
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-xs text-muted-foreground">
                  day A (baseline)
                  <select
                    className="mt-1 block rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                    value={compareA}
                    onChange={(e) => setCompareA(e.target.value)}
                  >
                    {groups.map((g) => (
                      <option key={g.dateKey} value={g.dateKey}>
                        {formatDateKeyDisplay(g.dateKey)} ({g.patients.length})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-xs text-muted-foreground">
                  day B (compare)
                  <select
                    className="mt-1 block rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                    value={compareB}
                    onChange={(e) => setCompareB(e.target.value)}
                  >
                    {groups.map((g) => (
                      <option key={g.dateKey} value={g.dateKey}>
                        {formatDateKeyDisplay(g.dateKey)} ({g.patients.length})
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {compareA === compareB ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Pick two different days to compare performance.
                </p>
              ) : !snapA || !snapB ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Evaluate both days first (use <strong>evaluate this day</strong> below) so live
                  aggregates exist for the compare.
                </p>
              ) : comparison ? (
                <div className="mt-4 rounded-xl bg-primary-soft/50 p-4">
                  <p className="text-sm text-foreground">{comparison.sentence}</p>
                  {comparison.trustDelta != null && (
                    <p className="mt-2 font-display text-2xl font-semibold tabular-nums text-primary">
                      {comparison.trustDelta > 0 ? "+" : ""}
                      {comparison.trustDelta} trust
                    </p>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {evalError && (
            <div className="mb-6">
              <ErrorBlock message={evalError} onRetry={() => setEvalError(null)} />
            </div>
          )}

          {groups.map((g) => {
            const snap = daySnaps[g.dateKey];
            const busy = evaluatingDate === g.dateKey;
            return (
              <section key={g.dateKey} className="mb-10">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-display text-xl font-semibold">
                      {formatDateKeyDisplay(g.dateKey)}
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      {g.patients.length} patient{g.patients.length === 1 ? "" : "s"} generated this
                      day
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={!agentId || busy}
                      onClick={() => void runDay(g.dateKey, false)}
                      className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-xs font-medium lowercase text-primary-foreground disabled:opacity-50"
                    >
                      <Play className="h-3.5 w-3.5" />
                      {busy ? "evaluating…" : "evaluate this day"}
                    </button>
                    {snap && (
                      <button
                        type="button"
                        disabled={!agentId || busy}
                        onClick={() => void runDay(g.dateKey, true)}
                        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-2 text-xs font-medium lowercase disabled:opacity-50"
                      >
                        <RefreshCw className="h-3.5 w-3.5" /> force re-run day
                      </button>
                    )}
                  </div>
                </div>

                {busy && progress && (
                  <div className="mb-4">
                    <LoadingBlock
                      label={`evaluating ${progress.currentPatientId || "…"} (${progress.done}/${progress.total})…`}
                    />
                  </div>
                )}

                {snap && !busy && (
                  <div className="glass-card mb-4 rounded-2xl p-4">
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      <BarChart3 className="h-3.5 w-3.5 text-primary" /> Day aggregate (cached)
                    </div>
                    <p className="mb-3 text-xs text-muted-foreground">
                      Restored from this browser session — not auto-run. Click evaluate this day to
                      refresh live scores.
                    </p>
                    <div className="flex flex-wrap gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">ok / fail · </span>
                        <span className="font-medium">
                          {snap.okCount}/{snap.failCount}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">mean trust · </span>
                        <span className="font-display text-lg font-semibold tabular-nums">
                          {snap.meanTrust != null ? snap.meanTrust : "—"}
                        </span>
                      </div>
                    </div>
                    {snap.meanMetrics.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {snap.meanMetrics.slice(0, 6).map((m) => (
                          <span
                            key={m.key}
                            className="rounded-full bg-secondary px-2.5 py-1 text-[11px] text-muted-foreground"
                          >
                            {m.label}: {m.value}
                            {m.unit === "%" ? "%" : ""}
                          </span>
                        ))}
                      </div>
                    )}
                    {snap.failCount > 0 && (
                      <p className="mt-2 text-xs text-warning">
                        {snap.failCount} patient(s) returned insufficient_data or errors — not
                        included in means.
                      </p>
                    )}
                  </div>
                )}

                {!snap && !busy && (
                  <div className="mb-4 rounded-2xl border border-dashed border-border bg-card/50 px-4 py-3 text-sm text-muted-foreground">
                    Not evaluated yet — click <span className="font-medium text-foreground">evaluate this day</span>{" "}
                    for a live day aggregate.
                  </div>
                )}

                <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                  {g.patients.map((p, i) => {
                    const selected = selectedId === p.id;
                    return (
                      <div
                        key={p.id}
                        className={`glass-card group relative flex flex-col overflow-hidden rounded-2xl transition-all hover:-translate-y-1 hover:shadow-lg ${
                          selected ? "ring-2 ring-primary/40" : ""
                        }`}
                        style={{ animationDelay: `${i * 40}ms` }}
                      >
                        <div
                          className={`h-1.5 w-full bg-gradient-to-r ${riskAccent[p.riskProfile] || riskAccent.Moderate}`}
                        />
                        <div className="flex flex-1 flex-col p-5">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <h3 className="font-display text-xl font-semibold">{p.name}</h3>
                                <SyntheticBadge />
                                {p.scenarioType && (
                                  <span className="rounded-full border border-border bg-secondary px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                                    {p.scenarioType.replace(/_/g, " ")}
                                  </span>
                                )}
                              </div>
                              <div className="mt-1 text-xs text-muted-foreground">
                                {p.id} · {p.age}
                                {p.sex} · {p.livingSituation}
                              </div>
                            </div>
                            <span
                              className={`shrink-0 rounded-full border px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider ${riskColor[p.riskProfile]}`}
                            >
                              {p.riskProfile}
                            </span>
                          </div>
                          <p className="mt-4 flex-1 text-sm leading-relaxed text-foreground/90">
                            {p.chiefComplaint}
                          </p>
                          <div className="mt-5 flex flex-wrap gap-2">
                            {(p.comorbidities || []).slice(0, 3).map((c) => (
                              <span
                                key={c}
                                className="rounded-full bg-secondary px-2 py-0.5 text-[10.5px] text-muted-foreground"
                              >
                                {c}
                              </span>
                            ))}
                          </div>
                          <Link
                            to="/"
                            search={patientSearchLink(p.id, agentId)}
                            className="mt-6 inline-flex items-center justify-center gap-1.5 rounded-full bg-primary px-4 py-2.5 text-sm font-medium lowercase text-primary-foreground transition group-hover:shadow-md"
                          >
                            open patient dashboard <ArrowRight className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </>
      )}
    </AppLayout>
  );
}
