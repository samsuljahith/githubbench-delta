import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, PageHeader } from "@/components/AppLayout";
import { ErrorBlock, InsufficientBlock, LoadingBlock } from "@/components/ApiStates";
import { useAsyncResource } from "@/hooks/useApiQuery";
import { postEvaluate } from "@/lib/api";
import { TrendingUp, TrendingDown } from "lucide-react";

export const Route = createFileRoute("/evaluation")({
  head: () => ({
    meta: [
      { title: "Evaluation Results · ElderWise" },
      {
        name: "description",
        content: "Live GitHubBench-Delta metric averages from evaluation_results.json.",
      },
      { property: "og:title", content: "Evaluation Results · ElderWise" },
      { property: "og:description", content: "Real evaluator metrics for the selected experiment." },
    ],
  }),
  component: EvaluationPage,
});

function EvaluationPage() {
  const { data: envelope, error, loading, reload } = useAsyncResource(() => postEvaluate());

  if (loading) {
    return (
      <AppLayout>
        <PageHeader eyebrow="GitHubBench-Delta" title="Evaluation Results" description="Loading…" />
        <LoadingBlock />
      </AppLayout>
    );
  }
  if (error) {
    return (
      <AppLayout>
        <PageHeader eyebrow="GitHubBench-Delta" title="Evaluation Results" description="Failed." />
        <ErrorBlock message={error} onRetry={reload} />
      </AppLayout>
    );
  }
  if (!envelope?.ok || !envelope.data?.metrics?.length) {
    return (
      <AppLayout>
        <PageHeader eyebrow="GitHubBench-Delta" title="Evaluation Results" description="No data." />
        <InsufficientBlock detail={envelope?.detail} />
      </AppLayout>
    );
  }

  const { metrics, n_rows, source } = envelope.data;

  return (
    <AppLayout>
      <PageHeader
        eyebrow="GitHubBench-Delta"
        title="Evaluation Results"
        description={`Metrics from ${source || "evaluation_results"} (${n_rows} rows). Experiment ${envelope.experiment_id}. Nothing here is fabricated.`}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {metrics.map((m, i) => {
          const isLowerBetter = m.key.includes("hallucin") || m.key.includes("unnecessary");
          const passes = isLowerBetter ? m.value <= m.target : m.value >= m.target;
          const Icon = passes ? TrendingUp : TrendingDown;
          const barMax = m.unit === "%" ? 100 : 5;
          const pct = Math.min(100, (m.value / barMax) * 100);
          return (
            <div
              key={m.key}
              className="animate-fade-in rounded-2xl border border-border bg-card p-5"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <div className="flex items-start justify-between">
                <div className="text-sm font-medium text-foreground">{m.label}</div>
                <span
                  className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10.5px] font-medium ${
                    passes ? "bg-success/10 text-success" : "bg-warning/10 text-warning"
                  }`}
                >
                  <Icon className="h-3 w-3" />
                  {passes ? "Above target" : "Below target"}
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-1.5">
                <span className="text-3xl font-semibold tabular-nums tracking-tight">{m.value}</span>
                <span className="text-sm text-muted-foreground">
                  {m.unit === "%" ? "%" : "/5"}
                </span>
                <span className="ml-auto text-[11px] text-muted-foreground">
                  target {m.target}
                  {m.unit === "%" ? "%" : ""}
                </span>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-secondary">
                <div
                  className={`h-full rounded-full transition-all ${passes ? "bg-primary" : "bg-warning"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{m.description}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-6 rounded-2xl border border-border bg-card p-6">
        <div className="text-sm font-semibold">How this is scored</div>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
          Values are mean metric scores from GitHubBench-Delta evaluation artifacts via{" "}
          <code className="text-xs">POST /evaluate</code>. The UI does not invent numbers.
        </p>
      </div>
    </AppLayout>
  );
}
