import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  Users,
  MessagesSquare,
  ClipboardList,
  GaugeCircle,
  ShieldCheck,
  BarChart3,
  Lightbulb,
  Activity,
} from "lucide-react";
import { defaultExperimentId, getHealth } from "@/lib/api";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/patients", label: "Synthetic Patients", icon: Users },
  { to: "/conversation", label: "Conversation", icon: MessagesSquare },
  { to: "/assessment", label: "Assessment", icon: ClipboardList },
  { to: "/evaluation", label: "Evaluation", icon: GaugeCircle },
  { to: "/trustscore", label: "TrustScore", icon: ShieldCheck },
  { to: "/benchmark", label: "Benchmark Report", icon: BarChart3 },
  { to: "/insights", label: "Research Insights", icon: Lightbulb },
] as const;

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

export function AppLayout({ children }: { children?: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex max-w-[1400px]">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar px-4 py-6 md:flex">
          <Link to="/" className="mb-8 flex items-center gap-2 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Activity className="h-4.5 w-4.5" strokeWidth={2.4} />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold tracking-tight">ElderWise</span>
              <span className="text-[10.5px] uppercase tracking-[0.14em] text-muted-foreground">
                Evaluation Demo
              </span>
            </div>
          </Link>

          <nav className="flex flex-col gap-0.5">
            {nav.map(({ to, label, icon: Icon }) => {
              const active = to === "/" ? pathname === "/" : pathname.startsWith(to);
              return (
                <Link
                  key={to}
                  to={to}
                  className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    active
                      ? "bg-primary-soft text-primary font-medium"
                      : "text-sidebar-foreground/80 hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" strokeWidth={active ? 2.4 : 1.9} />
                  {label}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto rounded-xl border border-border bg-card p-3 text-xs text-muted-foreground">
            <div className="mb-1 font-medium text-foreground">GitHubBench-Delta</div>
            Thin UI · live facade APIs · experiment {defaultExperimentId().slice(0, 14)}…
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur">
            <div className="flex items-center gap-3">
              <HealthPill />
              <span className="hidden text-xs text-muted-foreground sm:inline">
                Exp · {defaultExperimentId()}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="hidden sm:inline">Backend source of truth</span>
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
          <div className="mb-2 text-[11px] font-medium uppercase tracking-[0.14em] text-primary">
            {eyebrow}
          </div>
        )}
        <h1 className="text-3xl font-semibold tracking-tight text-foreground md:text-[34px]">
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
    <span className="inline-flex items-center gap-1.5 rounded-md border border-warning/40 bg-warning/10 px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-warning">
      Synthetic{id ? ` · ${id}` : ""}
    </span>
  );
}
