"""Factory for instantiating web search providers based on configuration."""

from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.services.search.base import BaseSearchProvider
from app.services.search.providers import (
    BraveSearchProvider,
    DuckDuckGoSearchProvider,
    MockSearchProvider,
    SerperSearchProvider,
    TavilySearchProvider,
)

logger = logging.getLogger(__name__)


def get_search_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseSearchProvider:
    """Return a configured search provider instance.

    Supported providers:
    - 'tavily': Requires Tavily API key.
    - 'brave': Requires Brave Search API key.
    - 'serper': Requires Serper.dev API key.
    - 'duckduckgo': Free, no API key required.
    - 'mock': In-memory mock results for testing/offline work.
    """
    chosen = (provider_name or settings.search_provider or "duckduckgo").strip().lower()

    if chosen == "mock":
        return MockSearchProvider()

    if chosen == "tavily":
        key = api_key or settings.tavily_api_key or settings.search_api_key
        if not key:
            raise ValueError(
                "Tavily search provider requires TAVILY_API_KEY or SEARCH_API_KEY environment variable."
            )
        return TavilySearchProvider(api_key=key)

    if chosen == "brave":
        key = api_key or settings.brave_api_key or settings.search_api_key
        if not key:
            raise ValueError(
                "Brave search provider requires BRAVE_API_KEY or SEARCH_API_KEY environment variable."
            )
        return BraveSearchProvider(api_key=key)

    if chosen == "serper":
        key = api_key or settings.serper_api_key or settings.search_api_key
        if not key:
            raise ValueError(
                "Serper search provider requires SERPER_API_KEY or SEARCH_API_KEY environment variable."
            )
        return SerperSearchProvider(api_key=key)

    if chosen == "duckduckgo":
        return DuckDuckGoSearchProvider()

    logger.warning(
        "Unknown search provider '%s'. Falling back to DuckDuckGoSearchProvider.", chosen
    )
    return DuckDuckGoSearchProvider()
