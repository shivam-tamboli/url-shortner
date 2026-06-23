# URL Shortener

A full-stack URL shortener built with FastAPI, PostgreSQL, Redis, and React. Paste a long URL, get a short link. Click the short link, get redirected instantly.

**Live Demo → [url-shortner-eta-khaki.vercel.app](https://url-shortner-eta-khaki.vercel.app)**
**API Docs → [url-shortner-amlv.onrender.com/docs](https://url-shortner-amlv.onrender.com/docs)**

---

## What it does

- Turns any long URL into a short 6-character code
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
         (fast path)              (slow path)
              │                        │
              │               ┌────────▼────────┐
              │               │ Query PostgreSQL │
              │               └────────┬────────┘
              │                        │
              │                  ┌─────┴──────┐
              │                found       not found
              │                  │               │
              │        ┌─────────▼──────┐        │
              │        │ Store in Redis  │      404
              │        │  (cache warm)  │     error
              │        └─────────┬──────┘
              │                  │
              └──────────┬───────┘
                         │
                         ▼
              ┌───────────────────────┐
              │  Redirect user to     │
              │  original long URL    │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Increment click      │  ← runs in background
              │  count in PostgreSQL  │    user doesn't wait
              └───────────────────────┘
```

> First visit always hits PostgreSQL. Every visit after that is served from Redis.
> Click counting runs as a background task — it does not slow down the redirect.

---

## Diagram 3 — URL Shortening Flow

What happens when a user submits a long URL.

```
  User submits  →  https://very-long-url.com/some/path
                              │
                              ▼
                  ┌───────────────────────┐
                  │  Does this long URL    │
                  │  already exist in DB?  │
                  └───────────┬───────────┘
                              │
                 ┌────────────┴─────────────┐
                 │                          │
                YES                         NO
                 │                          │
                 │              ┌───────────▼───────────┐
                 │              │  Generate random code  │
                 │              │  e.g. "kX9mQz"        │
                 │              │  (62 chars, 6 picks)   │
                 │              └───────────┬───────────┘
                 │                          │
                 │              ┌───────────▼───────────┐
                 │              │  Code already taken    │
                 │              │  in database?          │
                 │              └─────┬──────────┬───────┘
                 │                   YES         NO
                 │                   │            │
                 │                   └── retry ◄──┘
                 │                          │
                 │              ┌───────────▼───────────┐
                 │              │  Save to PostgreSQL    │
                 │              │  Cache in Redis        │
                 │              └───────────┬───────────┘
                 │                          │
                 └────────────┬─────────────┘
                              │
                              ▼
                  Return →  http://localhost:8000/kX9mQz
```

> Same long URL always returns the same short code — no duplicates created.
> 62 characters × 6 picks = 56 billion possible codes.

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
  └─────────────┴──────────────┴──────────────────────────────────────┘

  Indexes
  └── ix_urls_short_code  →  short_code column (unique)
                              every redirect searches by this column
```

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
│   ├── requirements.txt        — all Python dependencies with pinned versions
│   ├── .python-version         — pins Python 3.11.9 for Render deployment
│   ├── .env.example            — template for environment variables
│   ├── alembic/
│   │   └── versions/           — database migration files
│   └── app/
│       ├── config.py           — reads .env file, exposes a single settings object
│       ├── database.py         — async engine, session factory, get_db dependency
│       ├── models.py           — URL table definition using SQLAlchemy ORM
│       ├── schemas.py          — Pydantic request and response shapes
│       ├── redis_client.py     — get, set, delete cache helpers with graceful fallback
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

**Shorten a URL**

```bash
curl -X POST http://localhost:8000/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'
```

```json
{
  "short_code": "kX9mQz",
  "short_url": "http://localhost:8000/kX9mQz",
  "long_url": "https://google.com"
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
  "clicks": 14
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

---

## Known Limitations

- **Cold starts on Render free tier** — the backend spins down after 15 minutes of inactivity. The first request after a period of no traffic can take 30–60 seconds to respond. This is a free tier limitation, not a code issue.
- **No user authentication** — anyone can create short links. There is no concept of ownership, so a user cannot see or manage links they created.
- **No custom short codes** — codes are randomly generated. Users cannot choose their own vanity URLs like `/my-link`.
- **No link expiry** — links live forever. There is no TTL on the database rows.

---

## Challenges

The trickiest part of this project was making async SQLAlchemy work correctly in all the right places. FastAPI uses async functions throughout, and passing a database session created in one context into a background task — which runs after the response is already sent — silently fails. The session is closed by then. The fix was to give the background task its own independent session rather than inheriting one from the request. That kind of bug does not show up until you test with a real background task running after a real response.

Getting Alembic to work with async SQLAlchemy also required a full rewrite of the generated `env.py`. The default Alembic setup is synchronous. Running it as-is against an async engine just hangs. Once you understand why — sync code cannot await async calls — the fix is straightforward, but the error message points nowhere useful.

Deployment order also matters more than expected. The backend has to be live before the frontend is deployed, because the frontend needs the backend URL as a build-time environment variable. Getting CORS wrong in either direction — backend not allowing the frontend origin, or frontend calling the wrong URL — produces errors that look like network failures, not CORS failures. Reading the browser network tab carefully was the only way to diagnose it.
