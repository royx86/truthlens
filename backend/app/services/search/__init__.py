"""Search package exposing base classes, providers, and factory."""

from app.services.search.base import BaseSearchProvider
from app.services.search.factory import get_search_provider
from app.services.search.providers import (
    BraveSearchProvider,
    DuckDuckGoSearchProvider,
    MockSearchProvider,
    SerperSearchProvider,
    TavilySearchProvider,
)

__all__ = [
    "BaseSearchProvider",
    "get_search_provider",
    "TavilySearchProvider",
    "BraveSearchProvider",
    "SerperSearchProvider",
    "DuckDuckGoSearchProvider",
    "MockSearchProvider",
]
