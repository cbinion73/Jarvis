"""
JARVIS MyChart Sync — Playwright-based scraper with persistent Chromium profile.

First run:  launches a visible browser window → user logs in → cookies saved.
Later runs: headless, reuses saved session automatically.

Progress is streamed via _SYNC_STATE so the API can poll it.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

try:
    from .health_db import (
        upsert_mychart_page,
        replace_test_results,
        replace_medications,
        replace_conditions,
        replace_visits,
        replace_treatment_goals,
        log_sync,
    )
except ImportError:
    from health_db import (
        upsert_mychart_page,
        replace_test_results,
        replace_medications,
        replace_conditions,
        replace_visits,
        replace_treatment_goals,
        log_sync,
    )

log = logging.getLogger(__name__)

_PROFILE_DIR = Path.home() / ".jarvis" / "chrome_profile" / "mychart"
_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

_MYCHART_BASE = "https://mychart.stelizabeth.com/MyChart"
_LOGIN_URL    = f"{_MYCHART_BASE}/Authentication/Login"
_HOME_URL     = f"{_MYCHART_BASE}/Home"

# ---------------------------------------------------------------------------
# Live sync state (polled by /api/health/mychart/sync-status)
# ---------------------------------------------------------------------------
_SYNC_STATE: dict[str, Any] = {
    "running":   False,
    "step":      "",
    "progress":  0,       # 0-100
    "pages_done": [],
    "error":     None,
    "last_sync": None,
    "needs_login": False,
}


def get_sync_state() -> dict:
    return dict(_SYNC_STATE)


def _update(step: str, progress: int, **kw) -> None:
    _SYNC_STATE["step"]     = step
    _SYNC_STATE["progress"] = progress
    _SYNC_STATE.update(kw)
    log.info("[mychart_sync] %s (%d%%)", step, progress)


# ---------------------------------------------------------------------------
# Page extraction helpers
# ---------------------------------------------------------------------------

def _strip_text(html: str) -> str:
    """Very light HTML → text (no BeautifulSoup dependency needed)."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s{2,}", "\n", text)
    return text.strip()


async def _page_text(page: Page) -> str:
    return await page.evaluate("() => document.body.innerText")


def _is_login_page(url: str) -> bool:
    return "Login" in url or "Authentication" in url or "login" in url


# ---------------------------------------------------------------------------
# Parsers — turn raw text into structured rows
# ---------------------------------------------------------------------------

def _parse_test_results(text: str) -> list[dict]:
    results = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    date_pattern = re.compile(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}"
    )
    i = 0
    while i < len(lines):
        line = lines[i]
        # Skip nav/header noise
        if line.lower() in ("lab", "imaging", "individual results",
                             "load more results", "test results"):
            i += 1
            continue
        # Match a test name line followed by optional "Abnormal", then a date line
        date_match = None
        status = None
        provider = None
        if i + 1 < len(lines) and lines[i + 1] == "Abnormal":
            status = "Abnormal"
            look_ahead = i + 2
        else:
            look_ahead = i + 1
        if look_ahead < len(lines) and date_pattern.search(lines[look_ahead]):
            date_str = date_pattern.search(lines[look_ahead]).group(0)
            # Provider is usually 2 lines after the date line
            prov_idx = look_ahead + 1
            provider = lines[prov_idx].strip() if prov_idx < len(lines) else None
            results.append({
                "test_name":   line,
                "result_date": date_str,
                "status":      status or "Normal",
                "provider":    provider,
                "facility":    "St. Elizabeth Healthcare",
                "raw_text":    line,
            })
            i = prov_idx + 1
            continue
        i += 1
    return results


def _parse_medications(text: str) -> list[dict]:
    meds = []
    blocks = re.split(r"\n(?=[A-Z][a-z])", text)
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        name_line = lines[0]
        if len(name_line) < 4 or name_line.lower().startswith(("current", "medication",
                                                                 "st. elizabeth")):
            continue
        med: dict[str, Any] = {"name": name_line, "raw_text": block[:300]}
        # Generic / common name
        for l in lines[1:4]:
            if "Commonly known as:" in l:
                med["generic_name"] = l.split(":", 1)[-1].strip()
            elif "Generic name:" in l:
                med["generic_name"] = l.split(":", 1)[-1].strip()
        # Dosage — "Take X ..." or "Apply ..." or "Inject ..."
        for l in lines:
            if re.match(r"(Take|Apply|Inject|Use|Follow)", l, re.I):
                med["dosage"] = l[:200]
                break
        # Prescribed date
        m = re.search(r"Prescribed\s+(\w+ \d+,? \d{4})", block)
        if m:
            med["prescribed_date"] = m.group(1)
        # Prescriber
        m = re.search(r"Approved by\s+(.+)", block)
        if m:
            med["prescriber"] = m.group(1).strip()
        # Pharmacy
        m = re.search(r"(WALGREENS|EXPRESS SCRIPTS|CVS|KROGER)[^\n]+", block, re.I)
        if m:
            med["pharmacy"] = m.group(0)[:100]
        # Quantity / day supply
        m = re.search(r"Quantity\s+([^\n]+)", block)
        if m:
            med["quantity"] = m.group(1).strip()
        m = re.search(r"Day supply\s+(\d+)", block)
        if m:
            med["day_supply"] = int(m.group(1))
        meds.append(med)
    return meds


