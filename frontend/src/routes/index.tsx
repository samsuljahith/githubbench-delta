import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { AppLayout, PageHeader, SyntheticBadge } from "@/components/AppLayout";
import { ErrorBlock, InsufficientBlock, LoadingBlock } from "@/components/ApiStates";
import { useAsyncResource } from "@/hooks/useApiQuery";
import {
  getHealthcareReport,
  patientToCasePayload,
  postCaseRun,
  postHealthcareAssess,
  postMemorization,
  type CaseRunData,
  type EvalMetric,
  type FacadeEnvelope,
  type HealthcareEvaluateData,
  type HealthcareReport,
} from "@/lib/api";
import { getConversation } from "@/lib/demo-data";
import { deriveLiveInsights } from "@/lib/liveInsights";
import {
  DASHBOARD_SECTIONS,
  parseSetupSearch,
  patientFromSearch,
  setupSearchLink,
} from "@/lib/patient";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Download,
  Play,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  TrendingDown,
  TrendingUp,
  User,
} from "lucide-react";

export const Route = createFileRoute("/")({
  validateSearch: parseSetupSearch,
  head: () => ({
    meta: [
      { title: "Patient Dashboard · ElderWise" },
      {
        name: "description",
        content:
          "Unified Gemini patient workspace: conversation chrome + live assessment, evaluation, trust, benchmark, and research insights.",
      },
    ],
  }),
  component: PatientDashboard,
});

const LIVE_CTA = "run live evaluation";

const roleMeta = {
  assistant: { label: "ElderWise", icon: Sparkles, className: "bg-primary text-primary-foreground" },
  patient: { label: "Patient", icon: User, className: "bg-secondary text-foreground" },
  clinician: { label: "Clinician", icon: Stethoscope, className: "bg-accent text-accent-foreground" },
} as const;

const flagMeta = {
  normal: { icon: CheckCircle2, cls: "text-success", label: "Normal" },
  watch: { icon: Circle, cls: "text-warning", label: "Watch" },
  concern: { icon: AlertTriangle, cls: "text-destructive", label: "Concern" },
} as const;

function metricPct(metrics: EvalMetric[], keys: string[]): number {
  const hit = metrics.find((m) => keys.some((k) => m.key.includes(k)));
  return hit ? Math.round(hit.value) : 0;
}

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  if (typeof window !== "undefined") {
    window.history.replaceState(null, "", `#${id}`);
  }
}

type DashBundle = {
  envelope: FacadeEnvelope<CaseRunData>;
  memorizationNote: string;
};

function LiveCtaButton({
  onClick,
  loading,
  className = "",
}: {
  onClick: () => void;
  loading?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className={`inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-medium lowercase tracking-wide text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:opacity-50 ${className}`}
    >
      <Play className="h-3.5 w-3.5" />
      {loading ? "running…" : LIVE_CTA}
    </button>
  );
}

