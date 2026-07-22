import { createFileRoute } from "@tanstack/react-router";
import { AppLayout, PageHeader, SyntheticBadge } from "@/components/AppLayout";
import { conversation, patients } from "@/lib/demo-data";
import { Sparkles, User, Stethoscope } from "lucide-react";

export const Route = createFileRoute("/conversation")({
  head: () => ({
    meta: [
      { title: "Conversation Viewer · ElderWise" },
      {
        name: "description",
        content:
          "Replay the clinician-patient-assistant dialog that feeds the ElderWise Rapid Geriatric Assessment.",
      },
      { property: "og:title", content: "Conversation Viewer · ElderWise" },
      {
        property: "og:description",
        content: "Streamed dialog for RGA evaluation.",
      },
    ],
  }),
  component: ConversationPage,
});

const roleMeta = {
  assistant: { label: "ElderWise", icon: Sparkles, className: "bg-primary text-primary-foreground" },
  patient: { label: "Patient", icon: User, className: "bg-secondary text-foreground" },
  clinician: { label: "Clinician", icon: Stethoscope, className: "bg-accent text-accent-foreground" },
} as const;

function ConversationPage() {
  const p = patients[0];
  return (
    <AppLayout>
      <PageHeader
        eyebrow="Transcript"
        title="Conversation Viewer"
        description="Time-aligned dialog streamed to the model. Turns are grounded evidence for the structured assessment."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-sm">
        <SyntheticBadge id={p.id} />
        <span className="font-medium">{p.name}</span>
        <span className="text-muted-foreground">
          · {p.age}{p.sex} · {p.chiefComplaint}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">13 turns · 2m 41s</span>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5 md:p-8">
        <div className="mx-auto max-w-3xl space-y-5">
          {conversation.map((turn, i) => {
            const meta = roleMeta[turn.role];
            const Icon = meta.icon;
            const isPatient = turn.role === "patient";
            return (
              <div
                key={i}
                className={`animate-fade-in flex gap-3 ${isPatient ? "flex-row-reverse" : ""}`}
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.className}`}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className={`max-w-[78%] ${isPatient ? "items-end text-right" : ""} flex flex-col`}>
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
                        : "rounded-tl-sm border border-border bg-background text-foreground"
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
    </AppLayout>
  );
}