def _parse_conditions(text: str) -> list[dict]:
    conditions = []
    # Health Summary page: "Condition Summaries\nDiabetes\nHypertension\n..."
    in_conditions = False
    in_issues = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "Condition Summaries" in line:
            in_conditions = True
            continue
        if in_conditions:
            if line in ("Health Goal", "Treatment Goals", "Medications",
                        "Test Results", "Current Health Issues"):
                in_conditions = False
                if "Current Health Issues" in line:
                    in_issues = True
                continue
            if len(line) > 2:
                conditions.append({
                    "condition_name": line,
                    "category": "primary",
                    "status": "active",
                    "raw_text": line,
                })
        if "Current Health Issues" in line:
            in_issues = True
            in_conditions = False
            continue
        if in_issues:
            if line in ("Immunizations", "Allergies", "Recommended Actions",
                        "Quick Links", "Go to Health Issues"):
                in_issues = False
                continue
            if len(line) > 2 and not line.startswith("Go to"):
                conditions.append({
                    "condition_name": line,
                    "category": "health_issue",
                    "status": "active",
                    "raw_text": line,
                })
    return conditions


def _parse_visits(text: str) -> list[dict]:
    visits = []
    date_pattern = re.compile(
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2}\s+\d{4}"
    )
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    upcoming = False
    past = False
    i = 0
    while i < len(lines):
        l = lines[i]
        if "Upcoming" in l or "Future" in l:
            upcoming = True
            past = False
            i += 1
            continue
        if "Past visits" in l:
            upcoming = False
            past = True
            i += 1
            continue
        if date_pattern.match(l):
            visit: dict[str, Any] = {
                "visit_date": l,
                "is_upcoming": upcoming,
            }
            # next non-date lines are month/day/year (duped), then visit type, then provider
            j = i + 1
            while j < len(lines) and date_pattern.search(lines[j]):
                j += 1
            if j < len(lines):
                visit["visit_type"] = lines[j]
                j += 1
            if j < len(lines):
                visit["provider"] = lines[j]
                j += 1
            if j < len(lines):
                visit["facility"] = lines[j]
                j += 1
            visits.append(visit)
            i = j
            continue
        i += 1
    return visits


def _parse_treatment_goals(text: str) -> list[dict]:
    goals = []
    pattern = re.compile(
        r"(Blood Pressure|BMI|HEMOGLOBIN A1C|[A-Z][^\.]+?) below ([^\n]+)\n"
        r"Most recent value:([^\n]+)\n"
        r"Updated on ([^\n]+)\n"
        r"(Not On Track|On Track)"
    )
    for m in pattern.finditer(text):
        goals.append({
            "goal_name":     m.group(1).strip(),
            "target":        f"below {m.group(2).strip()}",
            "current_value": m.group(3).strip(),
            "last_updated":  m.group(4).strip(),
            "on_track":      m.group(5).strip() == "On Track",
        })
    return goals


# ---------------------------------------------------------------------------
# Scraping tasks
# ---------------------------------------------------------------------------

_PAGES = [
    ("test_results",  f"{_MYCHART_BASE}/app/test-results",        "test_results"),
    ("health_summary",f"{_MYCHART_BASE}/app/health-summary",      "conditions"),
    ("medications",   f"{_MYCHART_BASE}/Clinical/Medications",     "medications"),
    ("visits",        f"{_MYCHART_BASE}/Visits",                   "visits"),
]


async def _scrape_page(ctx: BrowserContext, name: str, url: str,
                       page_type: str) -> str | None:
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        if _is_login_page(page.url):
            log.warning("Redirected to login while scraping %s", name)
            return None
        text = await _page_text(page)
        return text
    except Exception as e:
        log.error("Error scraping %s: %s", name, e)
        return None
    finally:
        await page.close()


