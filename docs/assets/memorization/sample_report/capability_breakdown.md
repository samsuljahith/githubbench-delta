# Capability Breakdown (MDS)

Memorization Discounted Scoring decomposes observed performance as **S_obs = G + L** (generalization + memorization lift).

## Summary

| Field | Value |
|-------|------:|
| Mode | twin |
| Experiments | exp_6afa2ce533ba4e0a |
| Agents | 2 |
| Generated | 2026-07-20T09:36:17.051648+00:00 |

## Per-agent capability

| Agent | S_obs | G | L | S_disc | Mode | N |
|-------|------:|--:|--:|-------:|------|--:|
| codex | 0.682 | 0.414 | 0.269 | 0.414 | twin | 2 |
| minicpm | 0.539 | 0.225 | 0.315 | 0.225 | twin | 2 |

## Posterior lift intervals

| Agent | Mean L | Lower | Upper | Level |
|-------|-------:|------:|------:|------:|
| codex | 0.269 | 0.000 | 0.657 | 0.95 |
| minicpm | 0.315 | 0.000 | 0.721 | 0.95 |

## Notes

- Demo uses live mean scores (MiniCPM 0.539, Codex 0.682) with synthetic twin gaps.

## Assumptions

- Observed score decomposes as S_obs = G + L (generalization + memorization lift).
- When twin scores exist: L = max(0, S_obs - S_twin) and G = S_obs - L.
- When twins are absent: proxy L from (1 - consistency/grounding metrics) × 0.5.
- BayesianDiscountModel uses a Beta(1,1) prior with fractional lift updates.
- MDS is post-processing only; it does not modify benchmark metrics or artifacts.
- This model does not causally identify memorization — twin agreement is correlational.

## Limitations

- Twin absence forces proxy mode with reduced confidence.
- Beta–Binomial lift model is a convenience conjugate, not a causal MDS.
- Prompt paraphrase twins may still share surface cues with parents.
- Does not modify benchmark leaderboards or metric registry entries.

