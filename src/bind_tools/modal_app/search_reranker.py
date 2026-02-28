"""Modal class for web search + BGE reranker.

Calls an external search API, then reranks results using
BAAI/bge-reranker-v2-m3 (cross-encoder) and returns normalised scores.
"""

from __future__ import annotations

import math

import modal

from ._base import SEARCH_TIMEOUT, app
from .images import reranker_image


@app.cls(
    image=reranker_image,
    secrets=[modal.Secret.from_name("search-api-keys")],
    timeout=SEARCH_TIMEOUT,
    allow_concurrent_inputs=5,
    container_idle_timeout=300,
)
class SearchReranker:
    @modal.enter()
    def warmup(self):
        from FlagEmbedding import FlagReranker

        self.reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=False)

    @modal.method()
    def search_and_rerank(
        self,
        query: str,
        num_results: int = 10,
        provider: str = "brave",
    ) -> dict:
        from .search_providers import get_search_provider

        # 1. Call search provider
        search_provider = get_search_provider(provider)
        raw_results = search_provider.search(query, num_results=num_results)

        if not raw_results:
            return {
                "query": query,
                "provider": provider,
                "results": [],
                "num_raw": 0,
                "num_reranked": 0,
            }

        # 2. Build [query, "title. snippet"] pairs
        pairs = [[query, f"{r.title}. {r.snippet}"] for r in raw_results]

        # 3. Compute reranker scores (raw logits)
        raw_scores = self.reranker.compute_score(pairs)

        # Edge case: compute_score returns a bare float for a single pair
        if isinstance(raw_scores, (float, int)):
            raw_scores = [raw_scores]

        # 4. Sigmoid normalize to [0, 1]
        def sigmoid(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-x))

        scored = []
        for result, score in zip(raw_results, raw_scores):
            scored.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "score": round(sigmoid(score), 6),
            })

        # 5. Sort descending by score
        scored.sort(key=lambda x: x["score"], reverse=True)

        return {
            "query": query,
            "provider": provider,
            "results": scored,
            "num_raw": len(raw_results),
            "num_reranked": len(scored),
        }
