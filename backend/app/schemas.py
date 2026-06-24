from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = None


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str


class URLInfo(BaseModel):
    short_code: str
    long_url: str
    clicks: int
