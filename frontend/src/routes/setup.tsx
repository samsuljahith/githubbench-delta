import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppLayout, PageHeader } from "@/components/AppLayout";
import { ErrorBlock, LoadingBlock } from "@/components/ApiStates";
import { getCaseAgents, getFixturePatients, type CaseAgentInfo } from "@/lib/api";
import {
  isAllowedAgent,
  parseSetupSearch,
  setupSearchLink,
  type AllowedAgent,
} from "@/lib/patient";
import { apiPatientToUi, saveSyntheticCohort } from "@/lib/syntheticStore";
import { ArrowRight, Check, Cloud, HardDrive, FolderOpen } from "lucide-react";

export const Route = createFileRoute("/setup")({
  validateSearch: parseSetupSearch,
  head: () => ({
    meta: [
      { title: "Setup · ElderWise" },
      {
        name: "description",
        content:
          "Pick an agent, load the five fixed synthetic fixtures, then open Synthetic Patients.",
      },
    ],
  }),
  component: SetupPage,
});

function SetupPage() {
  const search = Route.useSearch();
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(search.agent ? 2 : 1);
  const [agents, setAgents] = useState<CaseAgentInfo[] | null>(null);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [pickedAgent, setPickedAgent] = useState<AllowedAgent | undefined>(search.agent);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCaseAgents()
      .then((rows) => {
        if (!cancelled) setAgents(rows);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setAgentsError(err instanceof Error ? err.message : "Failed to load agents");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const continueToGenerate = () => {
    if (!pickedAgent) return;
    setStep(2);
    void navigate({
      to: "/setup",
      search: setupSearchLink({ agent: pickedAgent }),
    });
  };

  const loadFixtures = async () => {
    if (!pickedAgent) return;
    setGenerating(true);
    setGenError(null);
    try {
      const env = await getFixturePatients();
      if (!env.ok || !env.data?.patients?.length) {
        throw new Error(env.detail || "No fixture patients found");
      }
      const batchId = "fixtures-v1";
      const generatedAt = new Date().toISOString();
      const ui = env.data.patients.map((p) =>
        apiPatientToUi(p, { batchId, generatedAt, source: "fixture" }),
      );
      saveSyntheticCohort(ui, batchId);
      void navigate({
        to: "/patients",
        search: setupSearchLink({ agent: pickedAgent }),
      });
    } catch (err: unknown) {
      setGenError(err instanceof Error ? err.message : "Failed to load fixtures");
      setGenerating(false);
    }
  };

  return (
    <AppLayout allowIncomplete>
      <PageHeader
        eyebrow="Setup"
        title={step === 1 ? "Choose an agent" : "Load demo patients"}
        description={
          step === 1
            ? "This model runs the live GitHub engineering assessment. Scores come from deterministic evaluators — not an LLM judge. Prefer MiniCPM for local / offline."
            : "Load the five versioned fixtures from datasets/synthetic/ (one of each scenario_type). Reproducible for the Saturday demo — not regenerated randomly."
        }
      />

      <div className="mb-8 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span
          className={`rounded-full px-3 py-1 ${step === 1 ? "bg-primary text-primary-foreground font-medium" : "bg-secondary"}`}
        >
          1 · agent
        </span>
        <ArrowRight className="h-3 w-3" />
        <span
          className={`rounded-full px-3 py-1 ${step === 2 ? "bg-primary text-primary-foreground font-medium" : "bg-secondary"}`}
        >
          2 · fixtures
        </span>
        <ArrowRight className="h-3 w-3" />
        <span className="rounded-full bg-secondary px-3 py-1">3 · pick patient</span>
      </div>

      {step === 1 && (
        <>
          {!agents && !agentsError && <LoadingBlock label="Loading available agents…" />}
          {agentsError && <ErrorBlock message={agentsError} />}
          {agents && (
            <div className="grid gap-4 md:grid-cols-3">
              {agents.map((a, i) => {
                const selected = pickedAgent === a.id;
                const Icon = a.deployment === "local" ? HardDrive : Cloud;
                return (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => {
                      if (isAllowedAgent(a.id)) setPickedAgent(a.id);
                    }}
                    className={`glass-card group animate-fade-in relative overflow-hidden rounded-2xl p-6 text-left transition-all hover:-translate-y-0.5 hover:shadow-md ${
                      selected ? "ring-2 ring-primary/50" : ""
                    }`}
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <div
                      className={`absolute inset-x-0 top-0 h-1 ${selected ? "bg-primary" : "bg-transparent group-hover:bg-primary/40"}`}
                    />
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-soft text-primary">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="font-display text-lg font-semibold">{a.label}</div>
                          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                            {a.deployment}
                          </div>
                        </div>
                      </div>
                      {selected && (
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                          <Check className="h-3.5 w-3.5" />
                        </span>
                      )}
                    </div>
                    <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{a.hint}</p>
                  </button>
                );
              })}
            </div>
          )}
          <div className="mt-8 flex justify-end">
            <button
              type="button"
              disabled={!pickedAgent}
              onClick={continueToGenerate}
              className="inline-flex items-center gap-1.5 rounded-full bg-primary px-5 py-2.5 text-sm font-medium lowercase text-primary-foreground disabled:opacity-40"
            >
              continue <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </>
      )}

      {step === 2 && (
        <>
          <div className="glass-card mx-auto max-w-xl rounded-2xl p-8 text-center md:p-10">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-soft text-primary">
              <FolderOpen className="h-6 w-6" />
            </div>
            <p className="text-sm text-muted-foreground">
              agent · <span className="font-medium text-foreground">{pickedAgent}</span>
            </p>
            <button
              type="button"
              className="mt-2 text-xs text-primary hover:underline"
              onClick={() => setStep(1)}
            >
              change agent
            </button>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Loads five fixed caregiver conversations from the repo (
              <code className="text-xs">datasets/synthetic/</code>
              ): complete, missing_finding, hallucination_risk, contraindication, incomplete.
            </p>
            <button
              type="button"
              disabled={generating}
              onClick={() => void loadFixtures()}
              className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-medium lowercase tracking-wide text-primary-foreground shadow-sm disabled:opacity-50"
            >
              <FolderOpen className="h-4 w-4" />
              {generating ? "loading…" : "load fixture patients"}
            </button>
          </div>

          {generating && (
            <div className="mt-6">
              <LoadingBlock label="Loading versioned synthetic fixtures…" />
            </div>
          )}
          {genError && (
            <div className="mt-6">
              <ErrorBlock message={genError} onRetry={() => void loadFixtures()} />
            </div>
          )}

          <div className="mt-6 flex justify-start">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="rounded-full border border-border bg-card px-4 py-2 text-sm lowercase"
            >
              back
            </button>
          </div>
        </>
      )}
    </AppLayout>
  );
}
