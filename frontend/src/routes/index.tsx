import { createFileRoute, Link } from "@tanstack/react-router";
import { AppLayout, PageHeader, SyntheticBadge } from "@/components/AppLayout";
import { ErrorBlock, InsufficientBlock, LoadingBlock } from "@/components/ApiStates";
import { useAsyncResource } from "@/hooks/useApiQuery";
import {
  defaultExperimentId,
  postEvaluate,
  postTrust,
  type EvalMetric,
  type TrustData,
} from "@/lib/api";
import { patients, timeline } from "@/lib/demo-data";
import {
  ArrowRight,
  MessagesSquare,
  ClipboardList,
  GaugeCircle,
  ShieldCheck,
  FileText,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard · ElderWise Evaluation" },
      {
        name: "description",
        content:
          "Overview combining synthetic narrative chrome with live GitHubBench-Delta TrustScore and metrics.",
      },
      { property: "og:title", content: "ElderWise Evaluation Dashboard" },
      { property: "og:description", content: "Live evaluator snapshot + labeled synthetic case." },
    ],
  }),
  component: Dashboard,
});

const workflow = [
  { label: "Synthetic Patient", to: "/patients" },
  { label: "Conversation", to: "/conversation" },
  { label: "Assessment", to: "/assessment" },
  { label: "Evaluation", to: "/evaluation" },
  { label: "TrustScore", to: "/trustscore" },
  { label: "Benchmark", to: "/benchmark" },
];

type Dash = { trust: TrustData; metrics: EvalMetric[]; experimentId: string };

async function loadDash(): Promise<Dash> {
  const eid = defaultExperimentId();
  const [t, e] = await Promise.all([postTrust(eid), postEvaluate(eid)]);
  if (!t.ok || !t.data) throw new Error(t.detail || "insufficient_data for trust");
  if (!e.ok || !e.data?.metrics?.length) throw new Error(e.detail || "insufficient_data for evaluate");
  return {
    trust: t.data,
    metrics: e.data.metrics,
    experimentId: t.experiment_id || eid,
  };
}

function Dashboard() {
  const activePatient = patients[0];
  const { data, error, loading, reload } = useAsyncResource(loadDash);

  return (
    <AppLayout>
      <PageHeader
        eyebrow="Run overview"
        title="Evaluation run · GitHubBench-Delta"
        description="Synthetic patient chrome is labeled narrative. TrustScore and metrics load from the live API."
        actions={
          <Link
            to="/benchmark"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <FileText className="h-4 w-4" /> Benchmark report
          </Link>
        }
      />

      {loading && <LoadingBlock />}
      {error && <ErrorBlock message={error} onRetry={reload} />}
      {!loading && !error && !data && <InsufficientBlock />}

      {data && (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Narrative case (synthetic)
                  </div>
                  <div className="mt-1 flex items-center gap-3">
                    <h2 className="text-xl font-semibold">{activePatient.name}</h2>
                    <SyntheticBadge id={activePatient.id} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {activePatient.age}
                    {activePatient.sex} · {activePatient.chiefComplaint}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Live experiment · {data.experimentId}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    TrustScore
                  </div>
                  <div className="mt-1 text-4xl font-semibold tracking-tight text-primary">
                    {data.trust.overall}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{data.trust.band}</div>
                </div>
              </div>

              <div className="mt-8">
                <div className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Workflow
                </div>
                <div className="flex flex-wrap items-center gap-x-1 gap-y-2">
                  {workflow.map((w, i) => (
                    <div key={w.label} className="flex items-center">
                      <Link
                        to={w.to}
                        className="rounded-md border border-border bg-secondary/60 px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:border-primary hover:text-primary"
                      >
                        {w.label}
                      </Link>
                      {i < workflow.length - 1 && (
                        <ArrowRight className="mx-1 h-3.5 w-3.5 text-muted-foreground" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Evaluator snapshot (live)
              </div>
              <div className="mt-4 space-y-4">
                {data.metrics.slice(0, 4).map((m) => (
                  <div key={m.key}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-foreground">{m.label}</span>
                      <span className="tabular-nums text-muted-foreground">
                        {m.value}
                        {m.unit === "%" ? "%" : ""}
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{
                          width: `${Math.min(100, (m.value / (m.unit === "%" ? 100 : 5)) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <Link
                to="/evaluation"
                className="mt-6 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                View all metrics <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-4">
            {[
              {
                label: "Experiment",
                value: data.experimentId.slice(0, 12) + "…",
                sub: "default VITE id",
              },
              {
                label: "Metrics returned",
                value: String(data.metrics.length),
                sub: "POST /evaluate",
              },
              {
                label: "Trust overall",
                value: String(data.trust.overall),
                sub: "POST /trust",
              },
              {
                label: "Trust bands",
                value: String(data.trust.breakdown.length),
                sub: "group_scores",
              },
            ].map((k) => (
              <div key={k.label} className="rounded-xl border border-border bg-card p-4">
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {k.label}
                </div>
                <div className="mt-1 text-2xl font-semibold tracking-tight">{k.value}</div>
                <div className="text-xs text-muted-foreground">{k.sub}</div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Demo timeline (narrative)</h3>
            <span className="text-xs text-muted-foreground">Not live evaluator timing</span>
          </div>
          <ol className="relative border-l border-border pl-6">
            {timeline.map((s, i) => (
              <li
                key={s.t}
                className="group relative pb-5 last:pb-0 animate-fade-in"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <span className="absolute -left-[29px] top-1 flex h-3 w-3 items-center justify-center rounded-full border-2 border-primary bg-background transition-transform group-hover:scale-125" />
                <div className="flex items-baseline gap-3">
                  <span className="text-[11px] font-medium tabular-nums text-primary">{s.t}</span>
                  <span className="text-sm font-medium text-foreground">{s.label}</span>
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">{s.detail}</div>
              </li>
            ))}
          </ol>
        </div>
        <div className="grid gap-3">
          {[
            {
              to: "/conversation",
              icon: MessagesSquare,
              label: "Conversation viewer",
              desc: "Synthetic dialog (narrative).",
            },
            {
              to: "/assessment",
              icon: ClipboardList,
              label: "Assessment domains",
              desc: "Live POST /assessment.",
            },
            {
              to: "/trustscore",
              icon: ShieldCheck,
              label: "TrustScore breakdown",
              desc: "Live POST /trust.",
            },
            {
              to: "/evaluation",
              icon: GaugeCircle,
              label: "Evaluation results",
              desc: "Live POST /evaluate.",
            },
          ].map(({ to, icon: Icon, label, desc }) => (
            <Link
              key={to}
              to={to}
              className="group rounded-xl border border-border bg-card p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-soft text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{label}</span>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </div>
                  <div className="text-xs text-muted-foreground">{desc}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
