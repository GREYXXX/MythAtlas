# MythAtlas — Codebase Report

> A full-stack mythology storytelling app with an interactive 3D globe, bilingual (EN/ZH) support, geospatial queries, and optional semantic search.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Repository Layout](#2-repository-layout)
3. [Docker & Deployment](#3-docker--deployment)
4. [Backend](#4-backend)
   - [Entry Point & App Setup](#41-entry-point--app-setup)
   - [Configuration](#42-configuration)
   - [Database Layer](#43-database-layer)
   - [Data Model](#44-data-model)
   - [Schemas (Request / Response)](#45-schemas-request--response)
   - [API Routes](#46-api-routes)
   - [Services](#47-services)
   - [Migrations (Alembic)](#48-migrations-alembic)
   - [Seed Script](#49-seed-script)
5. [Frontend](#5-frontend)
   - [Build Config](#51-build-config)
   - [Types](#52-types)
   - [API Client](#53-api-client)
   - [App.tsx — Root Component](#54-apptsx--root-component)
   - [GlobeView](#55-globeview)
   - [FilterBar](#56-filterbar)
   - [CountrySidebar](#57-countrysidebar)
   - [StoryPanel](#58-storypanel)
   - [Utilities & Hooks](#59-utilities--hooks)
6. [Data Files](#6-data-files)
7. [Full Request Flow Examples](#7-full-request-flow-examples)
8. [Technology Reference](#8-technology-reference)

---

## 1. System Architecture

```
┌──────────────────── Browser ────────────────────┐
│  React 18 SPA (Vite + Tailwind + TypeScript)    │
│  react-globe.gl  →  Three.js  →  WebGL          │
└────────────────────┬────────────────────────────┘
                     │  HTTP / REST  (JSON)
           ┌─────────▼──────────┐
           │   Nginx  (8080)    │  ← Docker: serves built SPA,
           │  /api/* → backend  │    proxies /api/* in production
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  FastAPI  (8000)   │  ← Python 3.12, asyncpg, SQLAlchemy 2.0
           │  Pydantic v2       │
           │  GeoAlchemy2       │
           │  pgvector-client   │
           └─────────┬──────────┘
                     │  SQL (async)
           ┌─────────▼──────────┐
           │  PostgreSQL 16     │
           │  + PostGIS         │  ← geospatial: POINT geography, ST_DWithin
           │  + pgvector        │  ← 768-dim vector embeddings, cosine search
           └────────────────────┘
                     ↕  optional external calls
           ┌─────────────────────┐
           │  OpenAI API         │  ← embeddings (text-embedding-3-small)
           │  GPT-4o-mini        │     story generation
           └─────────────────────┘
           ┌─────────────────────┐
           │  Ollama  (local)    │  ← fallback embeddings (nomic-embed-text)
           └─────────────────────┘
```

**Port map (Docker):**

| Service  | Internal | External |
|----------|----------|----------|
| db       | 5432     | 5432     |
| backend  | 8000     | 8000     |
| frontend | 80       | 8080     |

---

## 2. Repository Layout

```
MythAtlas/
├── docker-compose.yml          # Orchestrates all three services
├── .env.example                # Template for secrets / config
├── CLAUDE.md                   # AI assistant guidance
│
├── backend/
│   ├── Dockerfile
│   ├── docker-entrypoint.sh    # migrate → seed → uvicorn
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              # async Alembic config
│   │   └── versions/
│   │       ├── 20260404_0001_initial_schema.py
│   │       └── 20260411_0002_embedding_768.py
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, lifespan
│   │   ├── core/config.py      # Pydantic settings
│   │   ├── db/
│   │   │   ├── base.py         # SQLAlchemy Base
│   │   │   └── session.py      # async engine + session factory
│   │   ├── models/story.py     # Story ORM model
│   │   ├── schemas/
│   │   │   ├── story.py        # StoryLight, StoryFull, StoryCreate
│   │   │   ├── ai.py           # AIGenerateRequest/Response
│   │   │   └── search.py       # SearchResult
│   │   ├── api/
│   │   │   ├── __init__.py     # Aggregates all routers
│   │   │   ├── deps.py         # verify_admin_token dependency
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── stories.py
│   │   │       ├── search.py
│   │   │       ├── stats.py
│   │   │       └── ai.py
│   │   └── services/
│   │       ├── embeddings.py   # OpenAI / Ollama embed_text()
│   │       ├── search_service.py  # vector → FTS → ILIKE fallback
│   │       ├── story_geo.py    # PostGIS ↔ lat/lng conversion
│   │       └── ai_generate.py  # GPT-4o-mini story generation
│   └── scripts/seed.py         # One-time DB seed on startup
│
├── frontend/
│   ├── Dockerfile              # node build → nginx runtime
│   ├── nginx.conf              # SPA fallback + API proxy
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── package.json
│   └── src/
│       ├── main.tsx            # React root
│       ├── App.tsx             # Top-level state + layout
│       ├── index.css           # Tailwind + glass-panel class
│       ├── types.ts            # Shared TypeScript types
│       ├── services/api.ts     # HTTP client (fetch wrappers)
│       ├── components/
│       │   ├── GlobeView.tsx
│       │   ├── FilterBar.tsx
│       │   ├── CountrySidebar.tsx
│       │   └── StoryPanel.tsx
│       ├── hooks/
│       │   └── useElementSize.ts
│       └── utils/
│           ├── countryDisplay.ts
│           └── cityLabels.ts
│
├── stories/
│   └── east_asia_stories.json  # 52 East Asian stories (reference data)
│
└── docker/db/
    └── Dockerfile              # postgres:16 + postgis + pgvector
```

---

## 3. Docker & Deployment

### `docker-compose.yml`

Three services wired together with health checks and dependency ordering.

#### `db` — PostgreSQL 16 + PostGIS + pgvector

- Custom image built from `./docker/db` (adds PostGIS and pgvector extensions to the official Postgres 16 image)
- Credentials: `mythatlas / mythatlas`, DB name `mythatlas`
- Data persisted in a named Docker volume `pgdata`
- Health check: `pg_isready -U mythatlas` every 5 s (backend waits until healthy before starting)

#### `backend` — FastAPI

- Built from `./backend/Dockerfile` (Python 3.12 slim)
- Startup sequence in `docker-entrypoint.sh`:
  1. `alembic upgrade head` — runs any pending DB migrations
  2. `python -m scripts.seed` — inserts sample stories if the table is empty
  3. `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Depends on `db` being healthy
- Env vars passed in from `.env`: `DATABASE_URL`, `ADMIN_TOKEN`, `CORS_ORIGINS`, `OPENAI_API_KEY`

#### `frontend` — Nginx + React SPA

- Two-stage Dockerfile:
  - **Build stage** (`node:20`): `npm ci` → `npm run build` (produces `dist/`)
  - **Runtime stage** (`nginx:1.27-alpine`): serves `dist/`, proxies `/api/` to `backend:8000`
- Nginx config:
  - `try_files $uri /index.html` — client-side routing works on direct URL access
  - `/api/` proxied to `http://backend:8000/api/`
- Port 8080 on host → port 80 inside container

---

## 4. Backend

### 4.1 Entry Point & App Setup

**`app/main.py`**

Creates the FastAPI application instance. Key setup:

- **CORS middleware** — reads `settings.cors_origins` (comma-separated), allows all HTTP methods and headers from those origins. Required so the frontend dev server (port 5173) can call the API (port 8000).
- **Lifespan hook** — on shutdown, calls `engine.dispose()` to cleanly close the async connection pool.
- **Router mount** — includes all route modules at the `/api` prefix.

### 4.2 Configuration

**`app/core/config.py`**

Pydantic v2 `BaseSettings` class. Reads from environment variables (and a `.env` file if present).

| Setting | Default | Purpose |
|---------|---------|---------|
| `app_name` | `"MythAtlas API"` | Display name |
| `debug` | `False` | Debug mode |
| `database_url` | localhost Postgres | asyncpg connection string |
| `cors_origins` | localhost:5173, :8080 | Allowed CORS origins |
| `admin_token` | `"dev-admin-change-me"` | Token for write endpoints |
| `openai_api_key` | _(empty)_ | Enables embeddings + GPT generation |
| `openai_model` | `"gpt-4o-mini"` | Model for story generation |
| `embedding_model` | `"text-embedding-3-small"` | OpenAI embedding model |
| `embedding_dimensions` | `768` | Vector size (matches Ollama too) |
| `ollama_base_url` | `http://localhost:11434` | Local fallback for embeddings |
| `local_embedding_model` | `"nomic-embed-text"` | Ollama model name |

### 4.3 Database Layer

**`app/db/base.py`**

Declares the SQLAlchemy `Base` class that all ORM models inherit from.

**`app/db/session.py`**

- Creates an **async SQLAlchemy engine** using the `asyncpg` driver (`postgresql+asyncpg://...`)
- Connection pool: 10 connections, overflow up to 20
- Provides `get_async_session()` — an `async_generator` used as a FastAPI dependency that yields a session and auto-closes it after each request

### 4.4 Data Model

**`app/models/story.py` — `Story` ORM class**

Maps to the `stories` PostgreSQL table.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `Integer` PK | Auto-increment |
| `title_en` | `String(512)` | English title |
| `title_zh` | `String(512)` | Chinese title |
| `content_en` | `Text` | Full English story body |
| `content_zh` | `Text` | Full Chinese story body |
| `country` | `String(128)` + index | Stored as `"Name 名字"` bilingual format |
| `tags` | `ARRAY(String)` | e.g. `["ancient", "dragon", "flood"]` |
| `emoji` | `String(16)` | Single emoji representing the myth |
| `location` | `Geography(POINT, 4326)` | PostGIS point; GIST index for geo queries |
| `embedding` | `Vector(768)` nullable | pgvector 768-dim float array for semantic search |

### 4.5 Schemas (Request / Response)

**`app/schemas/story.py`**

| Schema | Fields | Used for |
|--------|--------|----------|
| `StoryLight` | id, title_en/zh, lat, lng, country, emoji, tags | List endpoints |
| `StoryFull` | extends StoryLight + content_en/zh | Detail + create response |
| `StoryCreate` | title/content fields, lat, lng, country, tags, emoji | POST body |
| `StoryNearParams` | lat, lng, radius_km | Geo-search query validation |

`StoryCreate` includes a Pydantic validator that normalizes `tags`: strips whitespace, removes empty strings.

**`app/schemas/ai.py`**

- `AIGenerateRequest` — `{country, theme}`
- `AIGenerateResponse` — `{title_en, title_zh, content_en, content_zh, suggested_emoji, suggested_tags}`

**`app/schemas/search.py`**

- `SearchResult` — `{id, title_en, title_zh, country, emoji, score, method}`

### 4.6 API Routes

All routes are mounted at `/api`. Auth dependency (`verify_admin_token`) checks the `X-Admin-Token` request header; returns HTTP 403 on failure.

---

#### `GET /api/health`
Simple liveness check. Returns `{"status": "ok"}`. Used by Docker health check.

---

#### `GET /api/stories`
Returns `StoryLight[]` for all stories. Optional `?tag=` query param does a substring match on the tags array.  
Ordered: country name → ID.

#### `GET /api/stories/{story_id}`
Returns `StoryFull` (with full bilingual content). 404 if not found.

#### `GET /api/stories/near`
Geo-spatial query. Finds stories within `radius_km` (default 500, max 20 000) of a lat/lng point.  
Internally calls PostGIS `ST_DWithin(location, ST_MakePoint(lng, lat)::geography, radius_meters)`.  
Returns `StoryLight[]` sorted by ID.

#### `POST /api/stories` _(admin token required)_
Creates a new story. Steps:
1. Validates `StoryCreate` body
2. Converts `lat`/`lng` to a PostGIS `WKTElement`: `POINT(lng lat)` with SRID 4326
3. Inserts row into DB
4. Calls `embed_text()` to generate a vector embedding (silently skipped on failure)
5. Returns `StoryFull`

---

#### `GET /api/search?q=...&limit=20`
Semantic + full-text search with three-tier fallback:

1. **Vector search** (if any story has an embedding) — cosine distance via pgvector; score normalized to 0.0–1.0
2. **PostgreSQL full-text search** — `tsvector` / `ts_rank` on title+content fields; score normalized by ×2
3. **ILIKE fallback** — case-insensitive substring match on all text fields; fixed score 0.6

Each result includes a `method` field (`"vector"`, `"fulltext"`, `"ilike"`) so callers know which path was taken.

---

#### `GET /api/stats/summary`
Quick aggregate: `{total_stories, countries}`.

#### `GET /api/stats/countries`
Full breakdown: `{total_stories, country_count, countries}` where `countries` is a list of `{country, count, stories: StoryLight[]}` sorted by count descending.

---

#### `POST /api/ai/generate` _(admin token required)_
Generates a new myth using GPT-4o-mini. Body: `{country, theme}`.  
Returns a `AIGenerateResponse` ready to feed into `POST /api/stories`.  
Returns HTTP 503 if `OPENAI_API_KEY` is not configured.

---

### 4.7 Services

#### `services/embeddings.py`

**`embed_text(text: str) → list[float]`**

Converts text into a 768-dimensional float vector. Provider priority:
1. **OpenAI** `text-embedding-3-small` — if `OPENAI_API_KEY` is set; uses the AsyncOpenAI client
2. **Ollama** `nomic-embed-text` — local fallback; HTTP POST to `{ollama_base_url}/api/embeddings`

Input is truncated to 8 000 characters before sending to avoid API token limits.

**`build_embedding_document(...)`** — concatenates all four text fields (title + content, EN + ZH) into a single string for embedding, ensuring the vector captures all semantic content.

---

#### `services/search_service.py`

**`semantic_search(session, q, limit) → list[dict]`**

Orchestrates the three-tier search strategy described in the `/api/search` route. Key details:
- First checks how many stories have non-null embeddings (one cheap `COUNT` query)
- If zero embeddings exist, skips directly to full-text search
- Each tier writes `method` into the result dict for transparency
- Scores are normalized so the frontend can display them uniformly

---

#### `services/story_geo.py`

Bridges PostGIS geography types and plain Python dicts.

| Function | What it does |
|----------|-------------|
| `geography_to_lat_lng(location)` | Converts a PostGIS `Geography` column value → `(lat, lng)` tuple using `geoalchemy2.shape.to_shape()` |
| `story_to_light_dict(story)` | Serializes a `Story` ORM instance into a plain dict with lat/lng (no content fields) |
| `story_to_full_dict(story)` | Extends the light dict with `content_en` and `content_zh` |

---

#### `services/ai_generate.py`

**`generate_myth_json(country, theme) → dict`**

Calls GPT-4o-mini with a system prompt positioning it as a folklore scholar. Returns a structured JSON dict that maps directly onto `AIGenerateResponse`. Settings: `temperature=0.85`, `max_tokens=1800`. Strips markdown code fences from the raw model output before JSON parsing.

---

### 4.8 Migrations (Alembic)

**`alembic/env.py`** — Configured for async SQLAlchemy (uses `run_sync` to run migrations in an async-aware context).

| Migration | What it does |
|-----------|-------------|
| `20260404_0001_initial_schema` | Creates `postgis` + `vector` extensions; creates the `stories` table with all columns; adds indexes on `country` and `location` (GIST) |
| `20260411_0002_embedding_768` | Drops the `embedding` column and recreates it as `Vector(768)` — changing from 1536 to 768 dimensions. pgvector requires a drop+recreate to change vector size |

Migrations run automatically on every container start (`alembic upgrade head` in `docker-entrypoint.sh`).

---

### 4.9 Seed Script

**`backend/scripts/seed.py`**

Runs once on first boot. Checks if the `stories` table is empty; if so, inserts 12 built-in sample stories covering myths from around the world:

> Sun Wukong (Monkey King), Odysseus, Ragnarök, Amaterasu, Anansi, Raven (Pacific Northwest), Rama, Osiris, Cú Chulainn, Quetzalcoatl, Libyan Spirits, Rainbow Serpent

Each story has full EN/ZH bilingual content, coordinates, tags, emoji, and country.

If `OPENAI_API_KEY` is set, the seed script also auto-generates and stores embeddings for all 12 stories so semantic search works immediately.

---

## 5. Frontend

### 5.1 Build Config

**`package.json`** — Core dependencies:

| Package | Version | Role |
|---------|---------|------|
| `react` | 18.3.1 | UI framework |
| `react-dom` | 18.3.1 | DOM renderer |
| `react-globe.gl` | latest | 3D globe component (wraps Three.js) |
| `three` | 0.170.0 | 3D graphics engine (WebGL) |
| `typescript` | 5.6.3 | Type checking |
| `vite` | 5.4.11 | Bundler / dev server |
| `tailwindcss` | 3.4.15 | Utility-first CSS |

**`vite.config.ts`**
- Dev server on port `5173`
- `/api` proxied to `http://127.0.0.1:8000` (configurable via `VITE_API_PROXY_TARGET`)
- Path alias: `@` → `./src`

**`tailwind.config.js`** — Custom design tokens:

| Token | Value / Purpose |
|-------|----------------|
| `font.sans` | System fonts with CJK fallbacks (PingFang SC, Microsoft YaHei) |
| `font.storyZh` | Noto Serif SC — serif font for Chinese story body text |
| `font.storyEn` | Source Serif 4 — serif font for English story body text |
| `colors.glass` | `rgba(15,23,42,0.72)` — semi-transparent dark backdrop |
| `colors.glassBorder` | `rgba(255,255,255,0.08)` — subtle border for glass panels |
| `boxShadow.glow` | Sky-blue glow effect for selected elements |

---

### 5.2 Types

**`src/types.ts`** — shared interfaces used across all components:

```typescript
type Lang = "en" | "zh"

interface StoryLight {
  id: number; title_en: string; title_zh: string;
  lat: number; lng: number; country: string; emoji: string; tags: string[]
}

interface StoryFull extends StoryLight {
  content_en: string; content_zh: string
}

interface CountryGroup {
  country: string; count: number; stories: StoryLight[]
}

interface StatsResponse {
  total_stories: number; country_count: number; countries: CountryGroup[]
}

interface SearchHit {
  id: number; title_en: string; title_zh: string;
  country: string; emoji: string; score: number; method: string
}
```

---

### 5.3 API Client

**`src/services/api.ts`**

Thin fetch wrapper. Base URL: `import.meta.env.VITE_API_BASE || "/api"`. All functions throw on non-2xx responses.

| Function | HTTP call | Returns |
|----------|-----------|---------|
| `fetchStories(tag?)` | `GET /api/stories[?tag=...]` | `StoryLight[]` |
| `fetchStory(id)` | `GET /api/stories/{id}` | `StoryFull` |
| `fetchStoriesNear(lat, lng, radiusKm)` | `GET /api/stories/near` | `StoryLight[]` |
| `fetchStats()` | `GET /api/stats/countries` | `StatsResponse` |
| `fetchSummary()` | `GET /api/stats/summary` | `{total_stories, countries}` |
| `searchStories(q)` | `GET /api/search?q=...&limit=20` | `SearchHit[]` |

---

### 5.4 App.tsx — Root Component

The single source of truth for all application state.

**State managed:**

| State | Type | Purpose |
|-------|------|---------|
| `langUI` | `"en" \| "zh"` | UI display language (default: Chinese) |
| `stories` | `StoryLight[]` | All stories loaded from API |
| `stats` | `StatsResponse` | Country groups + counts |
| `theme` | string | Active theme filter (sun, moon, dragon, …) |
| `era` | string | Active era filter (ancient, classical, …) |
| `showLines` | boolean | Globe graticule on/off |
| `showCityNames` | boolean | City labels on/off |
| `selectedId` | `number \| null` | Currently selected story ID |
| `detail` | `StoryFull \| null` | Loaded story details for panel |
| `detailLoading/Error` | boolean/string | Story panel fetch state |
| `hoverStory` | `StoryLight \| null` | Globe hover state |
| `selectedCountry` | string | Sidebar country filter |
| `headerSearch` | string | Header search input value |

**Key behaviors:**
- On mount: fetches all stories + stats in parallel
- `filtered` memo: computes visible stories from `theme`/`era` filter + `selectedCountry`
- `openStory(id)`: fetches full story detail, sets `detail`, scrolls StoryPanel into view
- `runHeaderSearch()`: calls `searchStories()`, opens the top result automatically
- Language toggle: switches both UI labels and story text simultaneously

**Layout rendered:**
```
┌──────────────────────────────────────────────┐
│  Header (logo, language toggle, search bar)  │
├──────────────────┬───────────────────────────┤
│                  │                           │
│   GlobeView      │   CountrySidebar          │
│   (3D globe)     │   (scrollable list)       │
│                  │                           │
│   FilterBar      │                           │
│   (bottom bar)   │                           │
├──────────────────┴───────────────────────────┤
│   StoryPanel (modal overlay, slides up)      │
└──────────────────────────────────────────────┘
```

---

### 5.5 GlobeView

**`src/components/GlobeView.tsx`**

The visual centerpiece. Uses `react-globe.gl` (which wraps Three.js / WebGL) to render an interactive 3D Earth.

**Props:**

| Prop | Type | Purpose |
|------|------|---------|
| `stories` | `StoryLight[]` | Stories to render as markers |
| `selectedId` | `number \| null` | Highlights the selected marker |
| `onSelect(id)` | callback | Fired on marker click |
| `onHover(story)` | callback | Fired on marker hover |
| `showLines` | boolean | Toggle longitude/latitude lines |
| `showCityNames` | boolean | Toggle city label layer |
| `highlightCountry` | string | Highlights a country name in the header |
| `lang` | `Lang` | Language for labels |

**Level of Detail (LOD) clustering:**

To avoid rendering hundreds of overlapping markers when zoomed out, stories are grouped into grid cells based on camera altitude:

| Altitude range | Grid cell size | Behavior |
|----------------|---------------|---------|
| `< 0.92` | — | Show every individual story |
| `0.92 – 1.15` | 4.5° | Cluster nearby stories |
| `1.15 – 2.0` | 9.0° | Larger clusters |
| `> 2.8` | 18.0° | Very coarse clusters |

Clicking a cluster zooms the camera in; clicking a single story fires `onSelect`.

**Emoji markers:**
- Each marker is a custom HTML element containing the story's emoji
- Font-size scales with `__size` (a field set by the clustering logic)
- Selected marker gets a `glow` CSS shadow + scale animation
- Cluster badge shows story count when multiple stories are grouped

**Zoom controls:**
- `+` / `−` buttons on the right side of the globe
- Zoom in: multiply altitude by 0.72
- Zoom out: multiply altitude by 1.38
- Clamped to `ALT_MIN = 0.42` and `ALT_MAX = 6.2`

**City labels:**
- Loads `ne_110m_populated_places_simple.geojson` (Natural Earth data) at runtime
- `filterPlacesForAltitude()` controls which cities are visible at each zoom level (fewer at far zoom; filters by population threshold)
- Label text: English name, with CJK characters stripped as fallback

**Globe appearance:**
- Background: night-mode Earth texture + starfield (served via CDN)
- Atmosphere: blue glow shader
- Anisotropic texture filtering for sharper look at oblique angles

---

### 5.6 FilterBar

**`src/components/FilterBar.tsx`**

A horizontal control strip rendered at the bottom of the globe.

**Theme buttons** (filter by myth topic tag):
All | Sun | Flood | Fire | Dragon | Love | Moon | Princess

**Era buttons** (filter by historical period tag):
All Eras | Ancient | Classical | Medieval | Modern

**Toggle switches:**
- **Lines** — show/hide graticule (lat/lng grid lines on globe)
- **Cities** — show/hide city name labels

Styling: glass-panel design (dark semi-transparent background with blur), horizontally scrollable on narrow screens.

---

### 5.7 CountrySidebar

**`src/components/CountrySidebar.tsx`**

A scrollable panel on the right side listing stories grouped by country.

**Features:**
- **Search box** — filters the country list by name as you type
- **Country cards** — show country name (formatted for display language), story count, and a proportional bar (fraction of the country with the most stories)
- **Click to select** — clicking a country filters the globe and story list to that country; clicking again deselects
- **Expanded view** — the selected country card shows an inline list of its stories, each clickable to open the detail panel
- **Language-aware** — uses `formatCountryForDisplay()` to strip CJK characters in English mode

---

### 5.8 StoryPanel

**`src/components/StoryPanel.tsx`**

A modal panel that slides up from the bottom when a story is selected.

**Layout:**
- **Header**: Large emoji, bilingual title, country badge, tag pills
- **Body**: Story text (`StoryProse` sub-component)
- **Footer**: EN/ZH language toggle, AI-generated content disclaimer

**`StoryProse` component:**
- Splits story content by blank lines into paragraphs
- Linkifies any URLs found in text
- Chinese (`content_zh`): `font-storyZh`, `leading-[1.65]`
- English (`content_en`): `font-storyEn`, `leading-[1.72]`

**Interaction:**
- Clicking the overlay (outside the panel) closes it
- `onLang` prop switches between EN/ZH text instantly (content already loaded)

---

### 5.9 Utilities & Hooks

**`src/utils/countryDisplay.ts`**

`formatCountryForDisplay(country: string)` — Countries are stored bilingually as `"Japan 日本"`. This function strips the CJK portion when the UI is in English mode, returning just `"Japan"`.

**`src/utils/cityLabels.ts`**

- `NEPlaceFeature` — TypeScript type for a Natural Earth GeoJSON feature
- `englishPlaceName(properties)` — extracts the ASCII place name, stripping CJK as a fallback
- `filterPlacesForAltitude(features, altitude)` — controls city label density:

| Altitude | Cities shown |
|----------|-------------|
| ≥ 1.48 | None |
| < 0.92 | Population ≥ 120 000 |
| < 1.15 | Population ≥ 500 000 |
| else | Population ≥ 1.4 M or world-city flag |

**`src/hooks/useElementSize.ts`**

Custom React hook using `ResizeObserver` to track the pixel dimensions of a DOM element. Returns `{ref, size: {width, height}}`. Used by `GlobeView` to make the Three.js canvas fill its container correctly on resize.

---

## 6. Data Files

**`stories/east_asia_stories.json`**

A reference dataset of 52 East Asian myths and legends (region: East Asia). Each entry has:
- Bilingual metadata: `title_en`, `title_zh`, `summary_en`, `summary_zh` (summaries, not full content)
- Location: `lat`, `lng`
- Taxonomy: `country`, `emoji`, `type` (`myth` / `legend` / `epic`), `tags[]`
- Wikipedia links: `wiki_en`, `wiki_zh`

> Note: This file is not directly loaded by the seed script. The seed script has its own hardcoded stories. This JSON file appears to be a reference / data-prep artifact using `summary_en/zh` fields instead of the `content_en/zh` fields the DB schema requires.

---

## 7. Full Request Flow Examples

### Load the homepage

```
1. Browser → GET /  → Nginx serves index.html + JS bundle
2. React mounts App.tsx
3. App.useEffect → parallel:
     fetchStories()      GET /api/stories       → StoryLight[]
     fetchStats()        GET /api/stats/countries → StatsResponse
4. State update → GlobeView renders emoji markers
                → CountrySidebar renders country list
```

### Click a story marker on the globe

```
1. GlobeView onClick → onSelect(id)
2. App: setSelectedId(id) → openStory(id)
3. fetchStory(id) → GET /api/stories/{id} → StoryFull
4. App: setDetail(story)
5. StoryPanel slides up with full bilingual content
```

### Semantic search

```
1. User types query in header → presses Enter
2. App: runHeaderSearch()
3. searchStories(q) → GET /api/search?q=...&limit=20
4. Backend:
     embed_text(q)   → OpenAI / Ollama vector
     pgvector cosine_distance on stories.embedding
     (fallback: ts_rank, then ILIKE)
5. Returns SearchHit[] with score + method
6. App opens first result via openStory()
```

### Filter by theme + era

```
1. User clicks "Dragon" theme filter → setTheme("dragon")
2. App recomputes filtered memo:
     stories.filter(s => s.tags.includes("dragon"))
3. GlobeView re-renders with filtered markers only
4. CountrySidebar updates to show only countries with dragon stories
```

### Create a new story (admin)

```
1. POST /api/stories
   Headers: X-Admin-Token: <token>
   Body: StoryCreate JSON
2. Backend:
     verify_admin_token()
     Validate StoryCreate (Pydantic)
     Build WKTElement: POINT(lng lat)
     INSERT INTO stories ...
     embed_text(full_text) → store embedding
     Return StoryFull
```

---

## 8. Technology Reference

### Backend Stack

| Technology | What it does in this project |
|-----------|------------------------------|
| **FastAPI** | Web framework; async request handling, Pydantic validation, OpenAPI docs at `/docs` |
| **SQLAlchemy 2.0** | ORM; async sessions, declarative models, query builder |
| **asyncpg** | High-performance async PostgreSQL driver |
| **Alembic** | Schema migrations; run automatically on startup |
| **Pydantic v2** | Request/response validation and settings management |
| **GeoAlchemy2** | PostGIS integration — `Geography(POINT)` column type, `WKTElement`, `to_shape()` |
| **pgvector** | PostgreSQL extension for storing + querying 768-dim float vectors (cosine distance) |
| **OpenAI SDK** | `text-embedding-3-small` for embeddings; `gpt-4o-mini` for myth generation |
| **httpx** | Async HTTP client used to call the Ollama local embedding server |
| **Uvicorn** | ASGI server that runs the FastAPI app |

### Frontend Stack

| Technology | What it does in this project |
|-----------|------------------------------|
| **React 18** | Component-based UI; hooks for state and side effects |
| **TypeScript** | Type safety across all components, API responses, and shared interfaces |
| **Vite** | Dev server with HMR, production bundler, `/api` proxy |
| **react-globe.gl** | High-level 3D globe component; handles camera, renderer, and HTML markers |
| **Three.js** | Underlying 3D engine used by react-globe.gl (WebGL rendering) |
| **Tailwind CSS** | Utility-first styling; custom fonts, glass-panel theme, responsive layout |
| **PostCSS + Autoprefixer** | CSS processing pipeline for Tailwind |

### Database Extensions

| Extension | Purpose |
|-----------|---------|
| **PostGIS** | Stores story locations as `Geography(POINT, 4326)`; enables `ST_DWithin` for radius searches |
| **pgvector** | Stores 768-dim float embeddings; enables cosine-distance similarity search with `<=>` operator |

### Infrastructure

| Tool | Role |
|------|------|
| **Docker** | Containerizes all three services |
| **Docker Compose** | Orchestrates startup order, networking, volume mounts |
| **Nginx** | Serves the React SPA; proxies `/api/*` to FastAPI |
| **Google Fonts** | Noto Serif SC (Chinese serif), Source Serif 4 (English serif) — loaded via `<link>` in `index.html` |
| **Natural Earth** | `ne_110m_populated_places_simple.geojson` — city label data loaded at runtime by the globe |
