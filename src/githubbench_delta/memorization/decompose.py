"""Decompose observed score into generalization + memorization lift."""

from __future__ import annotations

from githubbench_delta.memorization.helpers import clamp01
from githubbench_delta.memorization.models import (
    CapabilityBreakdown,
    MemorizationLift,
    PosteriorInterval,
)


class CapabilityDecomposer:
    """Build per-agent capability breakdowns from lift aggregates + posteriors."""

    def decompose(
        self,
        lifts: list[MemorizationLift],
        posteriors: list[PosteriorInterval] | None = None,
    ) -> list[CapabilityBreakdown]:
        post_by_agent = {p.agent_id: p for p in (posteriors or [])}
        out: list[CapabilityBreakdown] = []
        for lift in lifts:
            post = post_by_agent.get(lift.agent_id)
            hat_l = post.mean if post is not None else lift.mean_lift
            observed = lift.mean_obs
            generalization = clamp01(observed - hat_l)
            discounted = (
                post.discounted_mean
                if post is not None and post.discounted_mean is not None
                else clamp01(observed - hat_l)
            )
            residual = observed - (generalization + hat_l)
            notes: list[str] = []
            if lift.mode == "proxy":
                notes.append(
                    "Proxy mode: lift estimated without twin evaluations; "
                    "posterior confidence is reduced."
                )
            out.append(
                CapabilityBreakdown(
                    agent_id=lift.agent_id,
                    observed_score=observed,
                    generalization=generalization,
                    memorization_lift=hat_l,
                    discounted_score=discounted if discounted is not None else generalization,
                    residual=residual,
                    mode=lift.mode,
                    n_tasks=lift.n_pairs,
                    notes=notes,
                )
            )
        return out
