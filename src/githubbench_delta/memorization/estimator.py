"""Estimate memorization lift from parent/twin scores or proxies."""

from __future__ import annotations

from collections import defaultdict

from githubbench_delta.dashboard.schemas import EvaluationRow
from githubbench_delta.memorization.helpers import clamp01, mean_or_none
from githubbench_delta.memorization.models import (
    AnalysisMode,
    MemorizationLift,
    TwinPair,
    TwinTaskSpec,
)


class MemorizationEstimator:
    """Join parent/twin evaluation rows or fall back to proxy lift estimates."""

    def estimate(
        self,
        rows: list[EvaluationRow],
        *,
        twin_specs: list[TwinTaskSpec] | None = None,
    ) -> tuple[list[MemorizationLift], AnalysisMode, list[str]]:
        notes: list[str] = []
        twin_map = {s.id: s.parent_task_id for s in (twin_specs or []) if s.id}
        parent_of = dict(twin_map)

        # Index mean overall score by (agent, task)
        scores: dict[tuple[str, str], list[float]] = defaultdict(list)
        metric_proxy: dict[tuple[str, str], list[float]] = defaultdict(list)
        for row in rows:
            if row.overall_score is None:
                continue
            key = (row.agent_id, row.task_id)
            scores[key].append(float(row.overall_score))
            # Proxy features when twins absent
            reps = row.metric_scores.get("reproducibility")
            xt = row.metric_scores.get("cross_trial_consistency")
            ground = row.metric_scores.get("grounding_ratio")
            parts = [float(x) for x in (reps, xt, ground) if x is not None]
            if parts:
                # Low consistency / grounding → higher suspected memorization proxy
                consistency = sum(parts) / len(parts)
                metric_proxy[key].append(clamp01(1.0 - consistency))

        twin_task_ids = set(parent_of.keys())
        parent_ids_with_twins = set(parent_of.values())

        # Detect whether any twin task ids appear in evaluation rows
        evaluated_tasks = {t for _, t in scores}
        twin_hits = evaluated_tasks & twin_task_ids
        # Also treat tasks whose id ends with __twin_para_ as twins even without catalog
        for tid in evaluated_tasks:
            if "__twin_" in tid and tid not in parent_of:
                # Infer parent by stripping suffix
                parent_guess = tid.split("__twin_")[0]
                parent_of[tid] = parent_guess
                twin_hits.add(tid)
                parent_ids_with_twins.add(parent_guess)

        mode: AnalysisMode = "twin" if twin_hits else "proxy"
        if mode == "proxy":
            notes.append(
                "No twin evaluation rows found; using proxy memorization lift "
                "(1 - mean(reproducibility, cross_trial_consistency, grounding_ratio))."
            )
            notes.append("Proxy mode applies a 0.5 confidence scale on lifts for Bayesian updates.")

        agents = sorted({a for a, _ in scores})
        lifts: list[MemorizationLift] = []

        for agent in agents:
            pairs: list[TwinPair] = []
            if mode == "twin":
                # For each parent that has a twin evaluated
                parents = sorted(
                    {
                        parent_of[t]
                        for t in twin_hits
                        if (agent, parent_of[t]) in scores and (agent, t) in scores
                    }
                )
                for parent_id in parents:
                    twin_ids = [
                        t for t, p in parent_of.items() if p == parent_id and t in twin_hits
                    ]
                    s_obs = mean_or_none(scores[(agent, parent_id)])
                    if s_obs is None:
                        continue
                    for tid in twin_ids:
                        s_twin = mean_or_none(scores[(agent, tid)])
                        if s_twin is None:
                            continue
                        lift = clamp01(max(0.0, s_obs - s_twin))
                        gen = clamp01(s_obs - lift)
                        pairs.append(
                            TwinPair(
                                parent_task_id=parent_id,
                                twin_task_id=tid,
                                agent_id=agent,
                                s_obs=s_obs,
                                s_twin=s_twin,
                                lift=lift,
                                generalization=gen,
                                mode="twin",
                            )
                        )
                if not pairs:
                    # Fall back to proxy for this agent
                    notes.append(
                        f"Agent {agent}: twin catalog present but no joined pairs; "
                        "using proxy lifts."
                    )
                    pairs = self._proxy_pairs(agent, scores, metric_proxy)
            else:
                pairs = self._proxy_pairs(agent, scores, metric_proxy)

            if not pairs:
                continue
            mean_lift = mean_or_none([p.lift for p in pairs]) or 0.0
            mean_obs = mean_or_none([p.s_obs for p in pairs]) or 0.0
            mean_gen = mean_or_none([p.generalization for p in pairs]) or 0.0
            lifts.append(
                MemorizationLift(
                    agent_id=agent,
                    mean_lift=mean_lift,
                    mean_obs=mean_obs,
                    mean_generalization=mean_gen,
                    n_pairs=len(pairs),
                    mode=pairs[0].mode,
                    pairs=pairs,
                )
            )

        if not lifts:
            notes.append("No evaluation rows with overall_score available.")
        return lifts, mode, notes

    @staticmethod
    def _proxy_pairs(
        agent: str,
        scores: dict[tuple[str, str], list[float]],
        metric_proxy: dict[tuple[str, str], list[float]],
    ) -> list[TwinPair]:
        pairs: list[TwinPair] = []
        task_ids = sorted({t for a, t in scores if a == agent and "__twin_" not in t})
        for tid in task_ids:
            s_obs = mean_or_none(scores[(agent, tid)])
            if s_obs is None:
                continue
            proxy_vals = metric_proxy.get((agent, tid), [])
            raw_lift = mean_or_none(proxy_vals)
            # Neutral prior when metrics missing; else scale proxy by 0.5
            lift = 0.25 if raw_lift is None else clamp01(0.5 * raw_lift)
            gen = clamp01(s_obs - lift)
            pairs.append(
                TwinPair(
                    parent_task_id=tid,
                    twin_task_id="",
                    agent_id=agent,
                    s_obs=s_obs,
                    s_twin=None,
                    lift=lift,
                    generalization=gen,
                    mode="proxy",
                    metadata={"proxy": True},
                )
            )
        return pairs
