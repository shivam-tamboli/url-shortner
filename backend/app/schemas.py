import re
from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = None
    expiry_hours: int | None = None

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not 1 <= len(v) <= 10:
            raise ValueError("must be between 1 and 10 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("can only contain letters, numbers, hyphens, and underscores")
        return v

    @field_validator("expiry_hours")
    @classmethod
    def validate_expiry_hours(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v <= 0:
            raise ValueError("must be greater than 0")
        if v > 87600:
            raise ValueError("cannot exceed 87600 hours (10 years)")
        return v


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
