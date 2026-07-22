import { createFileRoute, redirect } from "@tanstack/react-router";
import { parseSetupSearch } from "@/lib/patient";

/** Legacy route → unified patient dashboard section. */
export const Route = createFileRoute("/trustscore")({
  validateSearch: parseSetupSearch,
  beforeLoad: ({ search }) => {
    throw redirect({ to: "/", search, hash: "trust" });
  },
  component: () => null,
});
