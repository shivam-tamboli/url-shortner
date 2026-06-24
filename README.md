# URL Shortener

A full-stack URL shortener built with FastAPI, PostgreSQL, Redis, and React. Paste a long URL, get a short link. Click the short link, get redirected instantly.

**Live Demo → [url-shortner-eta-khaki.vercel.app](https://url-shortner-eta-khaki.vercel.app)**
**API Docs → [url-shortner-amlv.onrender.com/docs](https://url-shortner-amlv.onrender.com/docs)**

---

## What it does

- Turns any long URL into a short 6-character code
- Lets users choose their own custom short code instead of a random one
- Optionally sets an expiry time — the link stops working after that
- Redirects users to the original URL when they visit the short link
- Tracks how many times each link was clicked
- Uses Redis to serve popular links without hitting the database every time

---

## Diagram 1 — System Architecture

How all four pieces of the system sit together.

```
                    ┌──────────────────────┐
                    │    React Frontend     │
                    │    localhost:5173     │
                    └──────────┬───────────┘
                               │
                        HTTP requests
                               │
                    ┌──────────▼───────────┐
                    │    FastAPI Backend    │
                    │    localhost:8000     │
                    └────────┬─────┬───────┘
                             │     │
               ┌─────────────▼─┐ ┌─▼─────────────┐
               │     Redis     │ │   PostgreSQL   │
               │   port 6379   │ │   port 5432    │
               │   (cache)     │ │  (database)    │
               └───────────────┘ └───────────────┘
```

> Both Redis and PostgreSQL run as Docker containers locally.
> FastAPI runs directly on your machine and talks to both containers through exposed ports.

---

## Diagram 2 — Redirect Flow (Cache-Aside Pattern)

What happens every time someone clicks a short link.

```
  User visits  →  yoursite.com/abc123
                          │
                          ▼
               ┌─────────────────────┐
               │   Check Redis first  │
               └──────────┬──────────┘
                          │
              ┌───────────┴────────────┐
              │                        │
         CACHE HIT                CACHE MISS
              │                        │
     ┌────────▼────────┐      ┌────────▼────────┐
     │  Check expiry   │      │ Query PostgreSQL │
     │  in cache value │      └────────┬────────┘
     └──┬──────────┬───┘               │
       YES         NO            ┌─────┴──────┐
        │           │          found       not found
       410      redirect          │               │
      Gone                ┌──────┴──────┐       404
                          │  Expired?   │      error
                          └──┬───────┬──┘
                            YES      NO
                             │        │
                           410   ┌────▼──────────────┐
                          Gone   │  Store in Redis    │
                                 │  (remaining TTL)   │
                                 └────────┬───────────┘
                                          │
                                          ▼
                               ┌───────────────────────┐
                               │  Redirect user to     │
                               │  original long URL    │
                               └───────────┬───────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │  Increment click      │  ← background task
                               │  count in PostgreSQL  │
                               └───────────────────────┘
```

> Expiry time is stored inside the cached value as a JSON field — no database query on cache hit.
> On a cache miss, the remaining TTL (not the original duration) is used so Redis and PostgreSQL stay in sync.
> Click counting runs as a background task — it does not slow down the redirect.

---

## Diagram 3 — URL Shortening Flow

What happens when a user submits a long URL.

```
  User submits  →  https://very-long-url.com/some/path
                              │
                              ▼
                  ┌───────────────────────┐
                  │  Did user provide a    │
                  │  custom_code?          │
                  └───────────┬───────────┘
                              │
                 ┌────────────┴─────────────┐
                YES                          NO
                 │                           │
      ┌──────────▼──────────┐    ┌───────────▼───────────┐
      │  Is that code taken  │    │  Does this long URL    │
      │  in the database?   │    │  already exist in DB?  │
      └──────┬──────────┬───┘    └───────────┬───────────┘
            YES         NO                   │
             │           │        ┌──────────┴──────────┐
           409         use it    YES                     NO
         Conflict               │              ┌────────▼────────────┐
                                │              │  Generate random code│
                                │              │  e.g. "kX9mQz"      │
                                │              │  (62 chars, 6 picks) │
                                │              └────────┬────────────┘
                                │                       │
                                │         ┌─────────────▼───────────┐
                                │         │  Code already taken?     │
                                │         └─────┬──────────┬─────────┘
                                │              YES         NO
                                │               │           │
                                │               └─ retry ◄──┘
                                │
                                └──────────────────┐
                                                   ▼
                                    ┌──────────────────────────┐
                                    │  Save to PostgreSQL       │
                                    │  Set expires_at if given  │
                                    │  Cache in Redis (TTL set) │
                                    └──────────────┬───────────┘
                                                   │
                                                   ▼
                                       Return short URL + expires_at
```

> Same long URL always returns the same short code — no duplicates created.
> 62 characters × 6 picks = 56 billion possible codes.
> Custom codes skip the duplicate check and go straight to the taken/available check.

---

## Diagram 4 — Database Schema

```
  Table: urls
  ┌─────────────┬──────────────┬──────────────────────────────────────┐
  │   Column    │     Type     │              Notes                   │
  ├─────────────┼──────────────┼──────────────────────────────────────┤
  │ id          │ integer      │ primary key, auto increments 1, 2, 3 │
  │ short_code  │ varchar(10)  │ unique + indexed — fast lookups      │
  │ long_url    │ text         │ no length limit                      │
  │ clicks      │ integer      │ starts at 0, increments on redirect  │
  │ created_at  │ timestamp    │ auto set to UTC time on insert       │
  │ expires_at  │ timestamp    │ nullable — NULL means never expires  │
  └─────────────┴──────────────┴──────────────────────────────────────┘

  Indexes
  └── ix_urls_short_code  →  short_code column (unique)
                              every redirect searches by this column
```

---

## Diagram 5 — Link Expiry Flow

What happens when a link has an expiry set.

```
  User creates link with expiry_hours = 2
                   │
                   ▼
  expires_at = now + 2 hours  →  stored in PostgreSQL
  Redis TTL  = 2 × 3600 secs  →  cache evicts it automatically
                   │
                   ▼
         ┌─────────────────┐
         │  2 hours later  │
         └────────┬────────┘
                  │
        Someone clicks the short link
                  │
                  ▼
         Check Redis → already evicted by TTL → cache miss
                  │
                  ▼
         Query PostgreSQL → row found
                  │
                  ▼
         Is expires_at in the past?
                  │
            YES ──┴── NO
             │           │
           410          redirect
          Gone         as normal
```

> Redis TTL and PostgreSQL expires_at are always set to the same duration.
> This means cache and database stay in sync without any extra cleanup job.

---

## Tech Stack

- **Backend** — FastAPI (Python)
- **Database** — PostgreSQL with SQLAlchemy ORM
- **Cache** — Redis
- **Migrations** — Alembic
- **Frontend** — React + Vite
- **Local infra** — Docker + docker-compose
- **Deployed on** — Render (backend + database + cache) and Vercel (frontend)

---

## Project Structure

```
url-shortener/
├── docker-compose.yml          — spins up PostgreSQL and Redis locally
├── backend/
│   ├── main.py                 — FastAPI app entry point, CORS middleware, router registration
│   ├── requirements.txt        — production dependencies with pinned versions
│   ├── requirements-dev.txt    — local-only dev dependencies (pytest, pytest-asyncio)
│   ├── pytest.ini              — pytest configuration (asyncio mode)
│   ├── .python-version         — pins Python 3.11.9 for Render deployment
│   ├── .env.example            — template for environment variables
│   ├── alembic/
│   │   └── versions/           — database migration files
│   ├── tests/
│   │   ├── conftest.py         — shared fixtures (client, isolated DB per test)
│   │   └── test_urls.py        — 12 tests covering all core behaviours
│   └── app/
│       ├── config.py           — reads .env file, exposes a single settings object
│       ├── database.py         — async engine, session factory, get_db dependency
│       ├── models.py           — URL table definition using SQLAlchemy ORM
│       ├── schemas.py          — Pydantic request/response shapes with field validators
│       ├── redis_client.py     — cache helpers, stores expiry in JSON value
│       └── routers/
│           └── urls.py         — all API endpoints: shorten, redirect, stats
└── frontend/
    └── src/
        ├── App.jsx             — entire React UI: state, fetch calls, conditional rendering
        └── index.css           — styling
```

---

## Getting Started

You need Docker, Python 3.11+, and Node.js 18+ installed.

**1. Clone the repo and start the databases**

```bash
git clone https://github.com/shivam-tamboli/url-shortner.git
cd url-shortner
docker compose up -d
```

**2. Set up the backend**

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

**3. Set up the frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and the app is ready.

API docs are auto-generated at `http://localhost:8000/docs`.

---

## Running Tests

Tests require Docker to be running (they hit the real local database).

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

All 12 tests should pass. They cover shortening, redirecting, stats, custom codes, expiry, and all validation edge cases. Each test uses a UUID-based URL so they never conflict with each other or with real data.

---

## Deployment

The project is deployed across two platforms.

**Backend — Render**

- Create a PostgreSQL database on Render and copy the internal connection URL
- Create a Redis instance on Render and copy the internal Redis URL
- Create a Web Service pointing to the `backend/` directory
- Set build command: `pip install -r requirements.txt && alembic upgrade head`
- Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add all environment variables from `.env.example` using Render's production values

**Frontend — Vercel**

- Import the GitHub repo into Vercel
- Set root directory to `frontend`, framework to Vite
- Add one environment variable: `VITE_API_BASE = https://your-render-backend-url.onrender.com`
- Deploy — Vercel handles everything else automatically

**After both are deployed**

Go back to Render and update `ALLOWED_ORIGINS` to include your Vercel URL. This tells the backend to accept requests from your frontend domain.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/shorten` | Submit a long URL, get a short code back |
| `GET` | `/{short_code}` | Redirect to the original URL |
| `GET` | `/api/stats/{short_code}` | See click count for a link |
| `GET` | `/health` | Check if the server is running |

**Request fields**

| Field | Type | Required | Rules |
|---|---|---|---|
| `url` | string | yes | must be a valid URL |
| `custom_code` | string | no | 1–10 chars, letters/numbers/hyphens/underscores only |
| `expiry_hours` | integer | no | must be greater than 0, max 87600 (10 years) |

**Shorten a URL (basic)**

```bash
curl -X POST http://localhost:8000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'
```

```json
{
  "short_code": "kX9mQz",
  "short_url": "http://localhost:8000/kX9mQz",
  "long_url": "https://google.com",
  "expires_at": null
}
```

**Shorten a URL with custom code and expiry**

```bash
curl -X POST http://localhost:8000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com", "custom_code": "google", "expiry_hours": 24}'
```

```json
{
  "short_code": "google",
  "short_url": "http://localhost:8000/google",
  "long_url": "https://google.com",
  "expires_at": "2026-06-25T10:00:00+00:00"
}
```

**Check stats**

```bash
curl http://localhost:8000/api/stats/kX9mQz
```

```json
{
  "short_code": "kX9mQz",
  "long_url": "https://google.com",
  "clicks": 14,
  "expires_at": null
}
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the values.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | — |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `BASE_URL` | Base URL used when generating short links | `http://localhost:8000` |
| `ALLOWED_ORIGINS` | Comma-separated list of frontend URLs allowed by CORS | `http://localhost:5173` |

---

## Design Decisions

**Why Redis alongside PostgreSQL?**
PostgreSQL is the source of truth — it stores everything permanently. Redis sits in front of it as a cache. For a URL shortener, the same short codes get hit repeatedly. Without Redis, every redirect would query the database. With Redis, the first visit fetches from PostgreSQL, stores the result in Redis, and every visit after that is served from memory in under a millisecond.

**Why background tasks for click counting?**
When someone clicks a short link, they should be redirected instantly. Incrementing a database counter is a write operation that adds latency. By using FastAPI's BackgroundTasks, the redirect happens immediately and the counter update runs after the response is already sent. The user never waits for it.

**Why cache the URL on write, not just on first read?**
When a new URL is created, it gets stored in Redis immediately — not just when it is first visited. This means the very first click is also served from cache. Without this, the first visitor always hits the database. It is a small optimisation that costs nothing.

**Why check for existing long URLs before creating a new short code?**
If someone shortens the same URL twice, they should get the same short code back. Creating two different short codes for the same destination would waste database rows and confuse users. The deduplication check keeps the system clean.

**Why return 409 for a taken custom code instead of auto-generating a fallback?**
When a user explicitly picks a custom code, they have a reason for that exact name. Silently giving them a random code instead would be confusing — they would not know their choice was rejected. A 409 Conflict is honest and lets them pick a different name.

**Why set Redis TTL to match expires_at instead of running a cleanup job?**
The simplest correct solution. If the Redis TTL matches the expiry duration exactly, the cache entry disappears automatically when the link expires — no extra work needed. A separate cleanup job would be another moving part that can fail. Redis handles it for free.

---

## Known Limitations

- **Cold starts on Render free tier** — the backend spins down after 15 minutes of inactivity. The first request after a period of no traffic can take 30–60 seconds to respond. This is a free tier limitation, not a code issue.
- **No user authentication** — anyone can create short links. There is no concept of ownership, so a user cannot see or manage links they created.
- **Expired rows stay in PostgreSQL** — when a link expires, the row is not deleted. The redirect just returns 410. A background cleanup job could remove expired rows over time, but that is not implemented.

---

## Challenges

The trickiest part of this project was making async SQLAlchemy work correctly in all the right places. FastAPI uses async functions throughout, and passing a database session created in one context into a background task — which runs after the response is already sent — silently fails. The session is closed by then. The fix was to give the background task its own independent session rather than inheriting one from the request. That kind of bug does not show up until you test with a real background task running after a real response.

Getting Alembic to work with async SQLAlchemy also required a full rewrite of the generated `env.py`. The default Alembic setup is synchronous. Running it as-is against an async engine just hangs. Once you understand why — sync code cannot await async calls — the fix is straightforward, but the error message points nowhere useful.

Deployment order also matters more than expected. The backend has to be live before the frontend is deployed, because the frontend needs the backend URL as a build-time environment variable. Getting CORS wrong in either direction — backend not allowing the frontend origin, or frontend calling the wrong URL — produces errors that look like network failures, not CORS failures. Reading the browser network tab carefully was the only way to diagnose it.
