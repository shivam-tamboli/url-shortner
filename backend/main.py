from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import urls
from app.config import settings

app = FastAPI(
    title="URL Shortener",
    description="A URL shortening service built with FastAPI",
    version="1.0.0",
)

origins = [origin.strip() for origin in settings.allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
