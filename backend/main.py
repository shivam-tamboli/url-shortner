from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import urls

app = FastAPI(
    title="URL Shortener",
    description="A URL shortening service built with FastAPI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(urls.router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        pass


@app.get("/health")
async def health_check():
    return {"status": "ok"}
