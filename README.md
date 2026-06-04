# Incident Intelligence Assistant

> Assistant for IT operations teams. Answers questions over structured incident data (tickets, services) and unstructured documentation (runbooks, guides, policies, FAQs) using retrieval-augmented generation (RAG).

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.125+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 18](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Live demo:** [app](https://incident-intel-rho.vercel.app) · [API health](https://incident-intel-api-production.up.railway.app/health) · [API docs](https://incident-intel-api-production.up.railway.app/docs)

---

## Status

**Deployed** — live public full-stack demo on Vercel (frontend) + Railway (backend + Redis) + Neon (Postgres + pgvector). See [Deployment](#deployment).

A portfolio project covering API design, async database access with vector search, a React SPA, and a from-scratch deployment. Points worth a look:

- **Hybrid retrieval, built from scratch** — PostgreSQL full-text search (`ts_rank`) and pgvector cosine similarity, fused with Reciprocal Rank Fusion ([`search_service.py`](src/incident_intel/services/search_service.py)).
- **Streaming chat** over Server-Sent Events through a managed platform proxy.
- **Neon pooler + asyncpg interop** — the connection details documented under [Deployment](#deployment).

Implemented:

- REST APIs (tickets, documents, services, search, chat, conversations) with FastAPI
- Async SQLAlchemy with PostgreSQL + pgvector; Alembic migrations
- Redis caching; structured logging with request correlation
- Tests: 190 backend (pytest) · 32 frontend (Vitest)
- ruff, mypy (`--strict` on `src/`), pre-commit hooks

---

## Project Overview

What it does:

- Vector (semantic) search and PostgreSQL full-text search over documentation, fused with Reciprocal Rank Fusion
- Retrieval across runbooks, guides, policies, and FAQs
- Ticket questions answered with filtered SQL queries (list / count / by service)
- Chat answers generated from retrieved context; the prompt instructs the model to cite numbered sources, and the API returns the source metadata alongside the answer

### API

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness + database/Redis status |
| `/api/v1/tickets` | Ticket CRUD + lifecycle transitions |
| `/api/v1/documents` | Document CRUD (chunked and embedded on write) |
| `/api/v1/services` | Service listing |
| `/api/v1/search` | Keyword / vector / hybrid search |
| `/api/v1/chat` | RAG chat (SSE streaming) |
| `/api/v1/conversations` | Conversation history (list / get / delete) |

Interactive docs at [`/docs`](https://incident-intel-api-production.up.railway.app/docs).

### Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.13 |
| Backend | FastAPI, async SQLAlchemy, Alembic, Pydantic |
| Frontend | Vite, React, TypeScript, Tailwind, shadcn/ui, TanStack Query, React Router, Zod |
| Database | PostgreSQL 18 with pgvector |
| Cache | Redis 7.4 |
| AI / RAG | OpenAI SDK (embeddings + chat); PostgreSQL full-text search (`ts_rank`) + pgvector cosine + Reciprocal Rank Fusion |
| Tooling | uv, ruff, mypy, pytest, structlog; Vitest + MSW (frontend) |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Docker and Docker Compose
- Node.js 20+ (for the frontend)
- uv ([installation guide](https://github.com/astral-sh/uv))
- An OpenAI API key

### Backend

1. **Clone:**
   ```bash
   git clone https://github.com/Andrei618/incident-intel.git
   cd incident-intel
   ```
2. **Environment:**
   ```bash
   cp .env.example .env
   # set OPENAI_API_KEY in .env
   ```
3. **Infrastructure (Postgres + Redis):**
   ```bash
   docker compose up -d
   ```
4. **Dependencies:**
   ```bash
   uv sync
   ```
5. **Migrate the database:**
   ```bash
   uv run alembic upgrade head
   ```
6. **(Optional) seed demo data** — services, tickets, and documents. Calls OpenAI to generate embeddings, and is **not idempotent** (run once on an empty database):
   ```bash
   uv run python scripts/seed_scenarios.py
   ```
7. **Run the API:**
   ```bash
   uv run uvicorn incident_intel.main:app --reload --port 8000
   ```
   Open http://localhost:8000/docs

### Frontend

```bash
cd ui
cp .env.example .env          # set VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                   # http://localhost:5173
```

### Pre-commit hooks (optional)

```bash
uv run pre-commit install
```

---

## Project Structure

```
incident-intel/
├── src/incident_intel/       # FastAPI backend
│   ├── api/                  # Routes (health + /api/v1/*)
│   ├── core/                 # DB engine, Redis, logging
│   ├── llm/                  # OpenAI provider abstraction
│   ├── middleware/           # Request-ID correlation
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response models
│   └── services/             # Search, chat, embeddings, tickets, ...
├── ui/                       # Vite + React + TypeScript SPA
├── migrations/               # Alembic migrations
├── scripts/                  # Seeding / dev utilities
├── tests/                    # pytest (unit + integration)
├── Dockerfile                # Backend image (multi-stage)
├── railway.json              # Railway deploy config
├── docker-compose.yml        # Local Postgres (pgvector) + Redis
└── pyproject.toml
```

---

## Development

### Run

```bash
docker compose up -d
uv run uvicorn incident_intel.main:app --reload --port 8000
```

### Code quality

```bash
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy src/         # type-check (strict; src/ only — test-file types tracked separately)
uv run pytest            # tests (coverage runs by default via pyproject addopts)
```

### Database

```bash
uv run alembic upgrade head                               # apply migrations
uv run alembic revision --autogenerate -m "description"   # create a migration
```

---

## Testing

```bash
uv run pytest                                                # all backend tests (coverage on by default)
uv run pytest tests/unit/services/test_search_service.py    # a single file
```

Frontend:

```bash
cd ui && npm test
```

### Test database

The suite creates and drops **tables** inside a separate database, `incident_intel_test`, but does not create that database itself. Create it once:

```bash
docker exec -it incident-intel-db createdb -U postgres incident_intel_test
```

Override the target with `TEST_DATABASE_URL` (default `postgresql+asyncpg://postgres:postgres@localhost:5432/incident_intel_test`).

---

## Deployment

**Live:**
- **App (frontend):** https://incident-intel-rho.vercel.app
- **API (backend):** https://incident-intel-api-production.up.railway.app — [`/health`](https://incident-intel-api-production.up.railway.app/health) · [`/docs`](https://incident-intel-api-production.up.railway.app/docs)

### Architecture

```
Browser ──▶ Vercel (Vite/React SPA) ──▶ Railway (FastAPI + Redis) ──▶ Neon (PostgreSQL 18 + pgvector)
                                                │
                                                └──▶ OpenAI (embeddings + chat)
```

| Layer | Platform | Notes |
|-------|----------|-------|
| Frontend | **Vercel** | Vite/React SPA served as static assets; SPA rewrite so client-side routes don't 404 on reload |
| Backend + Cache | **Railway** (Amsterdam) | FastAPI built from a multi-stage `Dockerfile` + Redis; a long-lived ASGI process for SSE chat streaming |
| Database | **Neon** (Frankfurt) | PostgreSQL 18 + pgvector; **pooled** connection for the app, **direct** connection for migrations |

### How a deploy happens

Both platforms use **native GitHub integration** — no deploy scripts, no CI deploy jobs. `main` is production:

1. Work lands on feature branches → `develop` (integration); CI (lint / type / test) runs on every PR.
2. A deliberate **`develop → main`** PR is the promotion gate to production.
3. On push to `main`:
   - **Railway** rebuilds the backend from the `Dockerfile`, runs `alembic upgrade head` as a pre-deploy step (migrations apply *before* the new instance serves traffic; a failed migration leaves the previous instance running), then health-checks `/health`.
   - **Vercel** rebuilds and deploys the SPA. Each PR also gets a free preview URL.

### Neon + asyncpg connection details

The bits that make a pooled, serverless Postgres work with an async driver:

- The app uses Neon's **pooled** endpoint via **asyncpg** with `statement_cache_size=0` — Neon's pooler is transaction-mode (PgBouncer), so server-side prepared statements don't survive across requests.
- `sslmode` and `channel_binding` are **stripped from the URL** before asyncpg sees them (libpq-only parameters asyncpg rejects); TLS is still enforced via `connect_args={"ssl": "require"}`.
- **Alembic** uses a separate **direct** (non-pooled) URL via the sync **psycopg** driver — advisory locks and cross-transaction DDL don't survive a transaction pooler.

Configuration is environment-based. Backend variables: [`.env.example`](.env.example). Frontend variables: [`ui/.env.example`](ui/.env.example) (`VITE_API_BASE_URL`). No secrets are committed; production values live in the Railway and Vercel dashboards.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contact

**Andrei** — [GitHub](https://github.com/Andrei618)
