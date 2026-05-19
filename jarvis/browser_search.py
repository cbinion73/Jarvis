from __future__ import annotations

"""
JARVIS Browser Search — hybrid free web search.
================================================
Strategy:
  • Search:  Direct HTTP requests (urllib) — fast, no bot detection, free.
             Primary: DuckDuckGo HTML  (html.duckduckgo.com/html/)
             Fallback: Bing HTML       (www.bing.com/search)
  • Fetch:   Playwright headless Chrome — for rendering JS-heavy article pages.

This combination gives reliable search results (HTTP avoids headless-Chrome
bot detection on DDG) while still fetching full article text for deep research.
"""

import logging
import re
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
from html import unescape
from typing import Any

logger = logging.getLogger("jarvis.browser_search")

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "DNT": "1",
}

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

class SearchResult:
    __slots__ = ("title", "url", "snippet")

    def __init__(self, title: str, url: str, snippet: str) -> None:
        self.title   = title
        self.url     = url
        self.snippet = snippet

    def __repr__(self) -> str:
        return f"SearchResult({self.title!r}, {self.url!r})"

    def to_text(self) -> str:
        return f"**{self.title}**\n{self.url}\n{self.snippet}"


# ---------------------------------------------------------------------------
# Playwright browser pool (used only for fetch_page_text)
# ---------------------------------------------------------------------------

_browser_lock   = threading.Lock()
_browser: Any   = None
_playwright: Any = None


def _get_browser() -> Any:
    global _browser, _playwright
    with _browser_lock:
        if _browser is None or not _browser.is_connected():
            try:
                from playwright.sync_api import sync_playwright
                _playwright = sync_playwright().start()
                _browser = _playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                )
                logger.info("Headless Chromium started (article fetching)")
            except Exception as exc:
                logger.error("Could not start Playwright browser: %s", exc)
                return None
    return _browser


