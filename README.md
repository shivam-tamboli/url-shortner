# URL Shortener

A full-stack URL shortening service built with FastAPI, PostgreSQL, Redis, and React.

## Features

- Shorten any long URL to a 6-character code
- Instant redirects via Redis caching
- Click count tracking per short link
- Stats endpoint to view link performance
- Graceful fallback to PostgreSQL if Redis is unavailable

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python |
| Database | PostgreSQL |
| Cache | Redis |
| Frontend | React + Vite |
| Local infrastructure | Docker + docker-compose |

## Project Structure

```
url-shortener/
├── docker-compose.yml        # PostgreSQL and Redis containers
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variable template
│   ├── alembic/              # Database migrations
│   └── app/
│       ├── config.py         # Settings from .env
│       ├── database.py       # Async PostgreSQL connection
│       ├── models.py         # SQLAlchemy URL model
│       ├── schemas.py        # Pydantic request/response schemas
│       ├── redis_client.py   # Redis cache client
│       └── routers/
│           └── urls.py       # URL endpoints
└── frontend/
    └── src/
        └── App.jsx           # React UI
```

## Setup and Run

### Prerequisites
- Docker
- Python 3.11+
- Node.js 18+

### 1. Start the databases

```bash
docker compose up -d
```

### 2. Set up the backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/shorten` | Shorten a long URL |
| GET | `/{short_code}` | Redirect to original URL |
| GET | `/api/stats/{short_code}` | Get click stats for a short link |
| GET | `/health` | Health check |

## How It Works

1. User submits a long URL
2. Backend generates a random 6-character short code
3. URL is saved to PostgreSQL and cached in Redis
4. When the short link is visited, Redis is checked first (fast path)
5. On Redis miss, PostgreSQL is queried and result is cached for next time
6. Click count is incremented in the background after every redirect
