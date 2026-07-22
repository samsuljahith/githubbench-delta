import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { LayoutDashboard, Users, Activity, Settings2 } from "lucide-react";
import { getHealth } from "@/lib/api";
import {
  hasGeminiPatient,
  isSetupComplete,
  patientFromSearch,
  setupSearchLink,
  type AllowedAgent,
  type SetupSearch,
} from "@/lib/patient";

const nav = [
  { to: "/patients" as const, label: "Synthetic Patients", icon: Users },
  { to: "/" as const, label: "Patient Dashboard", icon: LayoutDashboard },
];

function HealthPill() {
  const [label, setLabel] = useState("API …");
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    getHealth()
      .then((h) => {
        setOk(h.status === "ok");
        setLabel(`API ${h.status} · v${h.version}`);
      })
      .catch(() => {
        setOk(false);
        setLabel("API unreachable");
      });
  }, []);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ${
        ok === true
          ? "bg-success/10 text-success"
          : ok === false
            ? "bg-destructive/10 text-destructive"
            : "bg-secondary text-muted-foreground"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          ok === true ? "bg-success" : ok === false ? "bg-destructive" : "bg-muted-foreground"
        }`}
      />
      {label}
    </span>
  );
}

function useSetupSearch(): SetupSearch {
  return useRouterState({
    select: (s) => {
      const search = s.location.search as SetupSearch | string;
      if (typeof search === "object" && search) {
        return {
          agent: search.agent,
          patient: search.patient,
        };
      }
      return {};
    },
  });
}

function SetupGate({ allowIncomplete }: { allowIncomplete?: boolean }) {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const search = useSetupSearch();

  useEffect(() => {
    if (allowIncomplete) return;
    if (pathname === "/setup") return;

    if (pathname === "/patients") {
      if (!search.agent) {
        void navigate({
          to: "/setup",
          search: setupSearchLink({ agent: search.agent, patient: search.patient }),
          replace: true,
        });
      }
      return;
    }

    if (!search.agent) {
      void navigate({
        to: "/setup",
        search: setupSearchLink({}),
        replace: true,
      });
      return;
    }
    if (!search.patient || !hasGeminiPatient(search)) {
      void navigate({
        to: "/patients",
        search: setupSearchLink({ agent: search.agent }),
        replace: true,
      });
    }
  }, [allowIncomplete, navigate, pathname, search]);

  return null;
}

export function AppLayout({
  children,
  allowIncomplete,
}: {
  children?: ReactNode;
  allowIncomplete?: boolean;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const setup = useSetupSearch();
  const complete = isSetupComplete(setup) && hasGeminiPatient(setup);
  const patient = patientFromSearch(setup);
  const agent = setup.agent as AllowedAgent | undefined;
  const search = setupSearchLink({
    agent: agent,
    patient: setup.patient,
  });

  const headerPatient =
    patient != null
      ? `${patient.id} · ${patient.name}`
      : setup.patient
        ? `${setup.patient} (regenerate cohort)`
        : "No patient";

  return (
    <div className="min-h-screen text-foreground">
      <SetupGate allowIncomplete={allowIncomplete} />
      <div className="mx-auto flex max-w-[1440px]">
        <aside className="sticky top-0 hidden h-screen w-[272px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar/90 px-4 py-6 backdrop-blur-md md:flex">
          <Link
            to={complete ? "/" : search.agent ? "/patients" : "/setup"}
            search={search}
            className="mb-10 flex items-center gap-3 px-2"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[oklch(0.58_0.1_165)] text-primary-foreground shadow-md">
              <Activity className="h-5 w-5" strokeWidth={2.4} />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="font-display text-lg font-semibold tracking-tight">ElderWise</span>
              <span className="text-[10.5px] uppercase tracking-[0.16em] text-muted-foreground">
                Evaluation
              </span>
            </div>
          </Link>

          <nav className="flex flex-col gap-1">
            <Link
              to="/setup"
              search={search}
              className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                pathname.startsWith("/setup")
                  ? "bg-primary text-primary-foreground font-medium shadow-sm"
                  : "text-sidebar-foreground/80 hover:bg-secondary hover:text-foreground"
              }`}
            >
              <Settings2 className="h-4 w-4" strokeWidth={pathname.startsWith("/setup") ? 2.4 : 1.9} />
              Setup
            </Link>
            {nav.map(({ to, label, icon: Icon }) => {
              const active = to === "/" ? pathname === "/" : pathname.startsWith(to);
              const locked = to === "/patients" ? !setup.agent : !complete;
              const fallbackTo = setup.agent ? "/patients" : "/setup";
              return (
                <Link
                  key={to}
                  to={locked ? fallbackTo : to}
                  search={
                    locked ? setupSearchLink({ agent: setup.agent }) : search
                  }
                  className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                    active && !locked
                      ? "bg-primary text-primary-foreground font-medium shadow-sm"
                      : "text-sidebar-foreground/80 hover:bg-secondary hover:text-foreground"
                  } ${locked ? "opacity-50" : ""}`}
                >
                  <Icon className="h-4 w-4" strokeWidth={active && !locked ? 2.4 : 1.9} />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="glass-card mt-auto rounded-2xl p-4 text-xs text-muted-foreground">
            <div className="mb-1 font-display text-sm font-semibold text-foreground">
              GitHubBench-Delta
            </div>
            {setup.agent ? (
              <>
                <div>
                  Agent · {agent}
                  {patient ? ` · ${patient.id}` : " · pick a patient"}
                </div>
                <div className="mt-1">Gemini patients · live evaluators</div>
              </>
            ) : (
              <div>Complete setup to unlock live scores</div>
            )}
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border/70 bg-background/70 px-6 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <HealthPill />
              <span className="hidden text-xs text-muted-foreground sm:inline">
                {setup.agent ? `${agent} · ${headerPatient}` : "Setup required"}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="hidden sm:inline">patient synthetic · scores live</span>
            </div>
          </header>
          <div className="animate-fade-in px-6 py-8 md:px-10 md:py-10">{children ?? <Outlet />}</div>
        </main>
      </div>
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        {eyebrow && (
          <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.16em] text-primary">
            {eyebrow}
          </div>
        )}
        <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground md:text-[36px]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function SyntheticBadge({ id }: { id?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/40 bg-warning/10 px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-warning">
      Synthetic{id ? ` · ${id}` : ""}
    </span>
  );
}
