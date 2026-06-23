import random
import string

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models import URL
from app.schemas import ShortenRequest, ShortenResponse, URLInfo
from app.redis_client import get_cached_url, set_cached_url
from app.config import settings

router = APIRouter()


def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


async def increment_click_count(short_code: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(URL).where(URL.short_code == short_code))
        url = result.scalars().first()
        if url:
            url.clicks += 1
            await db.commit()


@router.post("/api/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest, db: AsyncSession = Depends(get_db)):
    long_url = str(request.url)

    result = await db.execute(select(URL).where(URL.long_url == long_url))
    existing = result.scalars().first()
    if existing:
        return ShortenResponse(
            short_code=existing.short_code,
            short_url=f"{settings.base_url}/{existing.short_code}",
            long_url=existing.long_url,
        )

    while True:
        code = generate_short_code()
        result = await db.execute(select(URL).where(URL.short_code == code))
        if not result.scalars().first():
            break

    new_url = URL(short_code=code, long_url=long_url)
    db.add(new_url)
    await db.commit()
    await db.refresh(new_url)

    await set_cached_url(new_url.short_code, new_url.long_url)

    return ShortenResponse(
        short_code=new_url.short_code,
        short_url=f"{settings.base_url}/{new_url.short_code}",
        long_url=new_url.long_url,
    )


@router.get("/api/stats/{short_code}", response_model=URLInfo)
async def get_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalars().first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return URLInfo(
        short_code=url.short_code,
        long_url=url.long_url,
        clicks=url.clicks,
    )


@router.get("/{short_code}")
async def redirect_url(
    short_code: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    cached_url = await get_cached_url(short_code)
    if cached_url:
        background_tasks.add_task(increment_click_count, short_code)
        return RedirectResponse(url=cached_url, status_code=307)

    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalars().first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    await set_cached_url(short_code, url.long_url)
    background_tasks.add_task(increment_click_count, short_code)

    return RedirectResponse(url=url.long_url, status_code=307)
