from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = None
    expiry_hours: int | None = None


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    expires_at: datetime | None = None


class URLInfo(BaseModel):
    short_code: str
    long_url: str
    clicks: int
    expires_at: datetime | None = None
