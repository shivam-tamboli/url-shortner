# URL Shortener

A full-stack URL shortener built with FastAPI, PostgreSQL, Redis, and React. Paste a long URL, get a short link. Click the short link, get redirected instantly.

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

---

## Project Structure

```
url-shortener/
├── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── alembic/
│   │   └── versions/
│   └── app/
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── redis_client.py
│       └── routers/
│           └── urls.py
└── frontend/
    └── src/
        ├── App.jsx
        └── index.css
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
