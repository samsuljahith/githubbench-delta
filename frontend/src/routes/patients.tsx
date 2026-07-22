import { createFileRoute, Link } from "@tanstack/react-router";
import { AppLayout, PageHeader, SyntheticBadge } from "@/components/AppLayout";
import { patients } from "@/lib/demo-data";
import { ArrowRight, ShieldAlert } from "lucide-react";

export const Route = createFileRoute("/patients")({
  head: () => ({
    meta: [
      { title: "Synthetic Patients · ElderWise" },
      {
        name: "description",
        content:
          "Realistic synthetic geriatric cases used to evaluate the ElderWise assessment workflow. No real patient data.",
      },
      { property: "og:title", content: "Synthetic Patients · ElderWise" },
      {
        property: "og:description",
        content: "Synthetic geriatric cases for AI evaluation.",
      },
    ],
  }),
  component: PatientsPage,
});

const riskColor: Record<string, string> = {
  High: "text-destructive bg-destructive/10 border-destructive/30",
  Moderate: "text-warning bg-warning/10 border-warning/30",
  Low: "text-success bg-success/10 border-success/30",
};

function PatientsPage() {
  return (
    <AppLayout>
      <PageHeader
        eyebrow="Cohort"
        title="Synthetic Patients"
        description="Every case is fully synthetic and generated for evaluation. No real patient information is used or stored."
      />

      <div className="mb-6 flex items-start gap-3 rounded-xl border border-warning/40 bg-warning/5 p-4 text-sm">
        <ShieldAlert className="mt-0.5 h-4 w-4 text-warning" />
        <div>
          <div className="font-medium text-foreground">All records marked SYNTHETIC</div>
          <div className="text-xs text-muted-foreground">
            Cases are generated to reflect realistic geriatric presentations. They are not derived
            from real medical records.
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {patients.map((p, i) => (
          <div
            key={p.id}
            className="animate-fade-in group flex flex-col rounded-2xl border border-border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold">{p.name}</h3>
                  <SyntheticBadge />
                </div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {p.id} · {p.age}{p.sex} · {p.livingSituation}
                </div>
              </div>
              <span
                className={`rounded-md border px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider ${riskColor[p.riskProfile]}`}
              >
                {p.riskProfile} risk
              </span>
            </div>

            <p className="mt-3 text-sm text-foreground/90">{p.chiefComplaint}</p>

            <div className="mt-4 space-y-2 text-xs">
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground">
                  Comorbidities
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {p.comorbidities.map((c) => (
                    <span key={c} className="rounded-md bg-secondary px-2 py-0.5 text-foreground/80">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground">
                  Medications
                </div>
                <div className="mt-1 text-muted-foreground">{p.medications.join(" · ")}</div>
              </div>
            </div>

            <Link
              to="/conversation"
              className="mt-5 inline-flex items-center gap-1 self-start text-xs font-medium text-primary hover:underline"
            >
              Open conversation <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
