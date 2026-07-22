import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, PageHeader, SyntheticBadge } from "@/components/AppLayout";
import { ErrorBlock, InsufficientBlock, LoadingBlock } from "@/components/ApiStates";
import { useAsyncResource } from "@/hooks/useApiQuery";
import { postAssessment } from "@/lib/api";
import { CheckCircle2, AlertTriangle, Circle } from "lucide-react";

export const Route = createFileRoute("/assessment")({
  head: () => ({
    meta: [
      { title: "Structured Assessment · ElderWise" },
      {
        name: "description",
        content:
          "Assessment domains derived from GitHubBench-Delta evaluation.group_scores for a real experiment.",
      },
      { property: "og:title", content: "Structured Assessment · ElderWise" },
      { property: "og:description", content: "Live group_scores mapped to assessment domains." },
    ],
  }),
  component: AssessmentPage,
});

const flagMeta = {
  normal: { icon: CheckCircle2, cls: "text-success", label: "Normal" },
  watch: { icon: Circle, cls: "text-warning", label: "Watch" },
  concern: { icon: AlertTriangle, cls: "text-destructive", label: "Concern" },
} as const;

function AssessmentPage() {
  const { data: envelope, error, loading, reload } = useAsyncResource(() => postAssessment());

  if (loading) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Live API" title="Assessment" description="Loading group_scores…" />
        <LoadingBlock />
      </AppLayout>
    );
  }
  if (error) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Live API" title="Assessment" description="Failed to load." />
        <ErrorBlock message={error} onRetry={reload} />
      </AppLayout>
    );
  }
  if (!envelope?.ok || !envelope.data) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Live API" title="Assessment" description="No real artifacts." />
        <InsufficientBlock detail={envelope?.detail} />
      </AppLayout>
    );
  }

  const { domains, subject, method } = envelope.data;
  const totalScore = domains.reduce((s, d) => s + d.score, 0);
  const totalMax = domains.reduce((s, d) => s + d.max, 0);
  const flagged = domains.filter((d) => d.flag !== "normal").length;

  return (
    <AppLayout>
      <PageHeader
        eyebrow="GitHubBench-Delta"
        title="Assessment domains"
        description="Domains are mean evaluation.group_scores from the live experiment, scaled 0–5. Not a clinical RGA — backend is the source of truth."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          {domains.map((d, i) => {
            const meta = flagMeta[d.flag] ?? flagMeta.watch;
            const Icon = meta.icon;
            const pct = (d.score / d.max) * 100;
            return (
              <div
                key={d.domain}
                className="animate-fade-in rounded-xl border border-border bg-card p-4"
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
                    <div className="text-sm font-semibold tabular-nums">
                      {d.score}
                      <span className="text-muted-foreground">/{d.max}</span>
                    </div>
                    <div className={`text-[10.5px] font-medium uppercase tracking-wider ${meta.cls}`}>
                      {meta.label}
                    </div>
                  </div>
                </div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Experiment subject
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="font-semibold">{subject.name}</span>
              <SyntheticBadge id={subject.id} />
            </div>
            <div className="mt-4 text-[11px] uppercase tracking-wider text-muted-foreground">
              Composite
            </div>
            <div className="mt-1 text-4xl font-semibold tracking-tight text-primary">
              {totalScore.toFixed(1)}
              <span className="text-lg text-muted-foreground">/{totalMax}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {flagged} domain{flagged === 1 ? "" : "s"} flagged · {envelope.experiment_id}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Provenance
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              {method || "Mapped from evaluation_results.json"} · source{" "}
              {subject.source || "backend"}
            </p>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-secondary/60 p-3 text-[11px] leading-relaxed text-foreground/90">
              {JSON.stringify(
                {
                  experiment_id: envelope.experiment_id,
                  agents: subject.agents,
                  domains: domains.map((d) => ({
                    domain: d.domain,
                    score: d.score,
                    flag: d.flag,
                  })),
                },
                null,
                2,
              )}
            </pre>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
