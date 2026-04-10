# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MythAtlas is a full-stack mythology storytelling app — an interactive 3D globe for exploring myths and folklore geographically, with bilingual support (English/Chinese) and optional semantic search.

## Running the Project

The project runs entirely via Docker Compose:

```bash
docker compose up --build   # Start all services
docker compose down         # Stop services
docker compose down -v      # Stop and wipe database volume (full reset)
```

Services: Frontend (8080), Backend API (8000), PostgreSQL (5432).

On first boot, the backend automatically runs Alembic migrations → seed script → uvicorn.

**Initial setup:** Copy `.env.example` → `.env`. Optionally set `OPENAI_API_KEY` (enables embeddings + AI generation) and `ADMIN_TOKEN`.

## Frontend Development

```bash
cd frontend
npm run dev      # Dev server at http://localhost:5173 (proxies /api to backend)
npm run build    # TypeScript check + Vite build
npm run lint     # ESLint, zero warnings allowed
npm run preview  # Preview production build
```

## Architecture

### Three-Tier Structure

```
frontend/   React 18 + TypeScript + Vite + Tailwind + react-globe.gl
backend/    FastAPI + SQLAlchemy 2.0 async + Python 3.12
docker/db/  PostgreSQL 16 + PostGIS + pgvector
```

### Data Flow

- Frontend `src/services/api.ts` fetches from `/api/*` (proxied to backend in dev, nginx in Docker)
- Backend routes live in `backend/app/api/routes/` — stories, search, stats, ai, health
- All DB operations are fully async (asyncpg driver, SQLAlchemy async sessions)
- Story model (`backend/app/models/story.py`) stores: bilingual text, PostGIS POINT location, pgvector embedding (1536-dim), tags array, emoji, country

### Key Backend Services

- `services/embeddings.py` — OpenAI text-embedding-3-small calls; gracefully skipped if no API key
- `services/search_service.py` — pgvector cosine similarity search
- `services/story_geo.py` — PostGIS WKT conversions, builds light/full story dicts
- `services/ai_generate.py` — gpt-4o-mini story generation

### Frontend Component Hierarchy

`App.tsx` manages all state (stories, filters, language, search, selection) and renders:
- `GlobeView.tsx` — react-globe.gl with emoji markers, Three.js under the hood
- `CountrySidebar.tsx` — grouped story list by country
- `FilterBar.tsx` — theme/era filter toggles
- `StoryPanel.tsx` — bilingual detail view

### Authentication

`POST /api/stories` requires `Authorization: Bearer <ADMIN_TOKEN>` header (checked in `backend/app/api/deps.py`).

### Seed Data

JSON files in `stories/` are loaded on boot by `backend/scripts/seed.py`. Add new stories there as JSON files matching the schema in `stories/east_asia_stories.json`.

### Bilingual Support

All story content has `_en`/`_zh` field variants (e.g., `title_en`, `title_zh`, `content_en`, `content_zh`). The `Lang` type in `frontend/src/types.ts` is `"en" | "zh"`.
