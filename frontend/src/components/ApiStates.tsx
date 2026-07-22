/** Shared loading / error / empty banners for API-backed pages. */

export function LoadingBlock({ label = "Loading from GitHubBench-Delta…" }: { label?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
      <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      {label}
    </div>
  );
}

export function ErrorBlock({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-destructive/30 bg-card p-6">
      <div className="text-sm font-semibold text-destructive">Could not load data</div>
      <p className="mt-2 text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function InsufficientBlock({
  detail,
  onForceRetry,
}: {
  detail?: string | null;
  onForceRetry?: () => void;
}) {
  return (
    <div className="rounded-2xl border border-warning/30 bg-card p-6">
      <div className="text-sm font-semibold text-warning">insufficient_data</div>
      <p className="mt-2 text-sm text-muted-foreground">
        {detail ||
          "No evaluation artifacts for this experiment. The API does not invent scores."}
      </p>
      {onForceRetry && (
        <button
          type="button"
          onClick={onForceRetry}
          className="mt-4 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
        >
          Force re-run
        </button>
      )}
    </div>
  );
}
