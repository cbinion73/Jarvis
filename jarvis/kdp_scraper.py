"""
KDP scraper — uses Playwright to log into kdp.amazon.com and extract
bookshelf and sales data. Session cookies are persisted to avoid
re-login on every sync.
"""
from __future__ import annotations

import asyncio as _asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis.kdp_scraper")

# ---------------------------------------------------------------------------
# Module-level sync state + 2FA coordination
# ---------------------------------------------------------------------------

_sync_status: str = "idle"          # idle | running | needs_2fa | done | error
_2fa_future: "_asyncio.Future | None" = None
_broadcast_fn = None                 # set by service.py at startup


def set_broadcast(fn) -> None:
    """Called by service.py to wire up the WebSocket broadcast function."""
    global _broadcast_fn
    _broadcast_fn = fn


def _broadcast(payload: dict) -> None:
    """Fire-and-forget broadcast if wired."""
    try:
        if _broadcast_fn:
            _broadcast_fn(payload)
    except Exception:
        pass


def get_sync_status() -> str:
    return _sync_status


async def submit_2fa_code(code: str) -> None:
    """Called by the API endpoint when the user submits their OTP."""
    global _2fa_future
    if _2fa_future and not _2fa_future.done():
        _2fa_future.set_result(code.strip())

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KDP_BASE      = "https://kdp.amazon.com"
KDP_BOOKSHELF = "https://kdp.amazon.com/en_US/bookshelf"
KDP_REPORTS   = "https://kdp.amazon.com/en_US/reports"
COOKIES_PATH  = Path("data/kdp/session_cookies.json")
CREDS_PATH    = Path("data/settings/kdp_credentials.json")


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def load_credentials() -> dict | None:
    """Load {"email": ..., "password": ...} from CREDS_PATH. Return None if not found."""
    try:
        if not CREDS_PATH.exists():
            return None
        data = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
        if data.get("email") and data.get("password"):
            return data
        return None
    except Exception as exc:
        log.warning("KDP: failed to load credentials: %s", exc)
        return None


