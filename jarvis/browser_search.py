from __future__ import annotations

"""
JARVIS Browser Search — hybrid free web search.
================================================
Search strategy (in priority order):
  1. Tavily Search API  — AI-optimized, pre-cleaned content, free 1k/month
                          Requires: TAVILY_API_KEY in .env
                          Sign up:  https://tavily.com  (free, no CC)
  2. Brave Search API   — real-time independent index, free 2k/month
                          Requires: BRAVE_SEARCH_API_KEY in .env
                          Sign up:  https://brave.com/search/api/
  3. Wikipedia API      — encyclopedic fallback, always free, never blocked
  4. Curated fetch      — Playwright for specific authoritative research URLs

Fetch strategy (for full article text):
  1. Plain HTTP         — fast, works for most articles
  2. Playwright Chrome  — headless fallback for JS-rendered pages
"""

import json
import logging
import os
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
        data = json.loads(html)
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
                summary = json.loads(extract_html)
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
# Tavily Search API (tier 1 — AI-optimized, pre-cleaned, free 1k/month)
# Built for LLM agents: returns relevant content, not raw HTML.
# Sign up: https://tavily.com — free plan, no credit card
# Set TAVILY_API_KEY in .env
# ---------------------------------------------------------------------------

def _search_tavily(query: str, num_results: int, deep: bool = False) -> list[SearchResult]:
    """
    Tavily Search — AI-optimized results with pre-extracted content.
    Returns cleaned article text in the snippet, not just a description.
    Use deep=True for research tasks (fetches full page content per result).
    Returns empty list if key not configured or request fails.
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []

    payload = json.dumps({
        "api_key":              api_key,
        "query":                query,
        "search_depth":         "advanced" if deep else "basic",
        "include_answer":       False,
        "include_raw_content":  False,
        "max_results":          min(num_results, 10),
        "include_domains":      [],
        "exclude_domains":      [],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept":        "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results: list[SearchResult] = []
        for item in data.get("results", [])[:num_results]:
            title   = item.get("title", "")
            url_    = item.get("url", "")
            # Tavily returns `content` — pre-extracted relevant text, not raw HTML
            snippet = item.get("content", "") or item.get("snippet", "")
            if title and url_:
                results.append(SearchResult(
                    title=title,
                    url=url_,
                    snippet=snippet[:600],
                ))
        logger.info("Tavily search '%s' → %d results", query[:50], len(results))
        return results

    except urllib.error.HTTPError as exc:
        logger.warning("Tavily search HTTP %s: %s", exc.code, exc.reason)
        return []
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return []


def research(query: str, num_results: int = 5) -> list[SearchResult]:
    """
    Deep research search using Tavily advanced mode.
    Returns full extracted content per result — ideal for agent research tasks.
    Falls back to standard search() if Tavily unavailable.
    """
    if os.getenv("TAVILY_API_KEY"):
        results = _search_tavily(query, num_results, deep=True)
        if results:
            return results
    return search(query, num_results=num_results)


# ---------------------------------------------------------------------------
# Brave Search API (tier 2 — real-time index, free 2,000/month, no CC needed)
# Sign up: https://brave.com/search/api/
# Set BRAVE_SEARCH_API_KEY in .env
# ---------------------------------------------------------------------------

def _search_brave(query: str, num_results: int) -> list[SearchResult]:
    """
    Brave Search API — independent index, real-time results, free up to 2k/month.
    Returns empty list if key not configured or request fails.
    """
    import json as _json
    api_key = os.getenv("BRAVE_SEARCH_API_KEY", "")
    if not api_key:
        return []

    url = (
        "https://api.search.brave.com/res/v1/web/search"
        f"?q={urllib.parse.quote_plus(query)}"
        f"&count={min(num_results, 10)}"
        "&search_lang=en"
        "&text_decorations=false"
        "&safesearch=moderate"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Accept":                "application/json",
            "Accept-Encoding":       "gzip",
            "X-Subscription-Token": api_key,
        },
    )
    try:
        import gzip as _gzip
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
            if resp.info().get("Content-Encoding") == "gzip":
                raw = _gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))

        results: list[SearchResult] = []
        for item in data.get("web", {}).get("results", [])[:num_results]:
            title   = item.get("title", "")
            url_    = item.get("url", "")
            snippet = item.get("description", "") or item.get("extra_snippets", [""])[0]
            if title and url_:
                results.append(SearchResult(
                    title=title,
                    url=url_,
                    snippet=snippet[:400],
                ))
        logger.info("Brave search '%s' → %d results", query[:50], len(results))
        return results

    except urllib.error.HTTPError as exc:
        logger.warning("Brave search HTTP %s: %s", exc.code, exc.reason)
        return []
    except Exception as exc:
        logger.warning("Brave search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# DDG HTTP (kept for future use if bot detection is resolved)
# ---------------------------------------------------------------------------

def _search_ddg_http(query: str, num_results: int) -> list[SearchResult]:
    """DuckDuckGo HTML search — currently blocked; returns empty list."""
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
      1. Tavily  — AI-optimized, pre-cleaned content, free 1k/month (TAVILY_API_KEY)
      2. Brave   — real-time independent index, free 2k/month (BRAVE_SEARCH_API_KEY)
      3. Wikipedia — encyclopedic fallback, always free, no key needed
      4. Curated   — Playwright fetches of authoritative research URLs

    Args:
        query:         Search query string
        num_results:   Max results to return (default 5)
        engine:        "auto", "tavily", "brave", "wikipedia", "curated"
        fetch_content: If True, fetches the first result's full article text
        timeout_ms:    Browser timeout for fetch fallback

    Returns:
        List of SearchResult objects. Never raises.
    """
    t0 = time.monotonic()
    results: list[SearchResult] = []
    backend_used = "wikipedia"

    try:
        # 1. Tavily: AI-optimized content, best for agent research tasks
        if engine in ("auto", "tavily") and os.getenv("TAVILY_API_KEY"):
            results = _search_tavily(query, num_results)
            if results:
                backend_used = "tavily"

        # 2. Brave: real-time live web results
        if len(results) < 2 and engine in ("auto", "brave") and os.getenv("BRAVE_SEARCH_API_KEY"):
            brave = _search_brave(query, num_results - len(results))
            results.extend(brave)
            if brave:
                backend_used = "brave" if backend_used == "wikipedia" else backend_used

        # 3. Wikipedia: encyclopedic fallback
        if len(results) < 2 and engine in ("auto", "wikipedia"):
            wiki = _search_wikipedia(query, min(num_results - len(results), 4))
            results.extend(wiki)

        # 4. Curated domain fetch
        if len(results) < 2 and engine in ("auto", "curated"):
            keywords = query.lower().split()[:5]
            curated = _fetch_curated_context(
                keywords, num_pages=min(2, num_results - len(results))
            )
            results.extend(curated)

    except Exception as exc:
        logger.warning("search('%s') exception: %s", query[:60], exc)

    elapsed = time.monotonic() - t0
    logger.info(
        "search('%s') → %d results via %s in %.1fs",
        query[:60], len(results), backend_used, elapsed,
    )

    if fetch_content and results:
        results[0].snippet = fetch_page_text(results[0].url)[:800] or results[0].snippet

    return results


def _results_to_text(query: str, results: list[SearchResult], snippet_len: int = 300) -> str:
    """Format a list of SearchResult objects into an LLM-ready string."""
    if not results:
        return f"No web results found for: {query}"
    lines = [f"Web search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.title}")
        lines.append(f"   {r.url}")
        if r.snippet:
            lines.append(f"   {r.snippet[:snippet_len]}")
        lines.append("")
    return "\n".join(lines)


def search_to_text(
    query: str,
    num_results: int = 5,
    fetch_top_page: bool = False,
) -> str:
    """Returns search results as a formatted string ready for an LLM prompt."""
    results = search(query, num_results=num_results, fetch_content=fetch_top_page)
    return _results_to_text(query, results)


def research_to_text(
    query: str,
    num_results: int = 5,
) -> str:
    """
    Deep research search — returns AI-optimized full content per result.
    Uses Tavily advanced mode when available; falls back to standard search.
    Ideal for agent research tasks where content quality matters most.
    """
    results = research(query, num_results=num_results)
    return _results_to_text(query, results, snippet_len=600)


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
