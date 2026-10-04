"""
Pydantic schemas for normalized post data across social-media platforms.

Universal schema:
    NormalizedPost
      ├── platform ("instagram" | "facebook" | "reddit" | "twitter" | "threads")
      ├── url (str)
      ├── author (Author | None)
      ├── text (str | None)
      ├── published_at (str | None)
      ├── media (list[Media])
      ├── external_links (list[str])
      └── metadata (dict)
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class Media(BaseModel):
    type: Literal["image", "video", "audio", "unknown"]
    url: str | None = None
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    ocr_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Author(BaseModel):
    name: str | None = None
    username: str | None = None
    profile_url: str | None = None
    profile_image_url: str | None = None
    id: str | None = None


class NormalizedPost(BaseModel):
    platform: Literal[
        "instagram",
        "facebook",
        "reddit",
        "twitter",
        "threads",
    ]
    url: str
    author: Author | None = None
    text: str | None = None
    published_at: str | None = None
    media: list[Media] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScrapeResult(BaseModel):
    """
    Internal container preserving raw platform data alongside normalized representation.
    """
    platform: str
    raw_data: dict[str, Any] = Field(default_factory=dict)
    normalized_data: NormalizedPost


# ── API-level response envelopes ─────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str


class SuccessResponse(BaseModel):
    status: str = "success"
    platform: str
    data: NormalizedPost


class NotImplementedResponse(BaseModel):
    status: str = "not_implemented"
    platform: str = "unknown"
    message: str


class ErrorResponse(BaseModel):
    status: str = "error"
    platform: str = "unknown"
    message: str
