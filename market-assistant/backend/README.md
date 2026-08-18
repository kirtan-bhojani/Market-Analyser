---
title: Market Assistant Backend
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8080
pinned: false
---

# Market Assistant — Backend (Hugging Face Space)

FastAPI + arq analysis-only trading platform backend, deployed as a **Docker
Space**. HF runs a single container, so the worker and web server run together
via `PROCESS_TYPE=all` (see `docker-entrypoint.sh`).

## Required Space configuration (Settings → Variables and secrets)

Set these as **secrets** (never commit them):

| Key | Notes |
|---|---|
| `ENV` | `prod` |
| `PROCESS_TYPE` | `all` — runs web + worker in one container |
| `DATABASE_URL` | Neon/Supabase Postgres (async: `postgresql+asyncpg://…`, pgvector enabled) |
| `REDIS_URL` | Upstash Redis (`rediss://…`) |
| `JWT_SECRET` | Supabase JWT secret (or set `SUPABASE_JWKS_URL`) |
| `LLM_PROVIDER` + its key | e.g. `groq` + `GROQ_API_KEY` |
| `TELEGRAM_BOT_TOKEN` | alert delivery |
| `CORS_ALLOWED_ORIGINS` | the Vercel frontend origin |

The fail-fast config guard (`app/core/config.py`) crashes startup with a
readable error if any of these are missing in prod.

## Caveats on the free tier

- **No persistent disk:** ML model artifacts under `/data/models` are ephemeral
  and re-created on restart. Bake them into the image or fetch from a model repo
  for durability.
- **Sleeps after ~48h idle:** the worker's cron/ingestion pauses while asleep and
  resumes on the next request that wakes the Space.
