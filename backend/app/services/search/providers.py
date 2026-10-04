"""Concrete implementations of web search providers."""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx

from app.services.search.base import BaseSearchProvider

logger = logging.getLogger(__name__)


class TavilySearchProvider(BaseSearchProvider):
    """Tavily Search API Provider."""

    def __init__(self, api_key: str, timeout: float = 10.0):
        if not api_key:
            raise ValueError("Tavily API key is required.")
        self.api_key = api_key
        self.timeout = timeout
        self.endpoint = "https://api.tavily.com/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": limit,
            "search_depth": "basic",
            "include_answer": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        raw_results = data.get("results", [])
        normalized = []
        for item in raw_results[:limit]:
            normalized.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "snippet": item.get("content") or item.get("snippet"),
                    "published_date": item.get("published_date"),
                }
            )
        return normalized


class BraveSearchProvider(BaseSearchProvider):
    """Brave Search API Provider."""

    def __init__(self, api_key: str, timeout: float = 10.0):
        if not api_key:
            raise ValueError("Brave API key is required.")
        self.api_key = api_key
        self.timeout = timeout
        self.endpoint = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.endpoint, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        raw_results = data.get("web", {}).get("results", [])
        normalized = []
        for item in raw_results[:limit]:
            normalized.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "snippet": item.get("description"),
                    "published_date": item.get("page_age") or item.get("age"),
                }
            )
        return normalized


class SerperSearchProvider(BaseSearchProvider):
    """Google Serper.dev Search API Provider."""

    def __init__(self, api_key: str, timeout: float = 10.0):
        if not api_key:
            raise ValueError("Serper API key is required.")
        self.api_key = api_key
        self.timeout = timeout
        self.endpoint = "https://api.serper.dev/search"

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {"q": query, "num": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        raw_results = data.get("organic", [])
        normalized = []
        for item in raw_results[:limit]:
            normalized.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("link") or "",
                    "snippet": item.get("snippet"),
                    "published_date": item.get("date"),
                }
            )
        return normalized


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """DuckDuckGo HTML-based search provider (no API key required)."""

    def __init__(self, timeout: float = 3.5):
        self.timeout = timeout
        self.endpoint = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # 1. Attempt DuckDuckGo HTML search
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.post(
                    self.endpoint,
                    headers=self.headers,
                    data={"q": query, "b": ""},
                )
                if response.status_code == 200:
                    results = self._parse_html(response.text, limit)
                    if results:
                        return results
        except Exception as exc:
            logger.info("DuckDuckGo HTML query failed or timed out: %s; trying web search fallback", exc)

        # 2. Fallback to Bing web search (free, no API key required, reliable when DDG is blocked by ISP)
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(
                    "https://www.bing.com/search",
                    params={"q": query},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if resp.status_code == 200:
                    return self._parse_bing_html(resp.text, limit)
        except Exception as exc:
            logger.warning("Bing web search fallback failed: %s", exc)

        return []

    def _parse_bing_html(self, html_text: str, limit: int) -> List[Dict[str, Any]]:
        import base64
        results: List[Dict[str, Any]] = []
        matches = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html_text, re.DOTALL)
        for m in matches:
            link = re.search(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', m)
            if not link:
                continue
            raw_url, raw_title = link.groups()
            actual_url = self._extract_bing_url(raw_url)
            clean_title = self._clean_html(raw_title)
            snip = re.search(r'<p[^>]*>(.*?)</p>', m)
            clean_snip = self._clean_html(snip.group(1)) if snip else None

            if actual_url and clean_title:
                results.append(
                    {
                        "title": clean_title,
                        "url": actual_url,
                        "snippet": clean_snip,
                        "published_date": None,
                    }
                )
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _extract_bing_url(raw_url: str) -> str:
        import base64
        unescaped = html.unescape(raw_url)
        match = re.search(r'[?&]u=a1([A-Za-z0-9+/=_-]+)', unescaped)
        if match:
            b64 = match.group(1).replace('-', '+').replace('_', '/')
            b64 += '=' * (-len(b64) % 4)
            try:
                decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                if decoded.startswith('http'):
                    return decoded
            except Exception:
                pass
        return raw_url

    def _parse_html(self, html_text: str, limit: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        # Match each result block
        # <a class="result__snippet" ...>...</a>
        # <a class="result__url" href="...">...</a>
        # <a class="result__a" href="...">title</a>
        pattern = re.compile(
            r'<div class="result results_links[^"]*">(.*?)</div>\s*</div>',
            re.DOTALL | re.IGNORECASE,
        )
        link_pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        snippet_pattern = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )

        blocks = pattern.findall(html_text)
        for block in blocks:
            link_match = link_pattern.search(block)
            if not link_match:
                continue

            raw_url, raw_title = link_match.groups()
            actual_url = self._extract_target_url(raw_url)
            clean_title = self._clean_html(raw_title)

            snippet_match = snippet_pattern.search(block)
            clean_snippet = self._clean_html(snippet_match.group(1)) if snippet_match else None

            if actual_url and clean_title:
                results.append(
                    {
                        "title": clean_title,
                        "url": actual_url,
                        "snippet": clean_snippet,
                        "published_date": None,
                    }
                )
            if len(results) >= limit:
                break

        return results

    @staticmethod
    def _extract_target_url(raw_url: str) -> str:
        # DDG redirects use /l/?uddg=...
        if "uddg=" in raw_url:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs and qs["uddg"]:
                return qs["uddg"][0]
        return raw_url

    @staticmethod
    def _clean_html(raw: str) -> str:
        if not raw:
            return ""
        # Remove HTML tags
        no_tags = re.sub(r"<[^>]+>", "", raw)
        # Unescape HTML entities
        unescaped = html.unescape(no_tags)
        return " ".join(unescaped.split())


class MockSearchProvider(BaseSearchProvider):
    """Mock search provider for testing and offline development."""

    def __init__(self, mock_results: Optional[List[Dict[str, Any]]] = None):
        self.mock_results = mock_results

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if self.mock_results is not None:
            return self.mock_results[:limit]

        # Generate sensible mock results containing query keywords
        return [
            {
                "title": f"Fact Check: News and reports regarding {query}",
                "url": f"https://example-news.org/fact-check/{urllib.parse.quote(query[:30])}",
                "snippet": f"Detailed reporting and verification of claims related to '{query}'.",
                "published_date": "2026-01-15",
            },
            {
                "title": f"Official Statement regarding {query}",
                "url": f"https://official-sources.gov/statements/{urllib.parse.quote(query[:20])}",
                "snippet": f"Official records and statements regarding the matter of '{query}'.",
                "published_date": "2026-01-16",
            },
        ][:limit]
