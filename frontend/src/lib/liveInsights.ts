/** Derive Research Insights narrative from live case-run artifacts only. */

import type { CaseRunData, EvalMetric } from "@/lib/api";

export type LiveInsight = {
  title: string;
  body: string;
};

function metricPasses(m: EvalMetric): boolean {
  const isLowerBetter = m.key.includes("hallucin") || m.key.includes("unnecessary");
  return isLowerBetter ? m.value <= m.target : m.value >= m.target;
}

/**
 * Build insight cards from real TrustScore / metrics / loop data.
 * Returns [] when there is nothing real to show — never fabricates scores.
 */
export function deriveLiveInsights(data: CaseRunData): LiveInsight[] {
  const out: LiveInsight[] = [];
  const metrics = data.evaluate?.metrics ?? [];
  const trust = data.trust;

  if (trust) {
    const top = [...(trust.breakdown || [])].sort((a, b) => b.value - a.value).slice(0, 3);
    out.push({
      title: `TrustScore ${trust.overall} / 100`,
      body:
        `Band: ${trust.band}.` +
        (top.length
          ? ` Strongest live group_scores: ${top.map((b) => `${b.name} ${b.value}`).join("; ")}.`
          : ""),
    });
  }

  if (metrics.length) {
    const sorted = [...metrics].sort((a, b) => b.value - a.value);
    const best = sorted[0];
    const worst = sorted[sorted.length - 1];
    const passCount = metrics.filter(metricPasses).length;
    out.push({
      title: "Metric spread (this case)",
      body: `Highest: ${best.label} ${best.value}${best.unit === "%" ? "%" : ""} (target ${best.target}). Lowest: ${worst.label} ${worst.value}${worst.unit === "%" ? "%" : ""} (target ${worst.target}). ${passCount}/${metrics.length} metrics at/above target.`,
    });
  }

  const domains = data.assessment?.domains ?? [];
  if (domains.length) {
    const flagged = domains.filter((d) => d.flag !== "normal");
    const totalScore = domains.reduce((s, d) => s + d.score, 0);
    const totalMax = domains.reduce((s, d) => s + d.max, 0);
    out.push({
      title: "Assessment domain flags",
      body: `Composite ${totalScore.toFixed(1)}/${totalMax} across ${domains.length} domains. ${flagged.length} flagged (${flagged.map((d) => d.domain).join(", ") || "none"}).`,
    });
  }

  const loop = data.loop_engineering;
  if (loop) {
    out.push({
      title: "Loop engineering",
      body: `${loop.summary} Steps ${loop.step_count}, tool calls ${loop.tool_call_count}, errors ${loop.error_count}, latency ${Math.round(loop.latency_ms)} ms.`,
    });
  }

  out.push({
    title: "Run provenance",
    body: `Task ${data.task_id} · agent ${data.agent_id} · ${data.cached ? "cached" : "fresh"} run. Patient chrome is Gemini synthetic; scores are live evaluator outputs only.`,
  });

  return out;
}
