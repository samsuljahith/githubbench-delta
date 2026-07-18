# API Reference

Start the server:

```bash
uv run uvicorn githubbench_delta.api.app:create_app --factory --reload
```

## Core endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/metrics/catalog` | Methodology metric catalog JSON |

## Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard/` | Overview UI |
| GET | `/dashboard/health` | Dashboard health |
| GET | `/dashboard/experiments` | Experiments page |
| GET | `/dashboard/leaderboard` | Leaderboard page |
| GET | `/dashboard/api/*` | REST JSON for charts/tables/export |

Details: [Dashboard](dashboard.md).

## Notes

- The dashboard is **read-only** over experiment artifacts.
- Authentication is stubbed (anonymous viewer).
- No evaluation execution is triggered by API routes.
