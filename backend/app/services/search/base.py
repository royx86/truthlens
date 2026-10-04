"""Base abstract interface for web search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseSearchProvider(ABC):
    """Abstract interface for pluggable web search providers."""

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Execute web search query and return raw search result dictionaries.

        Expected raw dictionary items should contain at least:
        - title: str
        - url: str
        - snippet: Optional[str] / description
        - published_date / date: Optional[str]
        """
        raise NotImplementedError
