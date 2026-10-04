"""
Shared service to resolve, validate, and scrape social-media URLs into NormalizedPost.
Used by both /api/v1/scrape and /api/v1/analyze.
"""

import logging

from app.core.timing import timed_stage
from app.platforms.base import BasePlatformScraper
from app.platforms.detector import detect_platform
from app.platforms.facebook import FacebookScraper
from app.platforms.instagram import InstagramScraper
from app.schemas.post import NormalizedPost

logger = logging.getLogger(__name__)

# Registry of implemented platform scrapers
_SCRAPERS: dict[str, type[BasePlatformScraper]] = {
    "instagram": InstagramScraper,
    "facebook": FacebookScraper,
}

# Platforms recognized by detector but not yet implemented
_NOT_IMPLEMENTED_MESSAGES: dict[str, str] = {
    "reddit": "Reddit scraping is not implemented yet.",
    "twitter": "Twitter/X scraping is not implemented yet.",
    "threads": "Threads scraping is not implemented yet.",
}


class PlatformNotSupportedError(ValueError):
    """Raised when the URL cannot be mapped to any known platform."""
    def __init__(self, platform: str, message: str) -> None:
        super().__init__(message)
        self.platform = platform
        self.message = message


class PlatformNotImplementedError(NotImplementedError):
    """Raised when the platform is recognized but scraping is not implemented."""
    def __init__(self, platform: str, message: str) -> None:
        super().__init__(message)
        self.platform = platform
        self.message = message


async def scrape_social_post(url: str) -> NormalizedPost:
    """
    Detect platform and execute the corresponding scraper to obtain a NormalizedPost.

    Raises:
        PlatformNotSupportedError: if platform is unknown
        PlatformNotImplementedError: if platform is recognized but not supported
        ValueError: if platform URL validation fails
        RuntimeError: if scraping fails
    """
    clean_url = url.strip()
    with timed_stage("PLATFORM_DETECTION"):
        platform = detect_platform(clean_url)
    logger.info("Detecting platform for URL %s: %s", clean_url, platform)

    if platform == "unknown":
        raise PlatformNotSupportedError("unknown", "Unsupported or invalid URL.")

    if platform in _NOT_IMPLEMENTED_MESSAGES:
        raise PlatformNotImplementedError(platform, _NOT_IMPLEMENTED_MESSAGES[platform])

    scraper_cls = _SCRAPERS.get(platform)
    if not scraper_cls:
        raise PlatformNotSupportedError(platform, f"Platform '{platform}' is not handled.")

    scraper = scraper_cls()
    async with timed_stage("SCRAPE", metadata={"platform": platform}):
        return await scraper.scrape(clean_url)
