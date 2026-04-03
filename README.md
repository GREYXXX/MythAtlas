# MythAtlas — 世界神话地图 / World Mythology Map

Production-oriented monorepo: **React + globe.gl** frontend, **FastAPI** backend, **PostgreSQL + PostGIS + pgvector**, and **Docker Compose** for one-command local deployment.

## Features

- **Interactive 3D globe** with emoji markers, bilingual labels, graticule (“Lines”) toggle, and story detail panel.
- **REST API**: list/filter stories, fetch by id, **PostGIS** `ST_DWithin` for `/api/stories/near`, **semantic search** via embeddings + pgvector (with **FTS + ILIKE fallback** when embeddings are missing).
- **Optional AI**: `POST /api/ai/generate` (requires `OPENAI_API_KEY` and `X-Admin-Token`).
- **No runtime machine translation** — English and Chinese are stored in the database.

## Quick start (Docker)

Requirements: **Docker** + **Docker Compose**.

```bash
cp .env.example .env
# Optionally set OPENAI_API_KEY and ADMIN_TOKEN in .env
# If you previously ran with plain postgis and migrations failed, reset the DB volume once:
# docker compose down -v
docker compose up --build
```

The **`db`** service is built from `docker/db` (**PostgreSQL 16 + pgvector + PostGIS**). Plain `postgis/postgis` images do not include `vector`, so this project uses a small image based on `pgvector/pgvector` with PostGIS packages installed.

- **Web UI**: http://localhost:8080 (nginx → static app + `/api` → backend)
- **API**: http://localhost:8000/api (direct backend, CORS-enabled for dev origins)
- **PostgreSQL**: `localhost:5432` (user/password/db: `mythatlas` / `mythatlas` / `mythatlas`)

On first boot the backend runs **Alembic migrations** and **seeds** 12 sample stories.

## Local development (without Docker)

### Database

Run PostgreSQL **with PostGIS** (e.g. `postgis/postgis:16-3.4`) and create DB `mythatlas`. Ensure extensions `postgis` and `vector` are available (the migration enables them).

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env
# Set DATABASE_URL in .env to point at your Postgres
export $(grep -v '^#' ../.env | xargs)  # or set variables manually
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Admin-only routes expect header: `X-Admin-Token: <ADMIN_TOKEN>` (default in `.env.example`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev server proxies `/api` to `http://127.0.0.1:8000` (override with `VITE_API_PROXY_TARGET` in `vite.config.ts` if needed).

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/stories` | List stories (`?tag=` substring on tags) |
| GET | `/api/stories/{id}` | Full story |
| GET | `/api/stories/near` | `lat`, `lng`, `radius_km` — geography query |
| GET | `/api/search` | `q`, `limit` — semantic search (vector if embeddings exist) |
| GET | `/api/stats/countries` | Per-country aggregates |
| GET | `/api/stats/summary` | Totals |
| POST | `/api/stories` | Create story (requires `X-Admin-Token`) |
| POST | `/api/ai/generate` | JSON `{ country, theme }` — AI draft (requires admin token + OpenAI) |

## Project layout

```
/backend     FastAPI app, Alembic, seed script
/frontend    Vite + React + TypeScript + Tailwind + react-globe.gl
docker-compose.yml
.env.example
```

## License

See repository defaults; sample myth text is for demonstration only.

---

## 中文摘要

- **一键运行**：安装 Docker 后执行 `docker compose up --build`，浏览器访问 **http://localhost:8080**。
- **技术栈**：前端 React + globe.gl；后端 FastAPI；数据库 PostgreSQL + PostGIS + pgvector；中英双语内容存数据库，不做在线翻译。
- **管理接口**：创建故事与 AI 生成需携带请求头 `X-Admin-Token`（由环境变量 `ADMIN_TOKEN` 配置）。
