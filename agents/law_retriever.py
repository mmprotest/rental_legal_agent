"""Law retriever agent using the curated offline corpus.

Adds a lightweight semantic-like retriever:
- Tokenizes title/summary/keywords
- Builds TF–IDF vectors over static + runtime sources
- Expands the query (LLM-backed when available) and uses cosine similarity
Fallbacks to keyword scoring if needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from typing import Dict, List, Optional, Tuple

from api.models.schemas import CaseCategory, LawSearchResponse, LawSearchResult
from knowledge import LAW_SOURCES
from llm import LLMClient, ChatMessage


@dataclass
class RetrievalContext:
    results: List[LawSearchResult]


class LawRetrieverAgent:
    """Hybrid retriever with lightweight TF–IDF and optional LLM query expansion."""

    def __init__(self) -> None:
        # Runtime corpus additions
        self._runtime_index: Dict[str, Tuple[LawSearchResult, List[str]]] = {}
        # Cached TF–IDF index
        self._built = False
        self._vocab: Dict[str, int] = {}
        self._doc_terms: List[List[str]] = []
        self._doc_ids: List[str] = []
        self._doc_results: List[LawSearchResult] = []
        self._df_counts: List[int] = []  # per-term document frequency
        self._tfidf_vectors: List[List[float]] = []
        # LLM (optional) for query expansion
        self._llm = LLMClient()

    def add_runtime(self, result: LawSearchResult, keywords: List[str]) -> None:
        self._runtime_index[result.source_url] = (result, keywords)
        self._built = False  # mark index dirty

    # -------------------------- Indexing --------------------------
    def _tokenize(self, text: str) -> List[str]:
        tokens = []
        word = []
        for ch in text.lower():
            if ch.isalnum():
                word.append(ch)
            else:
                if word:
                    tokens.append("".join(word))
                    word = []
        if word:
            tokens.append("".join(word))
        return tokens

    def _collect_corpus(self) -> List[Tuple[str, LawSearchResult, List[str]]]:
        corpus: List[Tuple[str, LawSearchResult, List[str]]] = []
        for src in LAW_SOURCES:
            res = LawSearchResult(
                source_url=src.url,
                title=src.title,
                snippet=src.summary,
                as_of_date=src.as_of,
            )
            text = f"{src.title} {src.summary} {' '.join(src.keywords)}"
            corpus.append((text, res, src.keywords))
        for url, (res, keywords) in self._runtime_index.items():
            text = f"{res.title} {res.snippet} {' '.join(keywords)}"
            corpus.append((text, res, keywords))
        return corpus

    def _build_index(self) -> None:
        corpus = self._collect_corpus()
        self._vocab.clear()
        self._doc_terms.clear()
        self._doc_ids.clear()
        self._doc_results.clear()
        # Build vocab and per-doc terms
        for text, res, _ in corpus:
            terms = self._tokenize(text)
            self._doc_terms.append(terms)
            self._doc_ids.append(res.source_url)
            self._doc_results.append(res)
            for t in set(terms):
                if t not in self._vocab:
                    self._vocab[t] = len(self._vocab)
        # DF counts
        vocab_size = len(self._vocab)
        df = [0] * vocab_size
        for terms in self._doc_terms:
            seen = set()
            for t in terms:
                idx = self._vocab[t]
                if idx not in seen:
                    df[idx] += 1
                    seen.add(idx)
        self._df_counts = df
        # TF–IDF vectors
        N = max(1, len(self._doc_terms))
        self._tfidf_vectors = []
        for terms in self._doc_terms:
            tf: Dict[int, int] = {}
            for t in terms:
                idx = self._vocab[t]
                tf[idx] = tf.get(idx, 0) + 1
            # L2-normalized TF–IDF
            vec = [0.0] * vocab_size
            for idx, count in tf.items():
                idf = log(N / (1 + self._df_counts[idx])) + 1.0
                vec[idx] = (count / len(terms)) * idf
            # normalize
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vec = [v / norm for v in vec]
            self._tfidf_vectors.append(vec)
        self._built = True

    def _ensure_index(self) -> None:
        if not self._built:
            self._build_index()

    # ----------------------- Query expansion ----------------------
    def _expand_query(self, query: str) -> str:
        base = query.strip()
        # If LLM is in http mode, try expansion
        try:
            expansion = self._llm.chat(
                [
                    ChatMessage(role="system", content="Generate 3 short paraphrases and legal synonyms, comma-separated."),
                    ChatMessage(role="user", content=base),
                ],
                temperature=0.2,
            )
            # Keep short line
            extra = expansion.split("\n")[0]
            if len(extra) > 200:
                extra = extra[:200]
            return f"{base} {extra}"
        except Exception:
            # Offline/simple fallback synonyms
            synonyms: Dict[str, List[str]] = {
                "noise": ["nuisance", "quiet enjoyment", "loud", "disturbance"],
                "rent": ["increase", "assessment", "notice"],
                "repair": ["urgent", "hot water", "heating", "fix"],
                "notice": ["eviction", "vacate", "termination"],
                "standard": ["minimum", "heater", "electrical"],
            }
            ql = base.lower()
            extra_terms = []
            for key, syns in synonyms.items():
                if key in ql:
                    extra_terms.extend(syns)
            return base + (" " + " ".join(extra_terms) if extra_terms else "")

    def retrieve(
        self,
        query: str,
        category: Optional[CaseCategory] = None,
        top_k: int = 8,
    ) -> RetrievalContext:
        self._ensure_index()
        expanded = self._expand_query(query)
        q_terms = self._tokenize(expanded)
        if not q_terms:
            return RetrievalContext(results=[])
        # Build query TF–IDF
        vocab_size = len(self._vocab)
        q_tf: Dict[int, int] = {}
        for t in q_terms:
            if t in self._vocab:
                idx = self._vocab[t]
                q_tf[idx] = q_tf.get(idx, 0) + 1
        if not q_tf:
            # Fallback to keyword-only scoring if no overlap
            # Simple reuse of summaries as last resort
            candidates = [*self._doc_results]
            return RetrievalContext(results=candidates[:top_k])
        N = max(1, len(self._doc_terms))
        q_vec = [0.0] * vocab_size
        total_q = sum(q_tf.values()) or 1
        for idx, count in q_tf.items():
            idf = log(N / (1 + self._df_counts[idx])) + 1.0
            q_vec[idx] = (count / total_q) * idf
        q_norm = sum(v * v for v in q_vec) ** 0.5 or 1.0
        q_vec = [v / q_norm for v in q_vec]
        # Cosine similarity
        scored: List[Tuple[float, LawSearchResult]] = []
        for vec, res in zip(self._tfidf_vectors, self._doc_results):
            sim = sum(a * b for a, b in zip(q_vec, vec))
            scored.append((sim, res))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [res for sim, res in scored[:top_k] if sim > 0]
        # If we got nothing with positive similarity, fallback to first k
        if not results:
            results = self._doc_results[:top_k]
        return RetrievalContext(results=results)

    def search(self, query: str, top_k: int) -> LawSearchResponse:
        context = self.retrieve(query=query, top_k=top_k)
        return LawSearchResponse(results=context.results)
