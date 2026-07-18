# Mentor session prep (Day 5 — no Cursor)

## Bring

1. GitHub repository URL
2. This folder open locally: `docs/assets/example-report/` (HTML)
3. Dashboard: `uv run uvicorn githubbench_delta.api.app:create_app --factory --host 127.0.0.1 --port 8000`
4. Your filled [`self_study_notes.md`](self_study_notes.md)
5. Experiment ids:
   - **Live MiniCPM vs Codex showcase:** `exp_6afa2ce533ba4e0a` ([benchmark.md](benchmark.md))
   - Showcase (dry-run multi-agent UX): `exp_3c790a482f784d21`
   - Live MiniCPM smoke (single task): `exp_ac0f374eeaff4c85`

## Agenda

1. Complete project explanation (problem → agents → metrics → pipeline → UI/reports)
2. Every folder under `src/githubbench_delta/`
3. Every class you marked as “key” in notes
4. Every metric (18) and the 6 groups
5. Pipeline: create → run units → peer pass → artifacts
6. Architecture decisions + trade-offs
7. Founder Q&A
8. Live demo (dashboard + HTML report)

## Honest framing (say this)

- Authoritative live leaderboard numbers are from **`exp_6afa2ce533ba4e0a`** (MiniCPM vs Codex); see [benchmark.md](benchmark.md).
- The published 6×3 showcase (`exp_3c790a482f784d21`) is **dry-run** for pipeline/UX demos without cloud keys — not a live ranking.
- Codex in the live showcase hit rate-limit / quota errors on 3/6 units.
- Claude was not included in `exp_6afa2ce533ba4e0a`.

## Do not

- Open Cursor during the session
- Overclaim live model rankings from dry-run scores
