import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, PageHeader } from "@/components/AppLayout";
import { insights } from "@/lib/demo-data";
import { Lightbulb } from "lucide-react";

export const Route = createFileRoute("/insights")({
  head: () => ({
    meta: [
      { title: "Research Insights · ElderWise" },
      {
        name: "description",
        content:
          "Findings drawn from GitHubBench-Delta evaluation runs of the ElderWise Rapid Geriatric Assessment.",
      },
      { property: "og:title", content: "Research Insights · ElderWise" },
      { property: "og:description", content: "What we learned across evaluation runs." },
    ],
  }),
  component: InsightsPage,
});

const chart = [
  { v: "v0.1", score: 52 },
  { v: "v0.2", score: 64 },
  { v: "v0.3", score: 79 },
  { v: "v0.4", score: 86 },
];

function InsightsPage() {
  const max = Math.max(...chart.map((c) => c.score));
  return (
    <AppLayout>
      <PageHeader
        eyebrow="Findings"
        title="Research Insights"
        description="Narrative research notes for the demo UI — not live evaluator outputs. Use Assessment / Evaluation / TrustScore pages for API-backed numbers."
      />

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6">
          <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            TrustScore over model versions
          </div>
          <div className="mt-6 flex h-48 items-end gap-6">
            {chart.map((c, i) => (
              <div key={c.v} className="flex flex-1 flex-col items-center gap-2">
                <div className="flex w-full flex-1 items-end">
                  <div
                    className="w-full rounded-t-md bg-gradient-to-t from-primary/80 to-primary transition-all duration-700"
                    style={{
                      height: `${(c.score / max) * 100}%`,
                      animationDelay: `${i * 80}ms`,
                    }}
                  />
                </div>
                <div className="text-[11px] text-muted-foreground">{c.v}</div>
                <div className="text-xs font-semibold tabular-nums">{c.score}</div>
              </div>
            ))}
          </div>
          <p className="mt-6 text-xs text-muted-foreground">
            +34 point improvement from v0.1 → v0.4, driven mainly by evidence grounding and
            safety-flag recall.
          </p>
        </div>

        <div className="lg:col-span-3 grid gap-3">
          {insights.map((ins, i) => (
            <div
              key={ins.title}
              className="animate-fade-in group flex gap-4 rounded-2xl border border-border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
                <Lightbulb className="h-4 w-4" />
              </div>
              <div>
                <div className="text-sm font-semibold text-foreground">{ins.title}</div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{ins.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-border bg-card p-6">
        <div className="text-sm font-semibold">Methodology note</div>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
          All insights are derived from GitHubBench-Delta evaluator outputs on synthetic
          geriatric cases. No real patient data was used. Insights that could not be supported by
          evaluator metrics are excluded.
        </p>
      </div>
    </AppLayout>
  );
}
