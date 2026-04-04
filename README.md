# MythAtlas

**World Mythology Map** — explore myths and folklore on an interactive 3D globe. Stories are pinned as emoji markers; zoom in for clustering, city labels, and a detail panel with bilingual text.

<p align="center">
  <img src="docs/showcase.png" alt="MythAtlas — World Mythology Map UI with globe, story pins, and country sidebar" width="920" />
</p>

---

## What it does

| | |
| --- | --- |
| **Globe** | `react-globe.gl` · emoji markers · zoom-based clustering · English place names (Natural Earth) when zoomed in |
| **App** | Theme & era filters · country sidebar · semantic search (with optional OpenAI embeddings) |
| **API** | FastAPI · PostGIS geography · pgvector search · bilingual content stored in PostgreSQL |

---

## Run with Docker

**Requires:** [Docker](https://docs.docker.com/get-docker/) + Compose v2.

```bash
cp .env.example .env
# Optional: set OPENAI_API_KEY and ADMIN_TOKEN in .env
docker compose up --build
```

| Service | URL |
| --- | --- |
| **App** (nginx → UI + `/api` proxy) | [http://localhost:8080](http://localhost:8080) |
| **API** (direct) | [http://localhost:8000/api](http://localhost:8000/api) |
| **Postgres** | `localhost:5432` · user / pass / db: `mythatlas` |

First boot: Alembic migrations + seed data.  
Custom DB image: `docker/db` — PostgreSQL 16 + **PostGIS** + **pgvector** (plain PostGIS images lack `vector`).

**Reset database** (wipes volume): `docker compose down -v`

---

## Layout

```
backend/    FastAPI · Alembic · scripts
frontend/   Vite · React · TypeScript · Tailwind
docker/     DB image
docs/       Showcase asset
```

---

## License

Sample narrative content is for demonstration. See repository for license terms.

---

<p align="center"><sub>世界神话地图 · MythAtlas</sub></p>