# ---------------------------------------------------------------------------
# Detail scraper — navigates into individual test result pages
# ---------------------------------------------------------------------------

async def _scrape_test_result_detail(ctx: BrowserContext, url: str) -> dict:
    """
    Navigate to an individual MyChart test result page and extract structured data.
    Uses DOM-first extraction via JS, falls back to text parsing.
    """
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=20_000)
        if _is_login_page(page.url):
            return {}

        text = await _page_text(page)
        result: dict = {"raw_text": text[:3000], "url": url}

        # ── DOM-first extraction ────────────────────────────────────────────
        # MyChart renders lab components in tables or definition lists.
        # This JS walks the DOM to pull out structured component data.
        dom_components = await page.evaluate("""
        () => {
            const comps = [];
            // Strategy 1: table rows with component/value/range/flag columns
            const rows = document.querySelectorAll('tr, [role="row"]');
            rows.forEach(row => {
                const cells = Array.from(row.querySelectorAll('td, [role="cell"], th, [role="columnheader"]'))
                    .map(c => c.innerText.trim()).filter(Boolean);
                if (cells.length >= 2) {
                    // Heuristic: first cell = name, second = value, third = range, fourth = flag
                    const name = cells[0];
                    const val  = cells[1];
                    // Skip pure header rows
                    if (['Component','Test','Result','Your Value','Value'].includes(name)) return;
                    if (name.length > 100 || name.length < 2) return;
                    // Value should look numeric or be a recognisable result
                    if (!/^[0-9.<>]/.test(val) && !['Negative','Positive','Detected','Not Detected','Normal','Abnormal','Reactive','Non-Reactive'].includes(val)) return;
                    const comp = { name, value: val };
                    if (cells[2]) comp.reference_range = cells[2];
                    if (cells[3]) comp.flag = cells[3];
                    comps.push(comp);
                }
            });
            if (comps.length > 0) return comps;

            // Strategy 2: definition list or label/value pairs
            const labels = document.querySelectorAll('.result-label, .component-name, [class*="label"], dt');
            labels.forEach(lbl => {
                const name = lbl.innerText.trim();
                if (!name || name.length > 80) return;
                const sib = lbl.nextElementSibling || lbl.parentElement?.querySelector('.result-value, [class*="value"], dd');
                if (sib) {
                    comps.push({ name, value: sib.innerText.trim() });
                }
            });
            return comps;
        }
        """)

        if dom_components:
            result["components"] = json.dumps(dom_components)
            # Primary value from first component
            first = dom_components[0]
            result["value"]           = first.get("value", "")
            result["unit"]            = first.get("unit", "")
            result["reference_range"] = first.get("reference_range", "")
            result["flag"]            = first.get("flag", "")
            log.debug("DOM extraction: %d components from %s", len(dom_components), url)
            return result

        # ── Text fallback ───────────────────────────────────────────────────
        # Parse innerText when DOM strategies return nothing
        components = []
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        _HDR = {"Component", "Your Value", "Standard Range", "Flag",
                "Reference Range", "Result", "Test", "Value"}
        range_pat = re.compile(r'[\d.]+\s*[-–]\s*[\d.]+|[<>]\s*[\d.]+')
        flag_words = {"High", "Low", "Critical High", "Critical Low",
                      "Abnormal", "Normal", "H", "L", "Positive", "Negative",
                      "Detected", "Not Detected"}
        i = 0
        while i < len(lines):
            line = lines[i]
            if line in _HDR or len(line) > 80 or len(line) < 2:
                i += 1
                continue
            # Next line looks numeric/result-like?
            if i + 1 < len(lines) and re.match(r'^[\d.<>]', lines[i + 1]):
                comp: dict = {"name": line, "value": lines[i + 1]}
                if i + 2 < len(lines) and range_pat.search(lines[i + 2]):
                    comp["reference_range"] = lines[i + 2]
                    if i + 3 < len(lines) and lines[i + 3] in flag_words:
                        comp["flag"] = lines[i + 3]
                        i += 4
                    else:
                        i += 3
                elif i + 2 < len(lines) and lines[i + 2] in flag_words:
                    comp["flag"] = lines[i + 2]
                    i += 3
                else:
                    i += 2
                components.append(comp)
                continue
            i += 1

        if components:
            result["components"]      = json.dumps(components)
            result["value"]           = components[0].get("value", "")
            result["unit"]            = components[0].get("unit", "")
            result["reference_range"] = components[0].get("reference_range", "")
            result["flag"]            = components[0].get("flag", "")

        return result

    except Exception as e:
        log.error("Error scraping test detail %s: %s", url, e)
        return {}
    finally:
        await page.close()


