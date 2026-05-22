"""
rss_briefing.py — Live RSS news aggregator + OG image enrichment for JARVIS.

Pipeline:
  1. Fetch RSS feeds in parallel (fast, ~2-3 s)
  2. Extract any images already embedded in RSS (media:content / enclosure)
  3. For articles still missing images, fetch Open Graph meta tags in parallel
     — reads only the first 16 KB of each page (head section), ~300-600 ms each
  4. Cache enriched results for 30 minutes — daytime loads are instant

Zero API keys needed. Cost: $0.
"""

import re
import ssl
import time
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

# ---------------------------------------------------------------------------
# Feed registry
# ---------------------------------------------------------------------------

WORLD_FEEDS = [
    ("BBC",       "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("NYT",       "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("ALJAZEERA", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("AP",        "https://feeds.apnews.com/apnews/topnews"),          # Reuters defunct; AP replaces it
]

FINANCE_FEEDS = [
    ("CNBC",        "https://www.cnbc.com/id/100727362/device/rss/rss.html"),
    ("MARKETWATCH", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("BLOOMBERG",   "https://feeds.bloomberg.com/markets/news.rss"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^<]+?>")

# Open Graph / Twitter Card patterns — property and content can appear in either order
_OG_IMAGE_PATS = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.I),
]
_OG_DESC_PATS = [
    re.compile(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']', re.I),
]

# 30-minute server-side cache
_CACHE: dict = {"data": None, "expires": 0.0}
_CACHE_TTL = 1800  # seconds


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


# ---------------------------------------------------------------------------
# OG meta fetcher — reads only the <head> section, ~16 KB max
# ---------------------------------------------------------------------------

def _fetch_og_meta(url: str) -> dict:
    """
    Fetch og:image and og:description from a URL by reading only the first 16 KB
    (enough to cover the <head> on any real news site).  Fast: ~300-600 ms.
    Returns {"image_url": str, "og_description": str}.
    """
    if not url or not url.startswith("http"):
        return {}
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/124.0 Safari/537.36",
                "Accept":          "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Range":           "bytes=0-16383",
            },
        )
        with urllib.request.urlopen(req, timeout=6, context=_SSL_CTX) as resp:
            raw = resp.read(16384).decode("utf-8", errors="ignore")

        # Discard everything after </head> — saves regex time
        head_end = raw.lower().find("</head>")
        if head_end > 0:
            raw = raw[:head_end + 8]

        image_url = ""
        for pat in _OG_IMAGE_PATS:
            m = pat.search(raw)
            if m:
                image_url = m.group(1).replace("&amp;", "&").strip()
                # Skip data URIs, tiny tracking pixels
                if image_url.startswith("http") and len(image_url) < 500:
                    break
                image_url = ""

        description = ""
        for pat in _OG_DESC_PATS:
            m = pat.search(raw)
            if m:
                description = _strip_html(m.group(1).replace("&amp;", "&")).strip()
                if description:
                    break

        return {"image_url": image_url, "og_description": description}

    except Exception:
        return {}


# ---------------------------------------------------------------------------
# RSS feed fetcher
# ---------------------------------------------------------------------------

