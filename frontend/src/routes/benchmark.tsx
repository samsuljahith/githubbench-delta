import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, PageHeader } from "@/components/AppLayout";
import { ErrorBlock, InsufficientBlock, LoadingBlock } from "@/components/ApiStates";
import { useAsyncResource } from "@/hooks/useApiQuery";
import {
  defaultExperimentId,
  postEvaluate,
  postMemorization,
  postTrust,
  type EvalMetric,
  type TrustData,
} from "@/lib/api";
import { Download, FileText } from "lucide-react";
import { patients } from "@/lib/demo-data";

export const Route = createFileRoute("/benchmark")({
  head: () => ({
    meta: [
      { title: "Benchmark Report · ElderWise" },
      {
        name: "description",
        content: "Live GitHubBench-Delta trust + evaluate snapshot for the default experiment.",
      },
      { property: "og:title", content: "Benchmark Report · ElderWise" },
      { property: "og:description", content: "Real evaluator metrics — no fabricated baselines." },
    ],
  }),
  component: BenchmarkPage,
});

type Bundle = {
  trust: TrustData;
  metrics: EvalMetric[];
  experimentId: string;
  memorizationOk: boolean;
  memorizationNote: string;
};

async function loadBundle(): Promise<Bundle> {
  const eid = defaultExperimentId();
  const [trustEnv, evalEnv, memEnv] = await Promise.all([
    postTrust(eid),
    postEvaluate(eid),
    postMemorization([eid]),
  ]);
  if (!trustEnv.ok || !trustEnv.data) {
    throw new Error(trustEnv.detail || "insufficient_data for trust");
  }
  if (!evalEnv.ok || !evalEnv.data?.metrics?.length) {
    throw new Error(evalEnv.detail || "insufficient_data for evaluate");
  }
  return {
    trust: trustEnv.data,
    metrics: evalEnv.data.metrics,
    experimentId: trustEnv.experiment_id || eid,
    memorizationOk: memEnv.ok,
    memorizationNote: memEnv.ok
      ? "MDS report available via POST /memorization"
      : memEnv.detail || "MDS insufficient_data",
  };
}

function metricPct(metrics: EvalMetric[], keys: string[]): number {
  const hit = metrics.find((m) => keys.some((k) => m.key.includes(k)));
  return hit ? Math.round(hit.value) : 0;
}

function BenchmarkPage() {
  const p = patients[0];
  const { data, error, loading, reload } = useAsyncResource(loadBundle);

  const download = () => {
    if (!data) return;
    const payload = {
      run: data.experimentId,
      evaluator: "GitHubBench-Delta",
      patient: { id: p.id, synthetic: true, presentation: p.chiefComplaint },
      trustScore: data.trust.overall,
      band: data.trust.band,
      metrics: data.metrics.map((m) => ({
        key: m.key,
        label: m.label,
        value: m.value,
        target: m.target,
        unit: m.unit,
      })),
      comparisons: [
        {
          model: `Live experiment ${data.experimentId}`,
          trust: data.trust.overall,
          faith: metricPct(data.metrics, ["ground", "faith", "consistency"]),
          cover: metricPct(data.metrics, ["coverage", "task_resolution", "engineering"]),
          safety: metricPct(data.metrics, ["safety"]),
        },
      ],
      memorization: data.memorizationNote,
      note: "Synthetic patient chrome only. Metrics and TrustScore are live API outputs.",
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "elderwise-benchmark-report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Comparative" title="Benchmark Report" description="Loading…" />
        <LoadingBlock />
      </AppLayout>
    );
  }
  if (error) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Comparative" title="Benchmark Report" description="Failed." />
        <ErrorBlock message={error} onRetry={reload} />
      </AppLayout>
    );
  }
  if (!data) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Comparative" title="Benchmark Report" description="No data." />
        <InsufficientBlock />
      </AppLayout>
    );
  }

  const row = {
    model: `Live · ${data.experimentId}`,
    trust: data.trust.overall,
    faith: metricPct(data.metrics, ["ground", "consistency", "faith"]),
    cover: metricPct(data.metrics, ["task_resolution", "engineering", "coverage"]),
    safety: metricPct(data.metrics, ["safety"]),
  };

  return (
    <AppLayout>
      <PageHeader
        eyebrow="Comparative"
        title="Benchmark Report"
        description="Live TrustScore + evaluate metrics for the default experiment. Fabricated baseline rows were removed."
        actions={
          <button
            onClick={download}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <Download className="h-4 w-4" /> Download report
          </button>
        }
      />

      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-secondary/60 text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-5 py-3 text-left font-medium">Model</th>
              <th className="px-5 py-3 text-right font-medium">TrustScore</th>
              <th className="px-5 py-3 text-right font-medium">Grounding-ish</th>
              <th className="px-5 py-3 text-right font-medium">Coverage-ish</th>
              <th className="px-5 py-3 text-right font-medium">Safety</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-border bg-primary-soft/40">
              <td className="px-5 py-4">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">{row.model}</span>
                  <span className="rounded-md bg-primary px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary-foreground">
                    Current
                  </span>
                </div>
              </td>
              {[row.trust, row.faith, row.cover, row.safety].map((v, j) => (
                <td key={j} className="px-5 py-4 text-right">
                  <div className="flex items-center justify-end gap-3">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-secondary">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${v}%` }} />
                    </div>
                    <span className="w-8 text-right font-medium tabular-nums">{v}</span>
                  </div>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <FileText className="h-4 w-4 text-primary" /> Narrative chrome
          </div>
          <p className="mt-3 text-sm leading-relaxed text-foreground/90">
            Synthetic case {p.id} ({p.name}) is UI narrative only. Evaluator numbers above come from
            the API.
          </p>
          <p className="mt-3 text-xs text-muted-foreground">
            TrustScore {data.trust.overall} · {data.memorizationNote}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="text-sm font-semibold">What's in the report</div>
          <ul className="mt-3 space-y-2 text-sm text-foreground/90">
            <li>• Synthetic case metadata (patient marked SYNTHETIC)</li>
            <li>• Live POST /evaluate metrics</li>
            <li>• Live POST /trust composite</li>
            <li>• Memorization status via POST /memorization</li>
            <li>• No invented baseline competitor rows</li>
          </ul>
        </div>
      </div>
    </AppLayout>
  );
}
