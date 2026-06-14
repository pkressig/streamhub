# PascalHub v0.1 — Source Intelligence Platform

A self-hosted platform for discovering, classifying, testing, scoring, and monitoring media content sources, with focus on Italian and German content.

## Architecture

- **Backend**: FastAPI + Python 3.12 + SQLAlchemy + Celery
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Containers**: Docker Compose

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

- Frontend: http://localhost:13000
- API: http://localhost:13001
- API Docs: http://localhost:13001/docs

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check |
| GET | /api/stats | Dashboard statistics |
| GET | /api/sources | List all sources |
| POST | /api/sources | Create a source |
| GET | /api/sources/{id} | Get source detail |
| DELETE | /api/sources/{id} | Delete a source |
| POST | /api/sources/{id}/test | Run a test now |

## Source Types

- `torznab` — Torznab indexer endpoints (tests ?t=caps)
- `newznab` — Newznab indexer endpoints (tests ?t=caps)
- `rss` — RSS/Atom feed URLs
- `manifest` — JSON manifest endpoints
- `generic_http` — Any HTTP endpoint

## Scoring

Each source receives scores 0–100:
- **Reliability** — % of successful tests in last 50 checks
- **Speed** — Response time (<500ms=100, >5000ms=0)
- **Trust** — Average of reliability and speed
- **Italian / German** — Placeholder (AI-based in v0.2+)
- **Overall** — Weighted composite

## Background Monitoring

Celery worker automatically retests all sources every 15 minutes.

## Development

```bash
# Backend only
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev
```
