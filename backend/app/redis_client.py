import json
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.config import settings

redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

CACHE_TTL = 86400


async def get_cached_url(short_code: str) -> tuple[str | None, datetime | None]:
    try:
        raw = await redis_client.get(short_code)
        if not raw:
            return None, None
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and "u" in payload:
                expires_at = (
                    datetime.fromtimestamp(payload["e"], tz=timezone.utc)
                    if "e" in payload
                    else None
                )
                return payload["u"], expires_at
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        # backward compat: old cached entries are plain URL strings
        return raw, None
    except Exception:
        return None, None


async def set_cached_url(
    short_code: str,
    long_url: str,
    ttl: int = CACHE_TTL,
    expires_at: datetime | None = None,
) -> None:
    try:
        payload: dict = {"u": long_url}
        if expires_at is not None:
            payload["e"] = expires_at.timestamp()
        await redis_client.set(short_code, json.dumps(payload), ex=ttl)
    except Exception:
        pass


async def delete_cached_url(short_code: str) -> None:
    try:
        await redis_client.delete(short_code)
    except Exception:
        pass
