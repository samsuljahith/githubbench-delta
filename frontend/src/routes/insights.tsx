import { createFileRoute, redirect } from "@tanstack/react-router";
import { parseSetupSearch } from "@/lib/patient";

/** Legacy route → unified patient dashboard section (live-derived insights). */
export const Route = createFileRoute("/insights")({
  validateSearch: parseSetupSearch,
  beforeLoad: ({ search }) => {
    throw redirect({ to: "/", search, hash: "insights" });
  },
  component: () => null,
});
