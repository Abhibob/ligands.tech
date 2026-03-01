"""Exa web search runner — direct API calls, no external dependencies beyond httpx."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from bind_tools.common.errors import InputMissingError, UpstreamError

logger = logging.getLogger(__name__)

EXA_API_URL = "https://api.exa.ai/search"


def _get_api_key() -> str:
    key = os.environ.get("EXA_API_KEY", "")
    if not key:
        raise InputMissingError(
            "EXA_API_KEY environment variable is not set. "
            "Get a key at https://dashboard.exa.ai/api-keys"
        )
    return key


def search(
    query: str,
    *,
    num_results: int = 10,
    search_type: str = "auto",
    category: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_published_date: str | None = None,
    include_text: bool = True,
    include_highlights: bool = True,
    max_characters: int = 3000,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Search the web using Exa API.

    Returns a dict with:
      - query: the original query
      - results: list of result dicts with title, url, text, highlights, etc.
      - num_results: number of results returned
      - search_type: the search type used
    """
    api_key = _get_api_key()

    # Build contents request
    contents: dict[str, Any] = {}
    if include_text:
        contents["text"] = {"maxCharacters": max_characters}
    if include_highlights:
        contents["highlights"] = {"maxCharacters": min(max_characters, 1000)}

    # Build request body
    body: dict[str, Any] = {
        "query": query,
        "numResults": num_results,
        "type": search_type,
    }
    if contents:
        body["contents"] = contents
    if category:
        body["category"] = category
    if include_domains:
        body["includeDomains"] = include_domains
    if exclude_domains:
        body["excludeDomains"] = exclude_domains
    if start_published_date:
        body["startPublishedDate"] = start_published_date

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(EXA_API_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        raise UpstreamError(
            f"Exa API returned {e.response.status_code}: {e.response.text[:200]}"
        )
    except httpx.ConnectError:
        raise UpstreamError("Could not connect to Exa API (https://api.exa.ai)")
    except httpx.TimeoutException:
        raise UpstreamError(f"Exa API timed out after {timeout_s}s")

    # Parse results
    raw_results = data.get("results", [])
    results = []
    for r in raw_results:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "published_date": r.get("publishedDate"),
            "author": r.get("author"),
            "text": r.get("text", ""),
            "highlights": r.get("highlights", []),
            "highlight_scores": r.get("highlightScores", []),
            "summary": r.get("summary", ""),
        })

    return {
        "query": query,
        "search_type": data.get("searchType", search_type),
        "num_results": len(results),
        "results": results,
    }
