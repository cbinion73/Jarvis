"""
JARVIS Tool: web
================
Search the web via DuckDuckGo or fetch and extract text from any URL.
"""
from __future__ import annotations

import re
import urllib.parse

import httpx

from .base import ApprovalFlag, ToolResult

# ---------------------------------------------------------------------------
# Anthropic tool schema
# ---------------------------------------------------------------------------

DEFINITION: dict = {
    "name": "web",
    "description": (
        "Search the web (via DuckDuckGo) or fetch a URL and return its plain-text content. "
        "Use 'search' to find pages relevant to a query; use 'fetch' to retrieve and read "
        "a specific URL. HTML is stripped; only meaningful text is returned."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["search", "fetch"],
                "description": "Whether to search the web or fetch a specific URL.",
            },
            "query": {
                "type": "string",
                "description": "Search query (used with 'search').",
            },
            "url": {
                "type": "string",
                "description": "Full URL to fetch (used with 'fetch').",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return. Default 5.",
                "default": 5,
            },
        },
        "required": ["operation"],
    },
}


# ---------------------------------------------------------------------------
# Approval logic
# ---------------------------------------------------------------------------

def needs_approval(inputs: dict) -> ApprovalFlag:  # noqa: ARG001
    """Web operations never require approval."""
    return ApprovalFlag.NONE


# ---------------------------------------------------------------------------
# HTML utilities
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s{2,}")
_SEARCH_RESULT_RE = re.compile(
    r'<a[^>]+class=["\']result__a["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_FETCH_LIMIT = 6_000
_TRUNCATION_NOTE = "\n\n[content truncated — showing first 6 000 chars]"


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = _TAG_RE.sub(" ", html)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

async def run(
    operation: str,
    query: str = "",
    url: str = "",
    max_results: int = 5,
) -> ToolResult:
    """Perform the requested web operation and return a ToolResult."""

    # ------------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------------
    if operation == "search":
        if not query:
            return ToolResult(output="'query' is required for the search operation.", error=True)

        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; JARVIS/1.0; +https://jarvis.local)"
                    )
                }
                resp = await client.get(search_url, headers=headers)
                resp.raise_for_status()
                html = resp.text
        except httpx.TimeoutException:
            return ToolResult(output="Search timed out. Try again or narrow your query.", error=True)
        except httpx.HTTPStatusError as exc:
            return ToolResult(
                output=f"Search request failed with HTTP {exc.response.status_code}.", error=True
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output=f"Search error: {exc}", error=True)

        # Extract result anchors — DDG HTML format
        matches = _SEARCH_RESULT_RE.findall(html)

        if not matches:
            # Fallback: grab any anchors with http URLs as a best-effort
            fallback_re = re.compile(
                r'href=["\']?(https?://[^\s"\'<>]+)["\']?[^>]*>(.*?)</a>',
                re.DOTALL | re.IGNORECASE,
            )
            matches = fallback_re.findall(html)

        results: list[str] = []
        seen_urls: set[str] = set()
        for href, title_html in matches:
            title = _strip_html(title_html).strip()
            href = href.strip()
            if not href or not title:
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            results.append(f"{len(results) + 1}. {title}\n   {href}")
            if len(results) >= max_results:
                break

        if not results:
            return ToolResult(
                output=f"No results found for: {query}",
                error=False,
            )

        output = f"Search results for: {query}\n\n" + "\n\n".join(results)
        return ToolResult(output=output, error=False, metadata={"query": query, "result_count": len(results)})

    # ------------------------------------------------------------------
    # FETCH
    # ------------------------------------------------------------------
    if operation == "fetch":
        if not url:
            return ToolResult(output="'url' is required for the fetch operation.", error=True)

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; JARVIS/1.0; +https://jarvis.local)"
                    )
                }
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text
        except httpx.TimeoutException:
            return ToolResult(output=f"Fetch timed out for URL: {url}", error=True)
        except httpx.HTTPStatusError as exc:
            return ToolResult(
                output=f"HTTP {exc.response.status_code} fetching {url}", error=True
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(output=f"Fetch error: {exc}", error=True)

        text = _strip_html(html)
        truncated = False
        if len(text) > _FETCH_LIMIT:
            text = text[:_FETCH_LIMIT] + _TRUNCATION_NOTE
            truncated = True

        return ToolResult(
            output=f"Content from {url}:\n\n{text}",
            error=False,
            metadata={"url": url, "truncated": truncated},
        )

    # ------------------------------------------------------------------
    # Unknown operation
    # ------------------------------------------------------------------
    return ToolResult(
        output=f"Unknown operation: '{operation}'. Must be one of: search, fetch.",
        error=True,
    )