function SectionShell({
  id,
  title,
  subtitle,
  actions,
  children,
}: {
  id: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mb-12 scroll-mt-32 animate-fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            {title}
          </h2>
          {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

function SectionEmpty({
  title,
  blurb,
  onRun,
  loading,
}: {
  title: string;
  blurb: string;
  onRun: () => void;
  loading?: boolean;
}) {
  return (
    <div className="glass-card relative overflow-hidden rounded-2xl p-8 text-center md:p-10">
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(circle at 30% 20%, oklch(0.9 0.06 185 / 0.5), transparent 55%)",
        }}
      />
      <div className="relative">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-soft text-primary">
          <Play className="h-6 w-6" />
        </div>
        <h3 className="font-display text-lg font-semibold">{title}</h3>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{blurb}</p>
        <div className="mt-6">
          <LiveCtaButton onClick={onRun} loading={loading} />
        </div>
      </div>
    </div>
  );
}

function HealthcareEvaluationCard({ report }: { report: HealthcareReport }) {
  const completeness = report.completeness;
  const findings = report.critical_findings ?? [];
  const warnings = report.safety_warnings ?? [];
  const ratio =
    completeness?.completeness_ratio != null
      ? Math.round(completeness.completeness_ratio * 100)
      : null;
  const reviewLabel = (report.review_status || "pending").replace(/_/g, " ");

  return (
    <div className="glass-card rounded-2xl border border-border/60 p-5 md:p-6">
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-border bg-secondary/80 px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
          clinical evidence layer
        </span>
        <span className="text-xs text-muted-foreground">report {report.report_id}</span>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className="rounded-xl bg-secondary/40 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Clinical Completeness
          </div>
          <div className="mt-2 font-display text-3xl font-semibold tabular-nums tracking-tight">
            {ratio != null ? `${ratio}%` : "—"}
          </div>
          {completeness && (
            <>
              <p className="mt-2 text-xs text-muted-foreground">
                {(completeness.present_fields ?? []).length} present ·{" "}
                {(completeness.missing_fields ?? []).length} missing of required RGA fields
              </p>
              {(completeness.missing_fields ?? []).length > 0 && (
                <p className="mt-2 text-xs text-foreground">
                  Missing: {completeness.missing_fields.join(", ")}
                </p>
              )}
            </>
          )}
        </div>

        <div className="rounded-xl bg-secondary/40 p-4">
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Human Review Status
          </div>
          <div className="mt-2 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-muted-foreground" />
            <span className="font-display text-2xl font-semibold capitalize tracking-tight">
              {reviewLabel}
            </span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Clinician workflow status — independent of engineering TrustScore.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <AlertTriangle className="h-3.5 w-3.5" />
            Missing Critical Findings
          </div>
          {findings.length === 0 ? (
            <p className="text-sm text-muted-foreground">None detected from submitted evidence.</p>
          ) : (
            <ul className="space-y-2">
              {findings.map((f) => (
                <li
                  key={f.finding_id}
                  className="rounded-xl border border-warning/20 bg-warning/5 px-3 py-2 text-sm"
                >
                  <span className="text-[10.5px] font-semibold uppercase tracking-wider text-warning">
                    {f.severity}
                  </span>
                  <p className="mt-0.5 text-foreground">{f.message}</p>
                  {f.evidence_span && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      evidence: “{f.evidence_span}”
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <ShieldAlert className="h-3.5 w-3.5" />
            Safety Warnings
          </div>
          {warnings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No safety warnings from rule checks.</p>
          ) : (
            <ul className="space-y-2">
              {warnings.map((w) => (
                <li
                  key={w.rule_id}
                  className="rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm"
                >
                  <p className="text-foreground">{w.message}</p>
                  {w.evidence_span && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      evidence: “{w.evidence_span}”
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {report.provenance && (
        <p className="mt-5 text-xs text-muted-foreground">{report.provenance}</p>
      )}
    </div>
  );
}

function PatientDashboard() {
  const search = Route.useSearch();
  const patient = patientFromSearch(search);
  const agentId = search.agent;
  const [runKey, setRunKey] = useState(0);
  const [force, setForce] = useState(false);
  const [started, setStarted] = useState(false);
  const [activeSection, setActiveSection] = useState("conversation");

  useEffect(() => {
    const hash = typeof window !== "undefined" ? window.location.hash.replace(/^#/, "") : "";
    if (hash && DASHBOARD_SECTIONS.some((s) => s.id === hash)) {
      setActiveSection(hash);
      requestAnimationFrame(() => scrollToSection(hash));
    }
  }, []);

  const { data, error, loading, reload } = useAsyncResource(async (): Promise<DashBundle | null> => {
    if (!started || !patient || !agentId) return null;
    const envelope = await postCaseRun(patientToCasePayload(patient), { agentId, force });
    let memorizationNote = "MDS not requested";
    if (envelope.ok && envelope.experiment_id) {
      try {
        const mem = await postMemorization([envelope.experiment_id]);
        memorizationNote = mem.ok
          ? "MDS report available via POST /memorization"
          : mem.detail || "MDS insufficient_data";
      } catch {
        memorizationNote = "MDS request failed";
      }
    }
    return { envelope, memorizationNote };
  }, [patient?.id, agentId, runKey, started, force]);

  /** Healthcare — only after Run Live Evaluation; LLM RGA then evaluate (not chrome placeholders). */
  const {
    data: hcEnvelope,
    error: hcError,
    loading: hcLoading,
    reload: hcReload,
  } = useAsyncResource(async (): Promise<FacadeEnvelope<HealthcareEvaluateData> | null> => {
    if (!started || !patient) return null;
    const turns = getConversation(patient);
    const transcript = turns.map((t) => `${t.role}: ${t.text}`).join("\n");
    const assessed = await postHealthcareAssess({
      patient: patientToCasePayload(patient),
      transcript,
      conversation: turns.map((t) => ({ role: t.role, text: t.text })),
    });
    const reportId = assessed.data?.report_id;
    if (reportId) {
      return getHealthcareReport(reportId);
    }
    return assessed;
  }, [patient?.id, runKey, started]);

  const startLiveEvaluation = useCallback((scrollId?: string) => {
    setForce(true);
    setStarted(true);
    setRunKey((k) => k + 1);
    scrollToSection(scrollId || "assessment");
    setActiveSection(scrollId || "assessment");
  }, []);

  const softReload = () => {
    setForce(false);
    setRunKey((k) => k + 1);
    reload();
  };

  if (!patient || !agentId) {
    return (
      <AppLayout>
        <PageHeader
          eyebrow="Patient dashboard"
          title="Select a Gemini patient"
          description="Synthetic cohort must come from Setup → Generate. Pick a patient on Synthetic Patients."
        />
        <Link
          to="/patients"
          search={setupSearchLink({ agent: agentId })}
          className="inline-flex rounded-full bg-primary px-5 py-2.5 text-sm font-medium lowercase text-primary-foreground"
        >
          open synthetic patients
        </Link>
      </AppLayout>
    );
  }

  const turns = getConversation(patient);
  const caseData = data?.envelope?.ok ? data.envelope.data : null;
  const env = data?.envelope;
  const insights = caseData ? deriveLiveInsights(caseData) : [];
  const liveReady = Boolean(caseData && env?.ok);
  const liveFailed = started && !loading && (Boolean(error) || (env != null && !env.ok));

  const downloadBenchmark = () => {
    if (!caseData || !env) return;
    const metrics = caseData.evaluate.metrics;
    const payload = {
      run: env.experiment_id,
      evaluator: "GitHubBench-Delta",
      patient: { id: patient.id, synthetic: true, presentation: patient.chiefComplaint },
      task_id: caseData.task_id,
      agent_id: caseData.agent_id,
      cached: caseData.cached,
      trustScore: caseData.trust.overall,
      band: caseData.trust.band,
      metrics: metrics.map((m) => ({
        key: m.key,
        label: m.label,
        value: m.value,
        target: m.target,
        unit: m.unit,
      })),
      comparisons: [
        {
          model: `Live case ${env.experiment_id}`,
          trust: caseData.trust.overall,
          faith: metricPct(metrics, ["ground", "faith", "consistency"]),
          cover: metricPct(metrics, ["coverage", "task_resolution", "engineering"]),
          safety: metricPct(metrics, ["safety"]),
        },
      ],
      memorization: data?.memorizationNote,
      note: "Synthetic patient chrome only. Metrics and TrustScore are live case-run outputs.",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `elderwise-benchmark-${patient.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /** Lazy body so caseData.! access is not evaluated while caseData is still null. */
  const renderLiveBody = (
    sectionId: string,
    emptyTitle: string,
    emptyBlurb: string,
    body: () => ReactNode,
  ) => {
    if (!started) {
      return (
        <SectionEmpty
          title={emptyTitle}
          blurb={emptyBlurb}
          onRun={() => startLiveEvaluation(sectionId)}
          loading={loading}
        />
      );
    }
    if (loading) {
      return <LoadingBlock label={`running live evaluation with ${agentId}…`} />;
    }
    if (error) {
      return <ErrorBlock message={error} onRetry={softReload} />;
    }
    if (env && !env.ok) {
      return (
        <InsufficientBlock
          detail={env.detail}
          onForceRetry={() => startLiveEvaluation(sectionId)}
        />
      );
    }
    if (liveReady && caseData) return body();
    return (
      <SectionEmpty
        title={emptyTitle}
        blurb={emptyBlurb}
        onRun={() => startLiveEvaluation(sectionId)}
      />
    );
  };

  return (
    <AppLayout>
      <PageHeader
        eyebrow="Patient workspace"
        title={patient.name}
        description={`${patient.id} · ${patient.age}${patient.sex} · agent ${agentId}. conversation is synthetic chrome. scores come only from live evaluation.`}
        actions={
          <LiveCtaButton
            onClick={() => startLiveEvaluation("assessment")}
            loading={loading && started}
          />
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <SyntheticBadge id={patient.id} />
        <span className="text-sm text-muted-foreground">{patient.chiefComplaint}</span>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider ${
            patient.riskProfile === "High"
              ? "border-destructive/30 bg-destructive/10 text-destructive"
              : patient.riskProfile === "Low"
                ? "border-success/30 bg-success/10 text-success"
                : "border-warning/30 bg-warning/10 text-warning"
          }`}
        >
          {patient.riskProfile} risk
        </span>
      </div>

      <nav className="sticky top-14 z-[9] mb-10 flex gap-1 overflow-x-auto rounded-2xl border border-border/80 bg-card/80 p-1.5 shadow-sm backdrop-blur-md">
        {DASHBOARD_SECTIONS.map((s) => {
          const active = activeSection === s.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => {
                setActiveSection(s.id);
                scrollToSection(s.id);
              }}
              className={`relative shrink-0 rounded-xl px-3.5 py-2 text-xs font-medium transition-colors ${
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </nav>

      {/* Conversation — always visible */}
      <SectionShell
        id="conversation"
        title="Conversation"
        subtitle="Synthetic dialog from Gemini patient fields — not a live voice recording."
      >
        <div className="glass-card relative overflow-hidden rounded-2xl p-5 md:p-8">
          <div className="pointer-events-none absolute bottom-0 left-6 top-6 w-px bg-gradient-to-b from-primary/40 via-border to-transparent" />
          <div className="mx-auto max-w-3xl space-y-5 pl-4">
            {turns.map((turn, i) => {
              const meta = roleMeta[turn.role];
              const Icon = meta.icon;
              const isPatient = turn.role === "patient";
              return (
                <div
                  key={i}
                  className={`flex gap-3 ${isPatient ? "flex-row-reverse" : ""}`}
                  style={{ animationDelay: `${i * 35}ms` }}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full shadow-sm ${meta.className}`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div
                    className={`max-w-[78%] ${isPatient ? "items-end text-right" : ""} flex flex-col`}
                  >
                    <div className="mb-1 flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="font-medium text-foreground/80">{meta.label}</span>
                      <span className="tabular-nums">{turn.t}</span>
                    </div>
                    <div
                      className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                        isPatient
                          ? "rounded-tr-sm bg-secondary text-foreground"
                          : turn.role === "assistant"
                            ? "rounded-tl-sm bg-primary-soft text-foreground"
                            : "rounded-tl-sm border border-border bg-background/80 text-foreground"
                      }`}
                    >
                      {turn.text}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </SectionShell>

      {/* Assessment */}
      <SectionShell
        id="assessment"
        title="Assessment"
        subtitle={
          liveReady
            ? `live domains · task ${caseData!.task_id}${caseData!.cached ? " · cached" : " · fresh"}`
            : "structured domains from a live case run"
        }
        actions={
          liveReady ? (
            <button
              type="button"
              onClick={() => startLiveEvaluation("assessment")}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium lowercase"
            >
              <RefreshCw className="h-3.5 w-3.5" /> force re-run
            </button>
          ) : undefined
        }
      >
        {renderLiveBody(
          "assessment",
          "Assessment not run yet",
          `Run a live evaluation with ${agentId} to fill assessment domains for this patient.`,
          () => (
          <>
            {caseData!.loop_engineering && (
              <div className="mb-4 rounded-xl border border-border bg-card/90 px-4 py-3 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">Loop engineering · </span>
                {caseData!.loop_engineering.summary}
              </div>
            )}
            <div className="space-y-3">
              {caseData!.assessment.domains.map((d, i) => {
                const meta = flagMeta[d.flag] ?? flagMeta.watch;
                const Icon = meta.icon;
                const pct = (d.score / d.max) * 100;
                return (
                  <div
                    key={d.domain}
                    className="glass-card animate-fade-in rounded-xl p-4"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <Icon className={`mt-0.5 h-4.5 w-4.5 ${meta.cls}`} />
                        <div>
                          <div className="text-sm font-semibold">{d.domain}</div>
                          <div className="text-xs text-muted-foreground">{d.note}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-display text-lg font-semibold tabular-nums">
                          {d.score}
                          <span className="text-sm text-muted-foreground">/{d.max}</span>
                        </div>
                        <div
                          className={`text-[10.5px] font-medium uppercase tracking-wider ${meta.cls}`}
                        >
                          {meta.label}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
          ),
        )}
      </SectionShell>

      {/* Engineering Evaluation — GitHubBench 18 metrics / loop engineering */}
      <SectionShell
        id="evaluation"
        title="Engineering Evaluation"
        subtitle="live GitHubBench metrics and loop engineering — not clinical scoring"
      >
        {renderLiveBody(
          "evaluation",
          "Engineering evaluation not run yet",
          "Metrics appear after you run live evaluation for this agent and patient.",
          () => (
          <>
            {caseData!.loop_engineering && (
              <div className="mb-6 glass-card rounded-2xl p-5">
                <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Loop engineering
                </div>
                <p className="mt-2 text-sm text-foreground">{caseData!.loop_engineering.summary}</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-4">
                  {[
                    { label: "Trajectory steps", value: caseData!.loop_engineering.step_count },
                    { label: "Tool calls", value: caseData!.loop_engineering.tool_call_count },
                    { label: "Errors", value: caseData!.loop_engineering.error_count },
                    {
                      label: "Latency (ms)",
                      value: Math.round(caseData!.loop_engineering.latency_ms),
                    },
                  ].map((k) => (
                    <div key={k.label} className="rounded-xl bg-primary-soft/60 p-3">
                      <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground">
                        {k.label}
                      </div>
                      <div className="mt-1 font-display text-2xl font-semibold tabular-nums">
                        {k.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {caseData!.evaluate.metrics.map((m, i) => {
                const isLowerBetter =
                  m.key.includes("hallucin") || m.key.includes("unnecessary");
                const passes = isLowerBetter ? m.value <= m.target : m.value >= m.target;
                const Icon = passes ? TrendingUp : TrendingDown;
                const barMax = m.unit === "%" ? 100 : 5;
                const pct = Math.min(100, (m.value / barMax) * 100);
                return (
                  <div
                    key={m.key}
                    className="glass-card animate-fade-in rounded-2xl p-5"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="text-sm font-medium text-foreground">{m.label}</div>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-medium ${
                          passes ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                        }`}
                      >
                        <Icon className="h-3 w-3" />
                        {passes ? "Pass" : "Watch"}
                      </span>
                    </div>
                    <div className="mt-3 font-display text-3xl font-semibold tabular-nums tracking-tight">
                      {m.value}
                      {m.unit === "%" ? "%" : ""}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      Target {m.target}
                      {m.unit === "%" ? "%" : ""} · {m.description}
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </>
          ),
        )}
      </SectionShell>

      {/* Healthcare Evaluation — live LLM RGA only after Run Live Evaluation */}
      <SectionShell
        id="healthcare"
        title="Healthcare Evaluation"
        subtitle="live LLM Rapid Geriatric Assessment then rule checks — not chrome placeholders; not the 18 engineering metrics; not a diagnosis"
      >
        {!started ? (
          <div className="glass-card rounded-2xl p-8 text-center md:p-10">
            <h3 className="font-display text-lg font-semibold">
              Healthcare evaluation has not been run yet.
            </h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              Metrics appear only after you run live evaluation. The conversation is sent to the
              configured LLM to produce a structured RGA; completeness reflects that live output
              only.
            </p>
            <div className="mt-6">
              <LiveCtaButton onClick={() => startLiveEvaluation("healthcare")} loading={false} />
            </div>
          </div>
        ) : hcLoading ? (
          <LoadingBlock label="extracting RGA via LLM and evaluating clinical evidence…" />
        ) : hcError ? (
          <ErrorBlock
            message={hcError}
            onRetry={() => {
              setForce(true);
              setRunKey((k) => k + 1);
              hcReload();
            }}
          />
        ) : !hcEnvelope ? (
          <LoadingBlock label="loading healthcare evaluation…" />
        ) : !hcEnvelope.ok ||
          hcEnvelope.status === "insufficient_data" ||
          !hcEnvelope.data?.report ||
          hcEnvelope.data.report.insufficient_data ? (
          <InsufficientBlock
            detail={
              hcEnvelope.detail ||
              hcEnvelope.data?.report?.detail ||
              "insufficient_data: no live RGA assessment to evaluate"
            }
            onForceRetry={() => {
              setForce(true);
              setStarted(true);
              setRunKey((k) => k + 1);
            }}
          />
        ) : (
          <HealthcareEvaluationCard report={hcEnvelope.data.report} />
        )}
      </SectionShell>

      {/* Trust */}
      <SectionShell id="trust" title="TrustScore" subtitle="composite trust from live group_scores">
        {renderLiveBody(
          "trust",
          "TrustScore not run yet",
          "The trust ring and breakdown fill from the same live case run.",
          () => {
            const { overall, band, breakdown } = caseData!.trust;
            const circ = 2 * Math.PI * 54;
            const dash = (overall / 100) * circ;
            return (
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="glass-card rounded-2xl p-6">
                  <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    <ShieldCheck className="h-3.5 w-3.5 text-primary" /> This case run
                  </div>
                  <div className="mt-6 flex flex-col items-center">
                    <div className="relative h-44 w-44">
                      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                        <circle
                          cx="60"
                          cy="60"
                          r="54"
                          strokeWidth="10"
                          className="fill-none stroke-secondary"
                        />
                        <circle
                          cx="60"
                          cy="60"
                          r="54"
                          strokeWidth="10"
                          strokeLinecap="round"
                          className="animate-trust-ring fill-none stroke-primary"
                          style={{ strokeDasharray: `${dash} ${circ}` }}
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <div className="font-display text-5xl font-semibold tabular-nums tracking-tight">
                          {overall}
                        </div>
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          / 100
                        </div>
                      </div>
                    </div>
                    <p className="mt-4 text-center text-sm text-muted-foreground">{band}</p>
                  </div>
                </div>
                <div className="glass-card lg:col-span-2 rounded-2xl p-6">
                  <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Breakdown (live group_scores)
                  </div>
                  <div className="mt-4 space-y-4">
                    {breakdown.map((b) => (
                      <div key={b.name}>
                        <div className="mb-1.5 flex items-center justify-between text-sm">
                          <span>{b.name}</span>
                          <span className="tabular-nums font-medium text-foreground">{b.value}</span>
                        </div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-secondary">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-primary to-[oklch(0.62_0.1_165)] transition-all duration-700"
                            style={{ width: `${Math.min(100, b.value)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          },
        )}
      </SectionShell>

      {/* Benchmark */}
      <SectionShell
        id="benchmark"
        title="Benchmark Report"
        subtitle="live trust + evaluate snapshot for this patient"
        actions={
          liveReady ? (
            <button
              type="button"
              onClick={downloadBenchmark}
              className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-medium lowercase text-primary-foreground"
            >
              <Download className="h-3.5 w-3.5" /> download report
            </button>
          ) : undefined
        }
      >
        {renderLiveBody(
          "benchmark",
          "Benchmark not run yet",
          "Run live evaluation to build a benchmark row from real metrics — no fabricated baselines.",
          () => {
            const metrics = caseData!.evaluate.metrics;
            const row = {
              model: `Live · ${env!.experiment_id}`,
              trust: caseData!.trust.overall,
              faith: metricPct(metrics, ["ground", "consistency", "faith"]),
              cover: metricPct(metrics, ["task_resolution", "engineering", "coverage"]),
              safety: metricPct(metrics, ["safety"]),
            };
            return (
              <>
                <div className="glass-card overflow-hidden rounded-2xl">
                  <table className="w-full text-sm">
                    <thead className="bg-primary-soft/50 text-xs uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium">Model / run</th>
                        <th className="px-4 py-3 text-right font-medium">Trust</th>
                        <th className="px-4 py-3 text-right font-medium">Faith</th>
                        <th className="px-4 py-3 text-right font-medium">Cover</th>
                        <th className="px-4 py-3 text-right font-medium">Safety</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-t border-border">
                        <td className="px-4 py-3.5 font-medium">{row.model}</td>
                        <td className="px-4 py-3.5 text-right font-display text-base tabular-nums">
                          {row.trust}
                        </td>
                        <td className="px-4 py-3.5 text-right tabular-nums">{row.faith}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums">{row.cover}</td>
                        <td className="px-4 py-3.5 text-right tabular-nums">{row.safety}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">{data?.memorizationNote}</p>
              </>
            );
          },
        )}
      </SectionShell>

      {/* Insights */}
      <SectionShell
        id="insights"
        title="Research Insights"
        subtitle="derived from this case’s live evaluator outputs only"
      >
        {renderLiveBody(
          "insights",
          "Insights not available yet",
          "Insights are written from live metrics and trust — never invented. Run live evaluation first.",
          () =>
            insights.length === 0 ? (
              <InsufficientBlock detail="No live metrics available to derive insights." />
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {insights.map((ins, i) => (
                  <div
                    key={ins.title}
                    className="glass-card animate-fade-in rounded-2xl border-l-4 border-l-primary p-5"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <h3 className="font-display text-base font-semibold">{ins.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{ins.body}</p>
                  </div>
                ))}
              </div>
            ),
        )}
      </SectionShell>

      {liveFailed && (
        <p className="mb-4 text-center text-xs text-muted-foreground">
          Live evaluation did not return scores. Use force re-run or check the agent provider.
        </p>
      )}
    </AppLayout>
  );
}
