from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .browser_search import search

try:
    from langchain_core.documents import Document
except ModuleNotFoundError:  # pragma: no cover - exercised via fallback tests
    Document = None  # type: ignore[assignment]


@dataclass(slots=True)
class RetrievalDocument:
    page_content: str
    metadata: dict[str, Any]


def langchain_documents_available() -> bool:
    return Document is not None


def retrieve_research_documents(
    query: str,
    *,
    limit: int = 3,
    fetch_content: bool = True,
) -> list[RetrievalDocument]:
    results = search(
        query,
        num_results=max(1, int(limit)),
        fetch_content=fetch_content,
    )
    documents: list[RetrievalDocument] = []
    for index, item in enumerate(results[:limit], start=1):
        snippet = str(getattr(item, "snippet", "") or "").strip()
        title = str(getattr(item, "title", "") or "Untitled result").strip()
        url = str(getattr(item, "url", "") or "").strip()
        page_content = f"{title}\n{snippet}".strip()
        if not page_content:
            continue
        documents.append(
            RetrievalDocument(
                page_content=page_content,
                metadata={
                    "title": title,
                    "url": url,
                    "rank": index,
                    "source": "browser_search",
                },
            )
        )
    return documents


def retrieve_research_material(
    query: str,
    *,
    limit: int = 3,
    fetch_content: bool = True,
) -> list[dict[str, Any]]:
    documents = retrieve_research_documents(
        query,
        limit=limit,
        fetch_content=fetch_content,
    )
    material: list[dict[str, Any]] = []
    for item in documents:
        material.append(
            {
                "title": str(item.metadata.get("title", "")).strip(),
                "url": str(item.metadata.get("url", "")).strip(),
                "snippet": item.page_content.split("\n", 1)[-1].strip()[:800],
                "source": str(item.metadata.get("source", "browser_search")).strip(),
                "rank": int(item.metadata.get("rank", 0) or 0),
            }
        )
    return material


def as_langchain_documents(
    query: str,
    *,
    limit: int = 3,
    fetch_content: bool = True,
) -> list[Any]:
    documents = retrieve_research_documents(
        query,
        limit=limit,
        fetch_content=fetch_content,
    )
    if Document is None:
        return documents
    return [
        Document(page_content=item.page_content, metadata=dict(item.metadata))
        for item in documents
    ]
