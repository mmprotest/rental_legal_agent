"""Law retriever agent using the curated offline corpus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from api.models.schemas import CaseCategory, LawSearchResponse, LawSearchResult
from knowledge import LAW_SOURCES


@dataclass
class RetrievalContext:
    results: List[LawSearchResult]


class LawRetrieverAgent:
    """Keyword matching against the curated knowledge base."""

    def __init__(self) -> None:
        # runtime_index stores url -> (result, keywords)
        self._runtime_index: Dict[str, tuple[LawSearchResponse.__args__[0], List[str]]] = {}

    def add_runtime(self, result: LawSearchResponse.__args__[0], keywords: List[str]) -> None:
        self._runtime_index[result.source_url] = (result, keywords)

    def retrieve(
        self,
        query: str,
        category: Optional[CaseCategory] = None,
        top_k: int = 8,
    ) -> RetrievalContext:
        scores: List[tuple[int, LawSearchResult]] = []
        query_lower = query.lower()
        # static sources
        for source in LAW_SOURCES:
            score = 0
            if category:
                if category == CaseCategory.REPAIRS_URGENT or category == CaseCategory.REPAIRS_NONURGENT:
                    if "repairs" in source.keywords:
                        score += 3
                if category == CaseCategory.RENT_INCREASE and "rent" in source.keywords:
                    score += 3
                if category == CaseCategory.MINIMUM_STANDARDS and "minimum standards" in source.summary.lower():
                    score += 3
                if category == CaseCategory.NOTICE_TO_VACATE and "notice" in source.summary.lower():
                    score += 3
            for keyword in source.keywords:
                if keyword.lower() in query_lower:
                    score += 2
            if any(term in query_lower for term in source.summary.lower().split()[:10]):
                score += 1
            if score:
                result = LawSearchResult(
                    source_url=source.url,
                    title=source.title,
                    snippet=source.summary,
                    as_of_date=source.as_of,
                )
                scores.append((score, result))
        # runtime sources
        for url, (res, keywords) in self._runtime_index.items():
            score = 0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 2
            if score:
                scores.append((score, res))
        scores.sort(key=lambda item: item[0], reverse=True)
        top_results = [result for _, result in scores[:top_k]]
        if len(top_results) < top_k:
            seen_urls = {result.source_url for result in top_results}
            for source in LAW_SOURCES:
                if source.url in seen_urls:
                    continue
                top_results.append(
                    LawSearchResult(
                        source_url=source.url,
                        title=source.title,
                        snippet=source.summary,
                        as_of_date=source.as_of,
                    )
                )
                seen_urls.add(source.url)
                if len(top_results) >= top_k:
                    break
            # fill from runtime if still short
            if len(top_results) < top_k:
                for url, (res, _) in self._runtime_index.items():
                    if url in seen_urls:
                        continue
                    top_results.append(res)
                    seen_urls.add(url)
                    if len(top_results) >= top_k:
                        break
        return RetrievalContext(results=top_results)

    def search(self, query: str, top_k: int) -> LawSearchResponse:
        context = self.retrieve(query=query, top_k=top_k)
        return LawSearchResponse(results=context.results)