def _fetch_feed(source_name: str, url: str, max_items: int = 5) -> list[dict]:
    """Synchronous fetch of a single RSS feed. Returns empty list on any error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/2.0"})
        with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)

        _MEDIA_NS = "http://search.yahoo.com/mrss/"
        items = root.findall(".//item")[:max_items]
        results = []
        for item in items:
            title_el = item.find("title")
            desc_el  = item.find("description")
            link_el  = item.find("link")

            title       = _strip_html(title_el.text if title_el is not None else "")
            description = _strip_html(desc_el.text  if desc_el  is not None else "")
            link        = (link_el.text or "").strip() if link_el is not None else ""

            # Try to extract hero image embedded in the RSS item itself
            image_url = ""
            # 1. media:content (Yahoo Media RSS namespace)
            for tag in (f"{{{_MEDIA_NS}}}content", "media:content"):
                el = item.find(tag)
                if el is not None:
                    candidate = el.get("url", "")
                    if candidate.startswith("http"):
                        image_url = candidate
                        break
            # 2. enclosure (podcast/image attachments)
            if not image_url:
                enc = item.find("enclosure")
                if enc is not None and "image" in enc.get("type", ""):
                    image_url = enc.get("url", "")
            # 3. <img> inside description HTML
            if not image_url and desc_el is not None and desc_el.text:
                m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_el.text, re.I)
                if m:
                    candidate = m.group(1)
                    if candidate.startswith("http"):
                        image_url = candidate

            if title:
                results.append({
                    "source":    source_name,
                    "title":     title,
                    "summary":   description[:200],
                    "link":      link,
                    "image_url": image_url,
                })
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# OG enrichment — fills in missing images in parallel
# ---------------------------------------------------------------------------

def _enrich_with_og(articles: list[dict], max_workers: int = 8) -> list[dict]:
    """
    For articles that don't already have an image_url, fetch OG meta in parallel.
    Modifies articles in-place and returns the list.
    """
    to_enrich = [
        i for i, a in enumerate(articles)
        if not a.get("image_url") and a.get("link")
    ]
    if not to_enrich:
        return articles

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_fetch_og_meta, articles[i]["link"]): i
            for i in to_enrich
        }
        for future in as_completed(futures, timeout=12):
            idx = futures[future]
            try:
                meta = future.result()
                if meta.get("image_url"):
                    articles[idx]["image_url"] = meta["image_url"]
                # Use OG description if it's longer / better than RSS truncation
                if meta.get("og_description"):
                    og = meta["og_description"][:300]
                    if len(og) > len(articles[idx].get("summary", "")):
                        articles[idx]["summary"] = og
            except Exception:
                pass

    return articles


# ---------------------------------------------------------------------------
# Parallel feed runner
# ---------------------------------------------------------------------------

def _fetch_feeds_parallel(
    feeds: list[tuple[str, str]],
    max_total: int,
    max_workers: int = 4,
) -> list[dict]:
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


# ---------------------------------------------------------------------------
# LLM formatter
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main entry point — with 30-minute server-side cache
# ---------------------------------------------------------------------------

def fetch_briefing_context(force_refresh: bool = False) -> dict:
    """
    Fetch world + finance news, enrich with OG images, cache 30 minutes.

    Cold start: ~15-20 s (RSS fetch + OG enrichment for ~24 articles in parallel)
    Warm (cached): < 1 ms

    Returns:
        {
            "world":           list[dict],   # each: {source, title, summary, link, image_url}
            "finance":         list[dict],
            "world_text":      str,          # LLM-formatted plaintext
            "finance_text":    str,
            "total_articles":  int,
            "sources_hit":     list[str],
            "fetch_error":     str,
            "enriched":        bool,         # True = images fetched this run
            "cached":          bool,         # True = served from cache
        }
    """
    global _CACHE

    # Serve from cache if fresh
    if not force_refresh and _CACHE["data"] is not None and time.time() < _CACHE["expires"]:
        cached = dict(_CACHE["data"])
        cached["cached"] = True
        return cached

    world: list[dict]   = []
    finance: list[dict] = []
    fetch_error = ""

    try:
        with ThreadPoolExecutor(max_workers=2) as outer:
            world_fut   = outer.submit(fetch_world_news)
            finance_fut = outer.submit(fetch_finance_news)
            world   = world_fut.result()
            finance = finance_fut.result()
    except Exception as exc:
        fetch_error = str(exc)

    # OG enrichment — world and finance in parallel
    if world or finance:
        with ThreadPoolExecutor(max_workers=2) as enrich_pool:
            wf = enrich_pool.submit(_enrich_with_og, world)
            ff = enrich_pool.submit(_enrich_with_og, finance)
            world   = wf.result()
            finance = ff.result()

    sources_hit = list({a["source"] for a in world + finance})
    total = len(world) + len(finance)

    if total == 0 and not fetch_error:
        fetch_error = "All RSS feeds returned empty results."

    result = {
        "world":          world,
        "finance":        finance,
        "world_text":     format_for_llm(world),
        "finance_text":   format_for_llm(finance),
        "total_articles": total,
        "sources_hit":    sources_hit,
        "fetch_error":    fetch_error,
        "enriched":       True,
        "cached":         False,
    }

    _CACHE["data"]    = result
    _CACHE["expires"] = time.time() + _CACHE_TTL

    return result
