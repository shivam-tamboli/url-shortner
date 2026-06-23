import random
import string

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import URL
from app.schemas import ShortenRequest, ShortenResponse

router = APIRouter()

BASE_URL = "http://localhost:8000"


def generate_short_code(length: int = 6) -> str:
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


@router.post("/api/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest, db: AsyncSession = Depends(get_db)):
    long_url = str(request.url)

    result = await db.execute(select(URL).where(URL.long_url == long_url))
    existing = result.scalars().first()
    if existing:
        return ShortenResponse(
            short_code=existing.short_code,
            short_url=f"{BASE_URL}/{existing.short_code}",
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

    return ShortenResponse(
        short_code=new_url.short_code,
        short_url=f"{BASE_URL}/{new_url.short_code}",
        long_url=new_url.long_url,
    )


@router.get("/{short_code}")
async def redirect_url(short_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalars().first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return RedirectResponse(url=url.long_url, status_code=307)
