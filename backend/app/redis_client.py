import redis.asyncio as aioredis
from app.config import settings

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

CACHE_TTL = 86400


async def get_cached_url(short_code: str) -> str | None:
    try:
        return await redis_client.get(short_code)
    except Exception:
        return None


async def set_cached_url(short_code: str, long_url: str, ttl: int = CACHE_TTL) -> None:
    try:
        await redis_client.set(short_code, long_url, ex=ttl)
    except Exception:
        pass


async def delete_cached_url(short_code: str) -> None:
    try:
        await redis_client.delete(short_code)
    except Exception:
        pass
