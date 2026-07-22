import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, PageHeader } from "@/components/AppLayout";
import { ErrorBlock, InsufficientBlock, LoadingBlock } from "@/components/ApiStates";
import { useAsyncResource } from "@/hooks/useApiQuery";
import { postTrust } from "@/lib/api";
import { ShieldCheck } from "lucide-react";

export const Route = createFileRoute("/trustscore")({
  head: () => ({
    meta: [
      { title: "TrustScore · ElderWise" },
      {
        name: "description",
        content:
          "Trust composite from equal-weight GitHubBench-Delta group_scores (live experiment).",
      },
      { property: "og:title", content: "TrustScore · ElderWise" },
      { property: "og:description", content: "Composite trust indicator from real group_scores." },
    ],
  }),
  component: TrustScorePage,
});

function TrustScorePage() {
  const { data: envelope, error, loading, reload } = useAsyncResource(() => postTrust());

  if (loading) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Composite" title="TrustScore" description="Loading…" />
        <LoadingBlock />
      </AppLayout>
    );
  }
  if (error) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Composite" title="TrustScore" description="Failed." />
        <ErrorBlock message={error} onRetry={reload} />
      </AppLayout>
    );
  }
  if (!envelope?.ok || !envelope.data) {
    return (
      <AppLayout>
        <PageHeader eyebrow="Composite" title="TrustScore" description="No data." />
        <InsufficientBlock detail={envelope?.detail} />
      </AppLayout>
    );
  }

  const { overall, band, breakdown, method } = envelope.data;
  const circ = 2 * Math.PI * 54;
  const dash = (overall / 100) * circ;

  return (
    <AppLayout>
      <PageHeader
        eyebrow="Composite"
        title="TrustScore"
        description={`Equal-weight mean of evaluation.group_scores × 100 via POST /trust. Experiment ${envelope.experiment_id}.`}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <ShieldCheck className="h-3.5 w-3.5 text-primary" /> This run
          </div>
          <div className="mt-6 flex flex-col items-center">
            <div className="relative h-40 w-40">
              <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
                <circle cx="60" cy="60" r="54" strokeWidth="10" className="fill-none stroke-secondary" />
                <circle
                  cx="60"
                  cy="60"
                  r="54"
                  strokeWidth="10"
                  strokeLinecap="round"
                  className="fill-none stroke-primary transition-all duration-1000"
                  style={{ strokeDasharray: `${dash} ${circ}` }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="text-4xl font-semibold tracking-tight">{overall}</div>
                <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground">
                  / 100
                </div>
              </div>
            </div>
            <div className="mt-4 rounded-full bg-primary-soft px-3 py-1 text-xs font-medium text-primary">
              {band}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm font-semibold">Breakdown</div>
            <div className="text-xs text-muted-foreground">{method || "Weighted composite"}</div>
          </div>
          <div className="space-y-4">
            {breakdown.map((b, i) => (
              <div key={b.name} className="animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span>{b.name}</span>
                  <span className="tabular-nums text-muted-foreground">{b.value}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-700"
                    style={{ width: `${b.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {[
          { band: "0–49", label: "Not clinically usable", cls: "border-destructive/30 text-destructive" },
          { band: "50–74", label: "Assistive with review", cls: "border-warning/30 text-warning" },
          { band: "75–100", label: "Trusted with oversight", cls: "border-success/30 text-success" },
        ].map((b) => (
          <div key={b.band} className={`rounded-xl border bg-card p-4 text-sm ${b.cls}`}>
            <div className="font-semibold">{b.band}</div>
            <div className="mt-1 text-xs opacity-80">{b.label}</div>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