async def _scrape_test_results_with_details(ctx: BrowserContext) -> str | None:
    """
    Scrape test results list, then navigate into each result for actual values.
    Returns the index page text for raw storage; structured results are written
    directly to the DB via replace_test_results().
    """
    page = await ctx.new_page()
    all_results = []

    try:
        await page.goto(f"{_MYCHART_BASE}/app/test-results",
                        wait_until="networkidle", timeout=30_000)
        if _is_login_page(page.url):
            await page.close()
            return None

        # Get the index page text for raw storage
        index_text = await _page_text(page)

        # Extract all individual test result links from the DOM
        detail_links = await page.evaluate("""
            () => {
                const links = [];
                const selectors = [
                    'a[href*="test-results"]',
                    'a[href*="TestResults"]',
                    '[data-testid*="result"] a',
                    '.result-row a',
                    'a[href*="OrderID"]',
                    'a[href*="orderId"]',
                ];
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        const href = el.href;
                        if (href && !links.includes(href) &&
                            href !== window.location.href &&
                            !href.includes('login') && !href.includes('Login')) {
                            links.push(href);
                        }
                    });
                }
                // Fallback: scan all anchors for result/order patterns
                if (links.length === 0) {
                    document.querySelectorAll('a[href]').forEach(el => {
                        const href = el.href;
                        if (href && href.includes('MyChart') &&
                            (href.includes('result') || href.includes('Result') ||
                             href.includes('order') || href.includes('Order')) &&
                            !href.includes('login') && !links.includes(href)) {
                            links.push(href);
                        }
                    });
                }
                return links.slice(0, 50);
            }
        """)

        await page.close()

        log.info("Found %d individual test result links", len(detail_links))

        if not detail_links:
            # Fall back to text-only parsing
            return index_text

        # Scrape each detail page
        for url in detail_links:
            detail = await _scrape_test_result_detail(ctx, url)
            if detail:
                all_results.append(detail)

        # Store detailed results
        if all_results:
            try:
                from .health_db import replace_test_results as _replace
            except ImportError:
                from health_db import replace_test_results as _replace

            # UI text to skip when looking for the test name
            _UI_NOISE = {
                "test results", "individual results", "lab results", "results",
                "back", "print", "share", "mychart", "menu", "home",
                "loading", "please wait", "close", "details",
            }

            structured = []
            for r in all_results:
                raw = r.get("raw_text", "")
                url_str = r.get("url", "")

                # Extract order ID from URL (?orderId=xxx or /xxx at end)
                order_id = None
                oid_m = re.search(r'[?&/](?:orderId|order_id|id)[=:/](\w+)', url_str, re.I)
                if oid_m:
                    order_id = oid_m.group(1)

                # Test name: first non-empty, non-noise line from raw text
                lines = [l.strip() for l in raw.splitlines() if l.strip()]
                test_name = None
                for ln in lines[:10]:
                    if ln.lower() not in _UI_NOISE and len(ln) > 3 and len(ln) < 120:
                        # Skip if it looks like a date or pure number
                        if not re.match(r'^[\d/\-]+$', ln) and not re.match(
                                r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', ln):
                            test_name = ln
                            break
                if not test_name:
                    test_name = url_str.split("/")[-1].split("?")[0].replace("-", " ").title() or "Unknown"

                # Result date — prefer the most specific match in raw text
                date_match = re.search(
                    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
                    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
                    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
                    r"\s+\d{1,2},?\s+\d{4}",
                    raw,
                )

                # Provider — look for "MD", "DO", "APRN", "NP", "PA" patterns
                provider = None
                prov_m = re.search(
                    r'([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+,? (?:MD|DO|APRN|NP|PA|RN))',
                    raw,
                )
                if prov_m:
                    provider = prov_m.group(1)

                # Determine flag/status
                flag = r.get("flag") or ""
                status = "Abnormal" if flag.lower() in ("high", "low", "h", "l",
                    "critical high", "critical low", "abnormal") else "Normal"

                structured.append({
                    "test_name":       test_name,
                    "result_date":     date_match.group(0) if date_match else None,
                    "status":          status,
                    "provider":        provider,
                    "facility":        "St. Elizabeth Healthcare",
                    "value":           r.get("value"),
                    "unit":            r.get("unit"),
                    "reference_range": r.get("reference_range"),
                    "flag":            flag or None,
                    "components":      r.get("components"),
                    "order_id":        order_id,
                    "raw_text":        raw[:800],
                })

            if structured:
                await _replace(structured)

        return index_text

    except Exception as e:
        log.error("Error in _scrape_test_results_with_details: %s", e)
        try:
            await page.close()
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Main sync entry point
# ---------------------------------------------------------------------------

async def run_sync(headless: bool = False) -> dict:
    """
    Full MyChart sync.  Call this from a FastAPI BackgroundTask.

    If the browser detects the login page, sets needs_login=True and stops.
    The caller can then re-invoke with headless=False so the user can log in.
    """
    _SYNC_STATE.update(
        running=True, step="Starting…", progress=0,
        pages_done=[], error=None, needs_login=False,
    )

    try:
        async with async_playwright() as pw:
            _update("Launching browser…", 5)
            ctx = await pw.chromium.launch_persistent_context(
                str(_PROFILE_DIR),
                headless=headless,
                args=["--no-sandbox"],
                viewport={"width": 1280, "height": 900},
            )

            # ── Quick login check ──────────────────────────────────────────
            _update("Checking login status…", 10)
            probe = await ctx.new_page()
            await probe.goto(_HOME_URL, wait_until="domcontentloaded", timeout=20_000)
            if _is_login_page(probe.url):
                if headless:
                    await ctx.close()
                    _SYNC_STATE.update(
                        running=False, step="Login required",
                        needs_login=True, progress=0,
                    )
                    return {"ok": False, "needs_login": True}
                # Visible mode — wait for user to log in
                _update("Waiting for you to log in…", 15, needs_login=True)
                for _ in range(120):          # wait up to 4 min
                    await asyncio.sleep(2)
                    if not _is_login_page(probe.url):
                        break
                else:
                    await ctx.close()
                    _SYNC_STATE.update(
                        running=False,
                        step="Login timed out — please try again",
                        error="timeout",
                    )
                    return {"ok": False, "error": "login_timeout"}
                _update("Logged in — starting sync…", 20, needs_login=False)
            await probe.close()

            # ── Scrape each page ──────────────────────────────────────────
            step_size = 60 // len(_PAGES)
            for idx, (name, url, ptype) in enumerate(_PAGES):
                pct = 20 + idx * step_size
                _update(f"Syncing {name.replace('_', ' ')}…", pct)

                if ptype == "test_results":
                    # Navigate into each individual result to capture actual values
                    text = await _scrape_test_results_with_details(ctx)
                else:
                    text = await _scrape_page(ctx, name, url, ptype)

                if text is None:
                    # Session expired mid-way
                    await ctx.close()
                    _SYNC_STATE.update(
                        running=False, step="Session expired",
                        needs_login=True, error="session_expired",
                    )
                    return {"ok": False, "needs_login": True}

                # Store raw page in DB
                await upsert_mychart_page(name, ptype, text)

                # Parse into structured tables
                if ptype == "test_results":
                    # Already handled by _scrape_test_results_with_details
                    pass
                elif ptype == "medications":
                    rows = _parse_medications(text)
                    if rows:
                        await replace_medications(rows)
                elif ptype == "conditions":
                    conds = _parse_conditions(text)
                    if conds:
                        await replace_conditions(conds)
                    goals = _parse_treatment_goals(text)
                    if goals:
                        await replace_treatment_goals(goals)
                    visits_data = []   # visits come from their own page
                if ptype == "visits":
                    visits_data = _parse_visits(text)
                    if visits_data:
                        await replace_visits(visits_data)

                _SYNC_STATE["pages_done"].append(name)

            await ctx.close()

        # ── Done ──────────────────────────────────────────────────────────
        now = datetime.utcnow().isoformat()
        await log_sync("mychart", "success",
                       f"Synced {len(_SYNC_STATE['pages_done'])} pages")
        _SYNC_STATE.update(
            running=False,
            step="Sync complete",
            progress=100,
            last_sync=now,
        )
        return {"ok": True, "pages": _SYNC_STATE["pages_done"]}

    except Exception as exc:
        log.exception("MyChart sync failed")
        await log_sync("mychart", "error", str(exc))
        _SYNC_STATE.update(
            running=False,
            step=f"Error: {exc}",
            progress=0,
            error=str(exc),
        )
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Apple Health ingest helper (called from service.py webhook)
# ---------------------------------------------------------------------------

async def ingest_apple_health(data: dict) -> dict:
    """Store an Apple Health payload (from Shortcuts) into the DB."""
    try:
        from .health_db import upsert_daily_metrics, log_sync
    except ImportError:
        from health_db import upsert_daily_metrics, log_sync

    await upsert_daily_metrics(data)
    await log_sync("apple_health", "success",
                   f"Ingested metrics for {data.get('date', 'today')}")
    return {"ok": True}
