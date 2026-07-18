# Mentor session prep (Day 5 — no Cursor)

## Bring

1. GitHub repository URL
2. This folder open locally: `docs/assets/example-report/` (HTML)
3. Dashboard: `uv run uvicorn githubbench_delta.api.app:create_app --factory --host 127.0.0.1 --port 8000`
4. Your filled [`self_study_notes.md`](self_study_notes.md)
5. Experiment ids:
   - Showcase (dry-run multi-agent): `exp_3c790a482f784d21`
   - Live MiniCPM smoke: `exp_ac0f374eeaff4c85`

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

- Published 6×3 showcase is **dry-run** for reproducibility without cloud keys.
- Live Ollama path for MiniCPM was verified on one task.
- Claude/Codex live comparison needs API keys; command is in [`showcase.md`](showcase.md).

## Do not

- Open Cursor during the session
- Overclaim live model rankings from dry-run scores
