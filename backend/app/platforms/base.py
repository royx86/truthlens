"""
Abstract base class for platform scrapers.

Each platform scraper (InstagramScraper, RedditScraper, …) must:
  1. Inherit from BasePlatformScraper.
  2. Implement the async `scrape(url)` method.
  3. Return a NormalizedPost on success.
  4. Raise a descriptive exception on failure (caught by the route).
"""

from abc import ABC, abstractmethod

from app.schemas.post import NormalizedPost


class BasePlatformScraper(ABC):
    """Minimal interface that every platform scraper must satisfy."""

    @abstractmethod
    async def scrape(self, url: str) -> NormalizedPost:
        """
        Scrape the given URL and return a NormalizedPost.

        Args:
            url: The fully-qualified URL of the social-media post.

        Returns:
            A NormalizedPost with as many fields populated as the scraper
            can provide.

        Raises:
            ValueError:  If the URL is invalid for this platform.
            RuntimeError: If the external scraping service fails.
        """
        ...