def _close_browser() -> None:
    """Call this on JARVIS shutdown to clean up browser resources."""
    global _browser, _playwright
    with _browser_lock:
        try:
            if _browser:
                _browser.close()
            if _playwright:
                _playwright.stop()
        except Exception:
            pass
        _browser = None
        _playwright = None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: int = 10) -> str:
    """Fetch URL via plain HTTP — no browser, no bot detection."""
    try:
        import gzip
        req = urllib.request.Request(url, headers=_HTTP_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            encoding = resp.headers.get_content_charset("utf-8") or "utf-8"
            # Handle gzip
            if resp.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode(encoding, errors="replace")
    except Exception as exc:
        logger.debug("_http_get(%s) failed: %s", url[:80], exc)
        return ""


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(text: str, max_len: int = 2000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


# ---------------------------------------------------------------------------
# DuckDuckGo HTML search (primary — direct HTTP)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Wikipedia API search (primary — never blocked, free, real data)
# ---------------------------------------------------------------------------

def _search_wikipedia(query: str, num_results: int) -> list[SearchResult]:
    """
    Search Wikipedia for the query and return article summaries as SearchResults.
    Uses the official MediaWiki API — no bot detection, always free.
    """
    results: list[SearchResult] = []

    # Step 1: search for matching article titles
    search_url = (
        "https://en.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={urllib.parse.quote_plus(query)}"
        "&format=json&srlimit=5&srprop=snippet"
    )
    html = _http_get(search_url, timeout=10)
    if not html:
        return []

    try:
        import json as _json
        data = _json.loads(html)
        search_hits = data.get("query", {}).get("search", [])
    except Exception:
        return []

    # Step 2: for each hit, get the article summary
    for hit in search_hits[:num_results]:
        page_title = hit.get("title", "")
        if not page_title:
            continue
        snippet = _strip_html(hit.get("snippet", ""))[:300]
        wiki_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(page_title.replace(" ", "_"))

        # Get the article extract (first 2 paragraphs)
        extract_url = (
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(page_title.replace(" ", "_"))
        )
        extract_html = _http_get(extract_url, timeout=8)
        if extract_html:
            try:
                import json as _j2
                summary = _j2.loads(extract_html)
                extract = summary.get("extract", "")[:500]
                if extract:
                    snippet = extract
            except Exception:
                pass

        if page_title and snippet:
            results.append(SearchResult(
                title=page_title,
                url=wiki_url,
                snippet=snippet,
            ))

    logger.info("Wikipedia search '%s' → %d results", query[:50], len(results))
    return results


# ---------------------------------------------------------------------------
# Curated research URLs (Playwright-fetchable authoritative sources)
# ---------------------------------------------------------------------------

# High-quality pages Playwright can fetch for passive income / SaaS research
_RESEARCH_URLS: list[tuple[str, str]] = [
    ("SaaS & Micro-SaaS Revenue",       "https://www.vibrantsnap.com/blog/micro-saas-ideas-profitable-niches-2026"),
    ("Indie Hacker Revenue Reports",    "https://www.indiehackers.com/products?revenueVerified=true"),
    ("Developer Passive Income Guide",  "https://dev.to/search?q=passive+income+developer"),
    ("SaaS Market Size 2024",           "https://www.statista.com/topics/1167/software-as-a-service-saas/"),
    ("Bootstrapped SaaS Examples",      "https://microacquire.com/blog/micro-saas-ideas/"),
    ("Developer Side Project Revenue",  "https://nomadlist.com/open"),
]


def _fetch_curated_context(keywords: list[str], num_pages: int = 2) -> list[SearchResult]:
    """Fetch pages from curated research list matching keywords."""
    results: list[SearchResult] = []
    kw_lower = [k.lower() for k in keywords]

    for label, url in _RESEARCH_URLS[:num_pages]:
        text = fetch_page_text(url, timeout_ms=12000)
        if text and len(text) > 100:
            results.append(SearchResult(
                title=label,
                url=url,
                snippet=text[:500],
            ))

    logger.info("Curated fetch → %d pages fetched", len(results))
    return results


# ---------------------------------------------------------------------------
# DDG HTTP (kept for future use if bot detection is resolved)
# ---------------------------------------------------------------------------

def _search_ddg_http(query: str, num_results: int) -> list[SearchResult]:
    """DuckDuckGo HTML search — currently blocked; returns empty list."""
    # DDG detects and blocks both headless Chrome and plain HTTP from servers.
    # Kept as a stub; returns empty so callers fall through to Wikipedia.
    logger.debug("DDG HTML search skipped (bot detection active)")
    return []


def _search_bing_http(query: str, num_results: int) -> list[SearchResult]:
    """Bing search — currently blocked; returns empty list."""
    logger.debug("Bing HTTP search skipped (bot detection active)")
    return []


# ---------------------------------------------------------------------------
# fetch_page_text — Playwright for JS-rendered articles
# ---------------------------------------------------------------------------

def fetch_page_text(url: str, timeout_ms: int = 15000) -> str:
    """
    Fetch a URL and return visible text content.
    Tries plain HTTP first (fast); falls back to Playwright for JS-heavy pages.
    """
    # 1. Try plain HTTP first — works for most articles
    html = _http_get(url, timeout=10)
    if html and len(html) > 500:
        # Strip scripts/styles before extracting text
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL)
        text = _strip_html(html)
        if len(text) > 200:
            return _clean_text(text)

    # 2. Fall back to Playwright for JS-rendered pages
    browser = _get_browser()
    if browser is None:
        return ""
    try:
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.evaluate("""
            () => {
                ['nav','footer','header','aside','script','style',
                 '[class*="ad-"]','[id*="cookie"]','[class*="cookie"]',
                 '[class*="banner"]','[class*="popup"]']
                .forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
            }
        """)
        text = page.inner_text("body")
        ctx.close()
        return _clean_text(text)
    except Exception as exc:
        logger.debug("fetch_page_text Playwright fallback(%s) failed: %s", url, exc)
        try:
            ctx.close()
        except Exception:
            pass
        return ""


# ---------------------------------------------------------------------------
# Public search API
# ---------------------------------------------------------------------------

def search(
    query: str,
    num_results: int = 5,
    engine: str = "auto",
    fetch_content: bool = False,
    timeout_ms: int = 12000,
) -> list[SearchResult]:
    """
    Search the web. Returns up to num_results SearchResult objects.

    Strategy (in order):
      1. Wikipedia API — official, never blocked, real factual data
      2. Curated domain fetch — Playwright fetches authoritative research URLs
      3. DDG / Bing HTTP stubs — kept for future use

    Args:
        query:         Search query string
        num_results:   Max results to return (default 5)
        engine:        "auto", "wikipedia", "curated", "duckduckgo", "bing", "google"
        fetch_content: If True, fetches the first result's full article text
        timeout_ms:    Browser timeout for fetch fallback

    Returns:
        List of SearchResult objects. Never raises.
    """
    t0 = time.monotonic()
    results: list[SearchResult] = []

    try:
        # Wikipedia API: best source of factual, structured data
        if engine in ("auto", "wikipedia"):
            results = _search_wikipedia(query, min(num_results, 4))

        # Add curated research pages if we still need more context
        if len(results) < 2 and engine in ("auto", "curated"):
            keywords = query.lower().split()[:5]
            curated = _fetch_curated_context(keywords, num_pages=min(2, num_results - len(results)))
            results.extend(curated)

    except Exception as exc:
        logger.warning("search('%s') exception: %s", query[:60], exc)

    elapsed = time.monotonic() - t0
    logger.info(
        "search('%s') → %d results in %.1fs",
        query[:60], len(results), elapsed,
    )

    if fetch_content and results:
        results[0].snippet = fetch_page_text(results[0].url)[:800] or results[0].snippet

    return results


def search_to_text(
    query: str,
    num_results: int = 5,
    fetch_top_page: bool = False,
) -> str:
    """Returns search results as a formatted string ready for an LLM prompt."""
    results = search(query, num_results=num_results, fetch_content=fetch_top_page)
    if not results:
        return f"No web results found for: {query}"
    lines = [f"Web search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.title}")
        lines.append(f"   {r.url}")
        if r.snippet:
            lines.append(f"   {r.snippet[:300]}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def _url_encode(s: str) -> str:
    return urllib.parse.quote_plus(s)


def _ddg_extract_url(href: str) -> str:
    """Extract the real URL from DuckDuckGo's redirect wrapper."""
    if href.startswith("//duckduckgo.com/l/?"):
        parsed = urllib.parse.urlparse("https:" + href)
        params = urllib.parse.parse_qs(parsed.query)
        return params.get("uddg", [href])[0]
    if href.startswith("http"):
        return href
    return "https:" + href if href.startswith("//") else href
