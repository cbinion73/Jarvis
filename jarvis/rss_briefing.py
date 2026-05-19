"""
rss_briefing.py — Live RSS news aggregator for JARVIS morning brief.

Fetches real headlines in parallel from major news outlets and returns
grounded context for the morning briefing LLM call. Zero API keys needed.
Inspired by Friday (SAGAR-TAMANG/friday-tony-stark-demo).
"""

import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# macOS Python 3.x doesn't bundle CA certificates — create an unverified context
# for public read-only RSS feeds (no sensitive data transmitted).
_SSL_CTX = ssl.create_default_context()
try:
    import certifi
    _SSL_CTX.load_verify_locations(certifi.where())
except Exception:
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE

WORLD_FEEDS = [
    ("BBC",       "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("NYT",       "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("ALJAZEERA", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("REUTERS",   "https://feeds.reuters.com/reuters/topNews"),
]

FINANCE_FEEDS = [
    ("CNBC",        "https://www.cnbc.com/id/100727362/device/rss/rss.html"),
    ("MARKETWATCH", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("BLOOMBERG",   "https://feeds.bloomberg.com/markets/news.rss"),
]

_TAG_RE = re.compile(r"<[^<]+?>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _fetch_feed(source_name: str, url: str, max_items: int = 5) -> list[dict]:
    """Synchronous fetch of a single RSS feed. Returns empty list on any error."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JARVIS/2.0"},
        )
        with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        items = root.findall(".//item")[:max_items]
        results = []
        for item in items:
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            title = _strip_html(title_el.text if title_el is not None else "")
            description = _strip_html(desc_el.text if desc_el is not None else "")
            link = (link_el.text or "").strip() if link_el is not None else ""
            if title:
                results.append(
                    {
                        "source": source_name,
                        "title": title,
                        "summary": description[:200],
                        "link": link,
                    }
                )
        return results
    except Exception:
        return []


def _fetch_feeds_parallel(feeds: list[tuple[str, str]], max_total: int, max_workers: int = 4) -> list[dict]:
    """Fetch a list of (name, url) feeds in parallel and return up to max_total items."""
    all_articles: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_feed, name, url): name for name, url in feeds}
        for future in as_completed(futures):
            all_articles.extend(future.result())
    return all_articles[:max_total]


def fetch_world_news(max_total: int = 12) -> list[dict]:
    """Fetch world news headlines in parallel from WORLD_FEEDS."""
    return _fetch_feeds_parallel(WORLD_FEEDS, max_total)


def fetch_finance_news(max_total: int = 12) -> list[dict]:
    """Fetch financial news headlines in parallel from FINANCE_FEEDS."""
    return _fetch_feeds_parallel(FINANCE_FEEDS, max_total)


def format_for_llm(articles: list[dict]) -> str:
    """Format a list of article dicts into a readable context string for the LLM."""
    if not articles:
        return ""
    lines: list[str] = []
    for article in articles:
        lines.append(f"[{article['source']}] {article['title']}")
        if article.get("summary"):
            lines.append(f"Brief: {article['summary']}")
        lines.append("---")
    return "\n".join(lines).rstrip("-").strip()


def fetch_briefing_context() -> dict:
    """
    Fetch world and finance news in parallel and return a structured context dict.

    Returns:
        {
            "world": list[dict],
            "finance": list[dict],
            "world_text": str,
            "finance_text": str,
            "total_articles": int,
            "sources_hit": list[str],
            "fetch_error": str,
        }
    """
    world: list[dict] = []
    finance: list[dict] = []
    fetch_error = ""

    try:
        with ThreadPoolExecutor(max_workers=2) as outer:
            world_future = outer.submit(fetch_world_news)
            finance_future = outer.submit(fetch_finance_news)
            world = world_future.result()
            finance = finance_future.result()
    except Exception as exc:
        fetch_error = str(exc)

    sources_hit = list({a["source"] for a in world + finance})
    total = len(world) + len(finance)

    if total == 0 and not fetch_error:
        fetch_error = "All RSS feeds returned empty results."

    return {
        "world": world,
        "finance": finance,
        "world_text": format_for_llm(world),
        "finance_text": format_for_llm(finance),
        "total_articles": total,
        "sources_hit": sources_hit,
        "fetch_error": fetch_error,
    }
