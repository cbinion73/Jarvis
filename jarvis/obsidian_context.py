from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "actually",
    "can",
    "do",
    "from",
    "for",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "jarvis",
    "know",
    "me",
    "my",
    "of",
    "obsidian",
    "on",
    "or",
    "right",
    "say",
    "tell",
    "that",
    "the",
    "this",
    "to",
    "what",
    "with",
    "you",
}


@dataclass(slots=True)
class ObsidianVaultSupport:
    vault_path: Path
    index_path: Path
    retriever_backend: str = "llamaindex"
    chunk_size: int = 768
    chunk_overlap: int = 80

    @property
    def enabled(self) -> bool:
        return self.vault_path.exists() and os.access(self.vault_path, os.R_OK)

    def status(self) -> dict[str, Any]:
        exists = self.vault_path.exists()
        readable = exists and os.access(self.vault_path, os.R_OK)
        markdown_files = self._markdown_files() if readable else []
        index_exists = self.index_path.exists()
        payload = {
            "enabled": bool(exists and readable),
            "vault_exists": exists,
            "vault_readable": readable,
            "vault_path": str(self.vault_path),
            "index_path": str(self.index_path),
            "index_exists": index_exists,
            "markdown_file_count": len(markdown_files),
            "requested_retriever_backend": self.retriever_backend,
            "active_retriever_backend": self._active_retriever_backend(),
            "llamaindex_available": _llamaindex_components() is not None,
        }
        if not exists:
            payload["detail"] = "Configured Obsidian vault path does not exist."
            return payload
        if not readable:
            payload["detail"] = "Configured Obsidian vault path is not readable."
            return payload
        payload["detail"] = "Obsidian vault is available for local retrieval."
        if index_exists:
            try:
                index_payload = json.loads(self.index_path.read_text(encoding="utf-8"))
                payload["indexed_at"] = str(index_payload.get("generated_at", "")).strip()
                payload["indexed_backend"] = str(index_payload.get("backend", "")).strip()
                payload["chunk_count"] = int(index_payload.get("chunk_count", 0) or 0)
            except (OSError, json.JSONDecodeError):
                pass
        return payload

    def retrieve(self, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        index = self.ensure_index()
        if str(index.get("backend", "")).strip() == "llamaindex":
            return self._retrieve_llamaindex(index, query, limit=limit)
        return self._retrieve_native(index, query, limit=limit)

    def _retrieve_native(self, index: dict[str, Any], query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        entries = list(index.get("files", []))
        terms = _query_terms(query)
        if not terms:
            return []
        ranked: list[tuple[float, dict[str, Any]]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            score = self._score_entry(entry, terms)
            if score <= 0:
                continue
            ranked.append((score, entry))
        ranked.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("title", "")),
                str(item[1].get("rel_path", "")),
            )
        )
        hits: list[dict[str, Any]] = []
        for score, entry in ranked[: max(1, limit)]:
            rel_path = str(entry.get("rel_path", "")).strip()
            path = self.vault_path / rel_path
            snippet = self._best_snippet(path, terms, fallback=str(entry.get("preview", "")))
            if not snippet:
                continue
            hits.append(
                {
                    "title": str(entry.get("title", "")).strip() or path.stem,
                    "rel_path": rel_path,
                    "source_path": str(path),
                    "score": round(score, 3),
                    "snippet": snippet,
                }
            )
        return hits

    def _retrieve_llamaindex(self, index: dict[str, Any], query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        terms = _query_terms(query)
        if not terms:
            return []
        ranked: list[tuple[float, dict[str, Any]]] = []
        for entry in list(index.get("chunks", [])):
            if not isinstance(entry, dict):
                continue
            score = self._score_chunk(entry, terms)
            if score <= 0:
                continue
            ranked.append((score, entry))
        ranked.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("title", "")),
                str(item[1].get("rel_path", "")),
                int(item[1].get("chunk_index", 0) or 0),
            )
        )
        hits: list[dict[str, Any]] = []
        for score, entry in ranked[: max(1, limit)]:
            rel_path = str(entry.get("rel_path", "")).strip()
            path = self.vault_path / rel_path
            snippet = _normalize_whitespace(str(entry.get("text", "") or str(entry.get("preview", ""))))[:320]
            if not snippet:
                snippet = self._best_snippet(path, terms, fallback=str(entry.get("preview", "")))
            if not snippet:
                continue
            hits.append(
                {
                    "title": str(entry.get("title", "")).strip() or path.stem,
                    "rel_path": rel_path,
                    "source_path": str(path),
                    "score": round(score, 3),
                    "snippet": snippet,
                }
            )
        return hits

    def conversation_context(self, query: str, *, limit: int = 3) -> str:
        hits = self.retrieve(query, limit=limit)
        if not hits:
            return ""
        lines = ["Retrieved Obsidian notes:"]
        for hit in hits:
            lines.append(f"- {hit['title']} ({hit['rel_path']}): {hit['snippet']}")
        return "\n".join(lines)

    def ensure_index(self) -> dict[str, Any]:
        if not self.enabled:
            return {"vault_path": str(self.vault_path), "files": [], "file_count": 0}
        cached = self._load_index()
        current_files = self._markdown_files()
        if self._index_matches(cached, current_files):
            return cached
        payload = {
            "vault_path": str(self.vault_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "backend": self._active_retriever_backend(),
            "file_count": len(current_files),
            "files": [self._index_entry(path) for path in current_files],
        }
        if payload["backend"] == "llamaindex":
            payload["chunks"] = self._llamaindex_chunks(current_files)
            payload["chunk_count"] = len(payload["chunks"])
        else:
            payload["chunk_count"] = 0
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return payload

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _index_matches(self, index_payload: dict[str, Any], current_files: list[Path]) -> bool:
        if str(index_payload.get("backend", "")).strip() != self._active_retriever_backend():
            return False
        indexed_files = list(index_payload.get("files", [])) if isinstance(index_payload, dict) else []
        if len(indexed_files) != len(current_files):
            return False
        expected = {
            str(path.relative_to(self.vault_path)): (path.stat().st_mtime_ns, path.stat().st_size)
            for path in current_files
        }
        for entry in indexed_files:
            if not isinstance(entry, dict):
                return False
            rel_path = str(entry.get("rel_path", "")).strip()
            if rel_path not in expected:
                return False
            expected_mtime, expected_size = expected[rel_path]
            if int(entry.get("mtime_ns", 0) or 0) != expected_mtime:
                return False
            if int(entry.get("size", 0) or 0) != expected_size:
                return False
        return True

    def _markdown_files(self) -> list[Path]:
        files = list(self.vault_path.rglob("*.md")) + list(self.vault_path.rglob("*.markdown"))
        return sorted(path for path in files if path.is_file())

    def _index_entry(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        stat = path.stat()
        title = self._extract_title(path, text)
        headings = self._extract_headings(text)
        preview = _normalize_whitespace(text)[:800]
        return {
            "rel_path": str(path.relative_to(self.vault_path)),
            "title": title,
            "headings": headings[:8],
            "preview": preview,
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }

    def _extract_title(self, path: Path, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or path.stem
        return path.stem

    def _extract_headings(self, text: str) -> list[str]:
        headings: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                headings.append(stripped.lstrip("#").strip())
        return headings

    def _score_entry(self, entry: dict[str, Any], terms: list[str]) -> float:
        title = str(entry.get("title", "")).lower()
        rel_path = str(entry.get("rel_path", "")).lower()
        headings = " ".join(str(item) for item in entry.get("headings", [])).lower()
        preview = str(entry.get("preview", "")).lower()
        score = 0.0
        for term in terms:
            if term in title:
                score += 5.0
            if term in headings:
                score += 3.0
            if term in preview:
                score += 2.0
            if term in rel_path:
                score += 1.0
        joined_query = " ".join(terms)
        if joined_query and joined_query in preview:
            score += 4.0
        return score

    def _score_chunk(self, entry: dict[str, Any], terms: list[str]) -> float:
        title = str(entry.get("title", "")).lower()
        rel_path = str(entry.get("rel_path", "")).lower()
        text = str(entry.get("text", "")).lower()
        preview = str(entry.get("preview", "")).lower()
        score = 0.0
        for term in terms:
            if term in title:
                score += 4.0
            if term in text:
                score += 3.0
            if term in preview:
                score += 2.0
            if term in rel_path:
                score += 1.0
        joined_query = " ".join(terms)
        if joined_query and joined_query in text:
            score += 5.0
        return score

    def _active_retriever_backend(self) -> str:
        requested = str(self.retriever_backend or "").strip().lower()
        if requested == "llamaindex" and _llamaindex_components() is not None:
            return "llamaindex"
        return "native"

    def _llamaindex_chunks(self, current_files: list[Path]) -> list[dict[str, Any]]:
        components = _llamaindex_components()
        if components is None:
            return []
        Document, SentenceSplitter = components
        documents: list[Any] = []
        for path in current_files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            documents.append(
                Document(
                    text=text,
                    metadata={
                        "rel_path": str(path.relative_to(self.vault_path)),
                        "title": self._extract_title(path, text),
                    },
                )
            )
        splitter = SentenceSplitter(
            chunk_size=max(128, int(self.chunk_size or 768)),
            chunk_overlap=max(0, int(self.chunk_overlap or 0)),
        )
        nodes = splitter.get_nodes_from_documents(documents)
        chunk_records: list[dict[str, Any]] = []
        for index, node in enumerate(nodes):
            metadata = dict(getattr(node, "metadata", {}) or {})
            rel_path = str(metadata.get("rel_path", "")).strip()
            title = str(metadata.get("title", "")).strip()
            text = _normalize_whitespace(_node_text(node))
            if not rel_path or not text:
                continue
            chunk_records.append(
                {
                    "chunk_index": index,
                    "rel_path": rel_path,
                    "title": title,
                    "text": text,
                    "preview": text[:320],
                }
            )
        return chunk_records

    def _best_snippet(self, path: Path, terms: list[str], *, fallback: str = "") -> str:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return _normalize_whitespace(fallback)[:320]
        chunks = _paragraph_chunks(text)
        if not chunks:
            return _normalize_whitespace(fallback)[:320]
        ranked: list[tuple[int, str]] = []
        for chunk in chunks:
            lowered = chunk.lower()
            score = sum(1 for term in terms if term in lowered)
            if score:
                ranked.append((score, chunk))
        if ranked:
            ranked.sort(key=lambda item: (-item[0], -len(item[1])))
            return ranked[0][1][:320]
        return chunks[0][:320]


def _query_terms(query: str) -> list[str]:
    terms = [
        token
        for token in re.findall(r"[a-z0-9]{3,}", str(query or "").lower())
        if token not in _STOPWORDS
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        unique.append(term)
    return unique


def _paragraph_chunks(text: str) -> list[str]:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    if cleaned.startswith("---\n"):
        closing = cleaned.find("\n---", 4)
        if closing != -1:
            cleaned = cleaned[closing + 4 :]
    paragraphs = re.split(r"\n\s*\n", cleaned)
    chunks: list[str] = []
    for paragraph in paragraphs:
        normalized = _normalize_whitespace(paragraph)
        if not normalized:
            continue
        if normalized.startswith("#"):
            continue
        chunks.append(normalized)
    return chunks


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _node_text(node: Any) -> str:
    getter = getattr(node, "get_content", None)
    if callable(getter):
        try:
            return str(getter() or "")
        except TypeError:
            return str(getter(metadata_mode="none") or "")
    return str(getattr(node, "text", "") or "")


def _llamaindex_components() -> tuple[Any, Any] | None:
    try:
        from llama_index.core import Document
        from llama_index.core.node_parser import SentenceSplitter
    except Exception:
        return None
    return Document, SentenceSplitter