def save_credentials(email: str, password: str) -> None:
    """Save credentials to CREDS_PATH (create parent dirs). Never raise."""
    try:
        CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CREDS_PATH.write_text(
            json.dumps({"email": email, "password": password}, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("KDP: credentials saved to %s", CREDS_PATH)
    except Exception as exc:
        log.warning("KDP: failed to save credentials: %s", exc)


# ---------------------------------------------------------------------------
# Cookie persistence
# ---------------------------------------------------------------------------

async def save_cookies(context: Any) -> None:
    """Save browser context cookies to COOKIES_PATH as JSON."""
    try:
        COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        cookies = await context.cookies()
        COOKIES_PATH.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.debug("KDP: cookies saved (%d cookies)", len(cookies))
    except Exception as exc:
        log.warning("KDP: failed to save cookies: %s", exc)


async def load_cookies(context: Any) -> bool:
    """Load cookies from COOKIES_PATH into context. Return False if file missing."""
    try:
        if not COOKIES_PATH.exists():
            return False
        cookies = json.loads(COOKIES_PATH.read_text(encoding="utf-8"))
        if not cookies:
            return False
        await context.add_cookies(cookies)
        log.debug("KDP: loaded %d cookies from disk", len(cookies))
        return True
    except Exception as exc:
        log.warning("KDP: failed to load cookies: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login(page: Any, email: str, password: str) -> bool:
    """
    Navigate to KDP signin and complete the Amazon multi-step login flow.
    Returns True on success, False on failure.
    Handles 2FA: pauses and waits for user to supply OTP via WebSocket.
    """
    global _sync_status, _2fa_future
    try:
        await page.goto(
            "https://kdp.amazon.com/en_US/signin",
            wait_until="domcontentloaded",
            timeout=30_000,
        )

        # Already logged in?
        url = page.url
        if "kdp.amazon.com" in url and "signin" not in url and "amazon.com/ap" not in url:
            log.info("KDP: already logged in (URL: %s)", url)
            return True

        # Amazon login is multi-step: email page, then password page.
        # ── Step 1: Enter email ──────────────────────────────────────────
        try:
            email_field = page.locator("#ap_email")
            await email_field.wait_for(state="visible", timeout=10_000)
            await email_field.fill(email)

            # Click "Continue" button
            continue_btn = page.locator("#continue, [name='continue'], input[type='submit']")
            await continue_btn.first.click()
            await page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except Exception as exc:
            log.warning("KDP login: email step failed: %s", exc)
            return False

        # Detect 2FA / OTP page (after email step)
        url = page.url
        if "ap/mfa" in url or "ap/cvf" in url or "ap/challenge" in url:
            log.warning("KDP login: 2FA / OTP page detected after email step")
            _sync_status = "needs_2fa"
            loop = _asyncio.get_event_loop()
            _2fa_future = loop.create_future()
            _broadcast({"type": "kdp.2fa_required", "message": "Amazon needs a verification code to continue."})
            try:
                code = await _asyncio.wait_for(_asyncio.shield(_2fa_future), timeout=300)
            except _asyncio.TimeoutError:
                log.warning("KDP 2FA: timed out waiting for user code")
                return False

            # Enter OTP code
            try:
                for sel in ["#auth-mfa-otpcode", "#otp-field", "input[name='otpCode']", "input[type='text']"]:
                    try:
                        otp_field = page.locator(sel)
                        await otp_field.wait_for(state="visible", timeout=3_000)
                        await otp_field.fill(code)
                        break
                    except Exception:
                        continue
                submit_btn = page.locator("input[type='submit'], button[type='submit'], #auth-signin-button")
                await submit_btn.first.click()
                await page.wait_for_load_state("domcontentloaded", timeout=20_000)
            except Exception as exc:
                log.warning("KDP 2FA: could not enter code: %s", exc)
                return False

            # Re-check URL after 2FA submit
            url = page.url
            if "ap/mfa" in url or "ap/cvf" in url or "ap/challenge" in url:
                log.warning("KDP login: still on 2FA page after code entry")
                return False

        # ── Step 2: Enter password ───────────────────────────────────────
        try:
            pw_field = page.locator("#ap_password")
            await pw_field.wait_for(state="visible", timeout=10_000)
            await pw_field.fill(password)

            signin_btn = page.locator("#signInSubmit, [name='signIn'], input[type='submit']")
            await signin_btn.first.click()
            await page.wait_for_load_state("domcontentloaded", timeout=20_000)
        except Exception as exc:
            log.warning("KDP login: password step failed: %s", exc)
            return False

        # Post-login: check for 2FA again (after password step)
        url = page.url
        if "ap/mfa" in url or "ap/cvf" in url or "ap/challenge" in url:
            log.warning("KDP login: 2FA required after password step")
            _sync_status = "needs_2fa"
            loop = _asyncio.get_event_loop()
            _2fa_future = loop.create_future()
            _broadcast({"type": "kdp.2fa_required", "message": "Amazon needs a verification code to continue."})
            try:
                code = await _asyncio.wait_for(_asyncio.shield(_2fa_future), timeout=300)
            except _asyncio.TimeoutError:
                log.warning("KDP 2FA: timed out waiting for user code")
                return False

            # Enter OTP code
            try:
                for sel in ["#auth-mfa-otpcode", "#otp-field", "input[name='otpCode']", "input[type='text']"]:
                    try:
                        otp_field = page.locator(sel)
                        await otp_field.wait_for(state="visible", timeout=3_000)
                        await otp_field.fill(code)
                        break
                    except Exception:
                        continue
                submit_btn = page.locator("input[type='submit'], button[type='submit'], #auth-signin-button")
                await submit_btn.first.click()
                await page.wait_for_load_state("domcontentloaded", timeout=20_000)
            except Exception as exc:
                log.warning("KDP 2FA: could not enter code: %s", exc)
                return False

            # Re-check URL after 2FA submit
            url = page.url
            if "ap/mfa" in url or "ap/cvf" in url or "ap/challenge" in url:
                log.warning("KDP login: still on 2FA page after code entry")
                return False

        # Check if we landed on KDP
        if "kdp.amazon.com" in url and "amazon.com/ap" not in url:
            log.info("KDP: login successful (URL: %s)", url)
            return True

        # May still be on Amazon or error page
        log.warning("KDP: login result unclear, URL=%s", url)
        # Try navigating to KDP bookshelf and see if it works
        await page.goto(KDP_BOOKSHELF, wait_until="domcontentloaded", timeout=20_000)
        final_url = page.url
        if "kdp.amazon.com" in final_url and "signin" not in final_url and "amazon.com/ap" not in final_url:
            log.info("KDP: login confirmed via bookshelf redirect (URL: %s)", final_url)
            return True

        log.warning("KDP: login failed — landed at %s", final_url)
        return False

    except Exception as exc:
        log.warning("KDP login: unhandled exception: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Scrape: Bookshelf
# ---------------------------------------------------------------------------

async def scrape_bookshelf(page: Any) -> list[dict]:
    """
    Navigate to KDP_BOOKSHELF and extract book rows.
    Returns list of dicts with: asin, title, status, marketplace,
    enrolled_in_kdp_select, last_updated.
    """
    books: list[dict] = []
    try:
        await page.goto(KDP_BOOKSHELF, wait_until="domcontentloaded", timeout=30_000)

        # Wait for the book table to appear — KDP renders a table or card list
        loaded = False
        for selector in [
            ".bookshelf-table",
            "table.title-list",
            "[data-type='kindle']",
            ".book-title-bar",
            "a[href*='/en_US/title-setup/kindle/']",
            "#container-summary",
        ]:
            try:
                await page.wait_for_selector(selector, timeout=15_000)
                loaded = True
                log.debug("KDP bookshelf: found selector %s", selector)
                break
            except Exception:
                continue

        if not loaded:
            log.warning("KDP bookshelf: no book table selector matched")
            return []

        # Extract book rows — try multiple KDP layout patterns
        books = await page.evaluate("""
() => {
    const results = [];

    // Pattern 1: table rows with .data-rows
    const rows = document.querySelectorAll('tr.title-row, tr[id^="id-"], [class*="book-row"]');
    rows.forEach(row => {
        try {
            const titleEl  = row.querySelector('[class*="book-title"], .title a, a[href*="title-setup"]');
            const statusEl = row.querySelector('[class*="status"], .status-badge, [class*="badge"]');
            const asinEl   = row.querySelector('[data-asin], a[href*="/title-setup/kindle/"]');

            let asin = '';
            if (asinEl) {
                const href = asinEl.getAttribute('href') || '';
                const m = href.match(/kindle\\/([A-Z0-9]{10})/);
                if (m) asin = m[1];
                if (!asin) asin = asinEl.getAttribute('data-asin') || '';
            }

            const title  = titleEl ? titleEl.textContent.trim() : '';
            const status = statusEl ? statusEl.textContent.trim() : '';

            if (title || asin) {
                const selectEl = row.querySelector('[class*="select"], [class*="kdp-select"]');
                const dateEl   = row.querySelector('[class*="date"], [class*="updated"]');
                results.push({
                    asin:                  asin,
                    title:                 title,
                    status:                status,
                    marketplace:           'com',
                    enrolled_in_kdp_select: selectEl ? selectEl.textContent.includes('Enrolled') : false,
                    last_updated:          dateEl ? dateEl.textContent.trim() : '',
                });
            }
        } catch(e) {}
    });

    // Pattern 2: anchor-based fallback (newer KDP UI)
    if (results.length === 0) {
        const links = document.querySelectorAll('a[href*="/en_US/title-setup/kindle/"]');
        links.forEach(link => {
            try {
                const href = link.getAttribute('href') || '';
                const m = href.match(/kindle\\/([A-Z0-9]{10})/);
                const asin = m ? m[1] : '';
                const title = link.textContent.trim();
                if (title || asin) {
                    results.push({
                        asin:                   asin,
                        title:                  title,
                        status:                 'Unknown',
                        marketplace:            'com',
                        enrolled_in_kdp_select: false,
                        last_updated:           '',
                    });
                }
            } catch(e) {}
        });
    }

    return results;
}
""")

        log.info("KDP bookshelf: scraped %d books", len(books))
        return books

    except Exception as exc:
        log.warning("KDP scrape_bookshelf failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Scrape: Sales Dashboard
# ---------------------------------------------------------------------------

async def scrape_sales_dashboard(page: Any) -> dict:
    """
    Navigate to KDP_REPORTS and extract top-level sales data.
    Returns dict with period, units_sold, kenp_pages_read, royalties_usd, last_updated.
    """
    try:
        await page.goto(KDP_REPORTS, wait_until="domcontentloaded", timeout=30_000)

        # Wait for report content
        loaded = False
        for selector in [
            "[class*='report']",
            "[class*='units-sold']",
            "[class*='royalt']",
            "#report-content",
            ".kdp-reports",
            "table",
        ]:
            try:
                await page.wait_for_selector(selector, timeout=15_000)
                loaded = True
                log.debug("KDP reports: found selector %s", selector)
                break
            except Exception:
                continue

        if not loaded:
            log.warning("KDP reports: no report selector matched")
            return {"error": "scrape_failed"}

        data = await page.evaluate("""
() => {
    function extractNum(text) {
        if (!text) return 0;
        const m = text.replace(/,/g, '').match(/[\\d.]+/);
        return m ? parseFloat(m[0]) : 0;
    }

    const result = {
        period:           '',
        units_sold:       0,
        kenp_pages_read:  0,
        royalties_usd:    0.0,
    };

    // Look for units sold figures
    const allText = document.body.innerText || '';

    // Period
    const dateRange = document.querySelector('[class*="date-range"], [class*="period"], [class*="reporting-period"]');
    if (dateRange) result.period = dateRange.textContent.trim();

    // Try to find units sold in summary tables
    const cells = document.querySelectorAll('td, th, [class*="metric"], [class*="summary-value"]');
    cells.forEach(cell => {
        const label = (cell.previousElementSibling || cell.parentElement || {}).textContent || '';
        const text = cell.textContent.trim();
        if (/units sold/i.test(label) || /units sold/i.test(cell.getAttribute('data-label') || '')) {
            result.units_sold = extractNum(text);
        }
        if (/kenp|page read/i.test(label) || /kenp|page read/i.test(cell.getAttribute('data-label') || '')) {
            result.kenp_pages_read = extractNum(text);
        }
        if (/royalt/i.test(label) || /royalt/i.test(cell.getAttribute('data-label') || '')) {
            if (!result.royalties_usd) result.royalties_usd = extractNum(text);
        }
    });

    return result;
}
""")

        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        log.info("KDP sales dashboard scraped: units=%s royalties=%s", data.get("units_sold"), data.get("royalties_usd"))
        return data

    except Exception as exc:
        log.warning("KDP scrape_sales_dashboard failed: %s", exc)
        return {"error": "scrape_failed"}


# ---------------------------------------------------------------------------
# Scrape: Book Detail
# ---------------------------------------------------------------------------

async def scrape_book_detail(page: Any, asin: str) -> dict:
    """
    Navigate to the KDP book detail page and extract pricing, categories, keywords,
    description snippet.
    Returns dict. On failure returns {"asin": asin, "error": "detail_scrape_failed"}.
    """
    url = f"{KDP_BASE}/en_US/title-setup/kindle/{asin}/details"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        # Wait for something to load
        loaded = False
        for selector in [
            "[class*='detail']",
            "[class*='pricing']",
            "form",
            "#tab-content-PRICING",
            "[class*='category']",
        ]:
            try:
                await page.wait_for_selector(selector, timeout=10_000)
                loaded = True
                break
            except Exception:
                continue

        if not loaded:
            log.warning("KDP detail %s: no detail selector matched", asin)
            return {"asin": asin, "error": "detail_scrape_failed"}

        detail = await page.evaluate(f"""
() => {{
    const result = {{
        asin:        '{asin}',
        price_usd:   '',
        categories:  [],
        keywords:    [],
        description: '',
    }};

    // Price
    const priceEl = document.querySelector('[class*="price"] input, #pricing-us-price, [name*="price"]');
    if (priceEl) result.price_usd = priceEl.value || priceEl.textContent.trim();

    // Categories (up to 2)
    const catEls = document.querySelectorAll('[class*="categor"] select option:checked, [class*="categor"] .selected, [class*="bisac"]');
    catEls.forEach(el => {{
        if (result.categories.length < 2) {{
            const text = el.textContent.trim();
            if (text) result.categories.push(text);
        }}
    }});

    // Keywords (up to 7)
    const kwEls = document.querySelectorAll('[name*="keyword"], [id*="keyword"], [class*="keyword"] input');
    kwEls.forEach(el => {{
        if (result.keywords.length < 7) {{
            const val = (el.value || el.textContent || '').trim();
            if (val) result.keywords.push(val);
        }}
    }});

    // Description snippet
    const descEl = document.querySelector('[class*="description"] textarea, #description, [name="description"]');
    if (descEl) {{
        const text = descEl.value || descEl.textContent || '';
        result.description = text.trim().slice(0, 300);
    }}

    return result;
}}
""")

        log.debug("KDP detail scraped for ASIN %s", asin)
        return detail

    except Exception as exc:
        log.warning("KDP scrape_book_detail(%s) failed: %s", asin, exc)
        return {"asin": asin, "error": "detail_scrape_failed"}


# ---------------------------------------------------------------------------
# Main entry point: run_full_sync
# ---------------------------------------------------------------------------

async def run_full_sync(email: str, password: str) -> dict:
    """
    Full KDP sync via Playwright:
    1. Load cookies → navigate → check login
    2. Login if needed
    3. Scrape bookshelf + sales dashboard
    4. Scrape detail for first 5 books
    5. Return result dict

    Returns {"ok": True, "books": [...], "sales": {...}, "synced_at": ISO}
         or {"ok": False, "error": "..."}
    """
    global _sync_status
    _sync_status = "running"

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("KDP: playwright not installed — run: pip install playwright")
        _sync_status = "error"
        _broadcast({"type": "kdp.sync_complete", "ok": False, "error": "playwright_not_installed"})
        return {"ok": False, "error": "playwright_not_installed"}

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            # ── Step 1: Try saved cookies ────────────────────────────────
            cookies_loaded = await load_cookies(context)
            logged_in = False

            if cookies_loaded:
                try:
                    await page.goto(KDP_BOOKSHELF, wait_until="domcontentloaded", timeout=20_000)
                    current_url = page.url
                    # Check if we're actually on KDP (not redirected to login)
                    if "kdp.amazon.com" in current_url and "signin" not in current_url and "amazon.com/ap" not in current_url:
                        logged_in = True
                        log.info("KDP: session restored from cookies")
                    else:
                        log.info("KDP: cookies expired, need to login")
                except Exception as exc:
                    log.warning("KDP: cookie navigation failed: %s", exc)

            # ── Step 2: Login if needed ──────────────────────────────────
            if not logged_in:
                success = await login(page, email, password)
                if not success:
                    await browser.close()
                    _sync_status = "error"
                    _broadcast({"type": "kdp.sync_complete", "ok": False, "error": "login_failed"})
                    return {"ok": False, "error": "login_failed"}
                logged_in = True
                await save_cookies(context)

            # ── Step 3: Scrape bookshelf ─────────────────────────────────
            books = await scrape_bookshelf(page)

            # ── Step 4: Scrape sales dashboard ───────────────────────────
            sales = await scrape_sales_dashboard(page)

            # ── Step 5: Scrape details for first 5 books ─────────────────
            detail_books: list[dict] = []
            for book in books[:5]:
                asin = book.get("asin", "")
                if asin:
                    detail = await scrape_book_detail(page, asin)
                    # Merge detail into book record
                    merged = {**book, **detail}
                    detail_books.append(merged)
                else:
                    detail_books.append(book)

            # For books 6+ just use the bookshelf data
            for book in books[5:]:
                detail_books.append(book)

            await browser.close()

            result = {
                "ok": True,
                "books": detail_books,
                "sales": sales,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
            _sync_status = "done"
            _broadcast({"type": "kdp.sync_complete", "ok": True})
            return result

    except Exception as exc:
        log.error("KDP run_full_sync failed: %s", exc, exc_info=True)
        _sync_status = "error"
        _broadcast({"type": "kdp.sync_complete", "ok": False, "error": str(exc)})
        return {"ok": False, "error": str(exc)}
