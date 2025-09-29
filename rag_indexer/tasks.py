"""Placeholder module for the legal corpus indexing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List


@dataclass
class SourceDocument:
    url: str
    title: str
    captured_at: datetime
    content: str


@dataclass
class Chunk:
    source_url: str
    source_title: str
    as_of: datetime
    text: str


class IndexingPipeline:
    """Stubbed pipeline that would later integrate with pgvector or Chroma."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def run(self, documents: Iterable[SourceDocument]) -> List[Chunk]:
        """Return naive chunks by slicing the content."""

        chunks: List[Chunk] = []
        for document in documents:
            text = document.content
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunk_text = text[start:end]
                chunks.append(
                    Chunk(
                        source_url=document.url,
                        source_title=document.title,
                        as_of=document.captured_at,
                        text=chunk_text,
                    )
                )
                start += self.chunk_size - self.overlap
        return chunks

