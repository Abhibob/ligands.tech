"""Pluggable search provider abstraction.

Each provider wraps an external search API and returns a list of
RawSearchResult objects for downstream reranking.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawSearchResult:
    """A single search result before reranking."""

    title: str
    url: str
    snippet: str


class SearchProvider(ABC):
    """Abstract base class for web search providers."""

    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> list[RawSearchResult]:
        ...


class BraveSearchProvider(SearchProvider):
    """Brave Web Search API provider."""

    API_URL = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, num_results: int = 10) -> list[RawSearchResult]:
        import httpx

        api_key = os.environ.get("BRAVE_API_KEY", "")
        if not api_key:
            raise RuntimeError("BRAVE_API_KEY environment variable is not set")

        resp = httpx.get(
            self.API_URL,
            headers={"Accept": "application/json", "Accept-Encoding": "gzip", "X-Subscription-Token": api_key},
            params={"q": query, "count": min(num_results, 20)},
            timeout=30.0,
        )
        resp.raise_for_status()

        results: list[RawSearchResult] = []
        for item in resp.json().get("web", {}).get("results", []):
            results.append(
                RawSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                )
            )
        return results[:num_results]


_PROVIDERS: dict[str, type[SearchProvider]] = {
    "brave": BraveSearchProvider,
}


def get_search_provider(name: str = "brave") -> SearchProvider:
    """Factory function to get a search provider by name."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown search provider: {name!r}. Available: {list(_PROVIDERS)}")
    return cls()
