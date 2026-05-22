"""
book_launch.py — Book Launch Asset Generator
=============================================
Pulls book data from Ghostwritr (via the bridge) and uses LLMGateway to
generate a full suite of launch assets:

  - Social series     Twitter (10 posts) + LinkedIn (6 posts)
  - Press release     600–800 words, AP style
  - Email sequence    Pre-launch · Launch day · 1-week follow-up
  - Amazon copy       Description + subtitle options + KDP keywords
  - Extended          Goodreads update, podcast pitch, newsletter blurb,
                      ARC review request

Storage: ~/.jarvis/publishing/launches/<slug>/assets.json
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.book_launch")


def _msg(system: str, user: str) -> list:
    """Build a messages list for LLMGateway.complete()."""
    try:
        from .llm_gateway import LLMMessage
    except ImportError:
        from llm_gateway import LLMMessage
    return [LLMMessage("system", system), LLMMessage("user", user)]

LAUNCHES_DIR = Path.home() / ".jarvis" / "publishing" / "launches"


# ---------------------------------------------------------------------------
# BookBrief — normalised input to every LLM prompt
# ---------------------------------------------------------------------------

@dataclass
class BookBrief:
    slug: str
    title: str
    subtitle: str
    workflow_type: str          # NONFICTION | FICTION
    book_status: str            # DRAFT | PUBLISHED
    current_stage: str          # e.g. EDITING
    promise: str                # core promise text
    outline_summary: str        # first 2 000 chars of OUTLINE artifact
    chapter_titles: list[str]   = field(default_factory=list)
    total_word_count: int       = 0
    author_name: str            = "Chris Binion"
    genre: str                  = "Nonfiction"
    target_audience: str        = ""
    key_themes: list[str]       = field(default_factory=list)


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_assets(slug: str) -> dict | None:
    """Return stored launch assets for *slug*, or None if not yet generated."""
    path = LAUNCHES_DIR / slug / "assets.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not load assets for %s: %s", slug, exc)
        return None


def save_assets(slug: str, assets: dict) -> None:
    """Persist launch assets to disk."""
    dest = LAUNCHES_DIR / slug
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "assets.json").write_text(
        json.dumps(assets, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Bridge helpers — extract BookBrief from Ghostwritr
# ---------------------------------------------------------------------------

def get_book_brief(bridge: Any, slug: str) -> BookBrief:
    """
    Pull book data from Ghostwritr and return a normalised BookBrief.
    Falls back to empty/default values if any call fails.
    """
    title = subtitle = promise = outline_summary = ""
    chapter_titles: list[str] = []
    total_word_count = 0
    workflow_type = "NONFICTION"
    book_status = "DRAFT"
    current_stage = ""
    genre = "Nonfiction"
    target_audience = ""
    key_themes: list[str] = []
    author_name = "Chris Binion"

    # ── DB: book row + stages ────────────────────────────────────────────
    try:
        if hasattr(bridge, "_db") and bridge._db and bridge._db.is_available():
            book_data = bridge._db.get_book_with_stages(slug)
            if book_data:
                title         = book_data.get("titleWorking") or book_data.get("title") or slug
                subtitle      = book_data.get("subtitle") or ""
                workflow_type = book_data.get("workflowType") or "NONFICTION"
                book_status   = book_data.get("status") or "DRAFT"

                # metadataJson
                meta = book_data.get("metadataJson") or {}
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                author_name     = meta.get("authorName") or author_name
                genre           = meta.get("genre") or genre
                target_audience = meta.get("targetAudience") or ""
                key_themes      = meta.get("keyThemes") or []

                # Derive current stage from stages list
                stages = book_data.get("stages") or []
                for st in reversed(stages):
                    if st.get("status") in ("IN_PROGRESS", "COMPLETE"):
                        current_stage = st.get("stageKey") or ""
                        break
    except Exception as exc:
        logger.debug("DB book fetch failed for %s: %s", slug, exc)

    # ── HTTP client: promise + manuscript ───────────────────────────────
    try:
        if hasattr(bridge, "_client") and bridge._client and bridge._client.is_available():
            try:
                prom = bridge._client.get_promise(slug)
                promise = (prom or {}).get("text") or (prom or {}).get("promise") or ""
                if not promise and isinstance(prom, str):
                    promise = prom
            except Exception:
                pass

            try:
                ms = bridge._client.get_manuscript(slug)
                chapters = (ms or {}).get("chapters") or []
                chapter_titles = [c.get("title") or c.get("name") or "" for c in chapters if c.get("title") or c.get("name")]
                total_word_count = sum(c.get("wordCount") or 0 for c in chapters)
            except Exception:
                pass
    except Exception as exc:
        logger.debug("HTTP client failed for %s: %s", slug, exc)

    # ── Outline artifact summary ─────────────────────────────────────────
    try:
        if hasattr(bridge, "_db") and bridge._db and bridge._db.is_available():
            book_row = bridge._db.get_book_with_stages(slug)
            if book_row:
                book_id = book_row.get("id")
                if book_id:
                    artifacts = bridge._db._run_sync_query(
                        "SELECT \"contentJson\" FROM \"Artifact\" "
                        "WHERE \"bookId\" = %s AND type = 'OUTLINE' "
                        "ORDER BY \"createdAt\" DESC LIMIT 1",
                        (book_id,),
                    )
                    if artifacts:
                        cj = artifacts[0].get("contentJson") or {}
                        if isinstance(cj, str):
                            try:
                                cj = json.loads(cj)
                            except Exception:
                                pass
                        raw = cj.get("text") or cj.get("content") or str(cj)
                        outline_summary = raw[:2000]
    except Exception as exc:
        logger.debug("Outline artifact fetch failed for %s: %s", slug, exc)

    return BookBrief(
        slug            = slug,
        title           = title or slug,
        subtitle        = subtitle,
        workflow_type   = workflow_type,
        book_status     = book_status,
        current_stage   = current_stage,
        promise         = promise,
        outline_summary = outline_summary,
        chapter_titles  = chapter_titles,
        total_word_count= total_word_count,
        author_name     = author_name,
        genre           = genre,
        target_audience = target_audience,
        key_themes      = key_themes,
    )


# ---------------------------------------------------------------------------
# Trigger detection
# ---------------------------------------------------------------------------

def check_launch_trigger(bridge: Any, slug: str) -> str | None:
    """
    Returns 'pre_launch' if book is at EDITING stage with no assets yet,
    'post_publish' if book is PUBLISHED and stored assets have an older trigger,
    None otherwise.
    """
    existing = load_assets(slug)
    try:
        if hasattr(bridge, "_db") and bridge._db and bridge._db.is_available():
            book = bridge._db.get_book_with_stages(slug)
            if not book:
                return None
            status = book.get("status") or ""
            stages = book.get("stages") or []
            stage_keys = [s.get("stageKey") for s in stages if s.get("status") in ("IN_PROGRESS", "COMPLETE")]
            current = stage_keys[-1] if stage_keys else ""

            if status == "PUBLISHED" and (not existing or existing.get("trigger") != "post_publish"):
                return "post_publish"
            if current == "EDITING" and not existing:
                return "pre_launch"
    except Exception as exc:
        logger.debug("check_launch_trigger failed for %s: %s", slug, exc)
    return None


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Any:
    """Extract the first JSON object or array from *text*. Raises ValueError on failure."""
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first [ or { and try to parse from there
    for start_char, end_char in (("[", "]"), ("{", "}")):
        idx = text.find(start_char)
        if idx == -1:
            continue
        # Walk from end to find matching close
        depth = 0
        for i, ch in enumerate(text[idx:], start=idx):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[idx : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"No valid JSON found in response (first 200 chars): {text[:200]}")


# ---------------------------------------------------------------------------
# Asset generators — one per asset type
# ---------------------------------------------------------------------------

def _generate_twitter(brief: BookBrief, gateway: Any) -> list[dict]:
    chapters_str = ", ".join(brief.chapter_titles[:6]) if brief.chapter_titles else "various chapters"
    prompt = f"""Book: {brief.title}{(' — ' + brief.subtitle) if brief.subtitle else ''}
Author: {brief.author_name}
Genre: {brief.genre} | Audience: {brief.target_audience or 'general readers'}
Promise: {brief.promise[:800]}
Key themes: {', '.join(brief.key_themes[:6]) or 'leadership, influence, growth'}
Chapter highlights: {chapters_str}

Write exactly 10 Twitter/X posts (280 chars max each) for a book launch campaign.
Include one of each type (label each with the type):
TEASER, CORE_PROMISE, QUOTE, BEHIND_SCENES, SOCIAL_PROOF_HOOK, LAUNCH_DAY, CHAPTER_HOOK, BENEFIT, POST_LAUNCH, EVERGREEN

Return ONLY a JSON array: [{{"type":"TEASER","text":"..."}},...] — no other text."""

    resp = gateway.complete(
        messages=_msg(
            "You are a book launch social media strategist. Write punchy, authentic posts. Voice: direct, curious, human. No hashtag spam. No em-dashes.",
            prompt,
        ),
        task_type="draft",
        agent_id="book-launch",
        max_tokens=2048,
    )
    try:
        return _extract_json(resp.text)
    except Exception as exc:
        logger.warning("Twitter JSON parse failed: %s", exc)
        lines = [l.strip() for l in resp.text.splitlines() if l.strip() and not l.strip().startswith("#")]
        return [{"type": f"POST_{i+1}", "text": l} for i, l in enumerate(lines[:10])]


def _generate_linkedin(brief: BookBrief, gateway: Any) -> list[dict]:
    prompt = f"""Book: {brief.title}{(' — ' + brief.subtitle) if brief.subtitle else ''}
Author: {brief.author_name}
Genre: {brief.genre} | Audience: {brief.target_audience or 'professionals'}
Promise: {brief.promise[:600]}
Key themes: {', '.join(brief.key_themes[:5]) or 'leadership, influence'}

Write 6 LinkedIn posts (150–350 words each) for a professional book launch.
Include one of each: ANNOUNCEMENT, EXCERPT_INSIGHT, LESSON_FROM_WRITING, COMMUNITY_QUESTION, LAUNCH_DAY, POST_LAUNCH_REFLECTION

Return ONLY a JSON array: [{{"type":"ANNOUNCEMENT","text":"..."}},...] — no other text."""

    resp = gateway.complete(
        messages=_msg(
            "You are a professional thought-leadership writer for LinkedIn. Posts are substantive, not salesy. First line is a hook. Voice matches a seasoned author and leader.",
            prompt,
        ),
        task_type="draft",
        agent_id="book-launch",
        max_tokens=3000,
    )
    try:
        return _extract_json(resp.text)
    except Exception as exc:
        logger.warning("LinkedIn JSON parse failed: %s", exc)
        return [{"type": "POST", "text": resp.text[:1500]}]


def _generate_press_release(brief: BookBrief, gateway: Any) -> str:
    wc = f"approx. {brief.total_word_count:,} words" if brief.total_word_count else "full-length"
    prompt = f"""Write a 600–800 word press release for the following book launch:

Title: {brief.title}
Subtitle: {brief.subtitle or '(none)'}
Author: {brief.author_name}
Genre/Category: {brief.genre}
Target audience: {brief.target_audience or 'general readers'}
Core promise: {brief.promise[:600]}
Key themes: {', '.join(brief.key_themes[:5]) or 'leadership, influence'}
Length: {wc}

Format exactly as:
FOR IMMEDIATE RELEASE

[HEADLINE in ALL CAPS]

[City, Date] — [Opening paragraph: news hook — what this book does / why it matters now]

[Paragraph 2: who this book is for and the key problem it solves]

[Paragraph 3: what makes this book different / author authority]

[Author quote — 1-2 compelling sentences in quotation marks]

[About the Author — 2 sentences. Keep [AUTHOR BIO PLACEHOLDER] for anything needing real facts.]

[Boilerplate: About the Book — title, author, publisher (Self-published), format, availability (Amazon/major retailers)]

Contact:
[PUBLICIST NAME PLACEHOLDER]
[EMAIL PLACEHOLDER]
[PHONE PLACEHOLDER]

###"""

    resp = gateway.complete(
        messages=_msg(
            "You are a professional book publicist. Write clear, factual press releases in AP style. Lead with the news hook, not the author bio.",
            prompt,
        ),
        task_type="strategy",
        agent_id="book-launch",
        max_tokens=2000,
    )
    return resp.text.strip()


def _generate_emails(brief: BookBrief, gateway: Any) -> list[dict]:
    prompt = f"""Write 3 book launch emails for: "{brief.title}" by {brief.author_name}

Book promise: {brief.promise[:500]}
Target audience: {brief.target_audience or 'readers interested in {brief.genre}'}

EMAIL 1 — PRE_LAUNCH (send 5–7 days before launch):
- 3 subject line options
- Body ~180 words: build anticipation, share why you wrote it
- CTA: "Reserve your copy" or "Add to your reading list"

EMAIL 2 — LAUNCH_DAY:
- 3 subject line options
- Body ~130 words: it's here, here's what you get
- CTA: Buy now (link placeholder)

EMAIL 3 — FOLLOW_UP (1 week after launch):
- 3 subject line options
- Body ~130 words: thank readers, ask for review, share momentum
- CTA: Leave a review on Amazon

Return ONLY JSON: [{{"type":"PRE_LAUNCH","subjects":["...","...","..."],"body":"...","cta":"..."}},...] — no other text."""

    resp = gateway.complete(
        messages=_msg(
            "You are an email marketing specialist for authors. Emails feel personal and direct, not like marketing copy. Short paragraphs. No jargon.",
            prompt,
        ),
        task_type="strategy",
        agent_id="book-launch",
        max_tokens=3000,
    )
    try:
        return _extract_json(resp.text)
    except Exception as exc:
        logger.warning("Email JSON parse failed: %s", exc)
        return [{"type": "EMAIL", "subjects": [], "body": resp.text[:1000], "cta": ""}]


def _generate_amazon_copy(brief: BookBrief, gateway: Any) -> dict:
    prompt = f"""Write Amazon KDP marketing copy for: "{brief.title}" by {brief.author_name}

Genre: {brief.genre}
Audience: {brief.target_audience or 'general readers'}
Promise: {brief.promise[:500]}
Themes: {', '.join(brief.key_themes[:4]) or 'leadership, growth'}

Return ONLY JSON with these exact keys:
{{
  "description": "150-word Amazon book description. Hook opening sentence. 2–3 body paragraphs. End with a call to action. Optimized for Amazon search.",
  "subtitles": ["subtitle option 1 (max 12 words, benefit-focused)", "option 2", "option 3"],
  "keywords": ["kw1","kw2","kw3","kw4","kw5","kw6","kw7"]
}}

Keywords: 7 KDP backend keywords/phrases targeting: {brief.genre}, {brief.target_audience or 'readers'}, themes above."""

    resp = gateway.complete(
        messages=_msg(
            "You are a KDP publishing specialist. Book descriptions are punchy and keyword-rich. Subtitles include a number or concrete benefit. Keywords target reader search intent.",
            prompt,
        ),
        task_type="draft",
        agent_id="book-launch",
        max_tokens=1500,
    )
    try:
        return _extract_json(resp.text)
    except Exception as exc:
        logger.warning("Amazon copy JSON parse failed: %s", exc)
        return {"description": resp.text[:600], "subtitles": [], "keywords": []}


def _generate_extended(brief: BookBrief, gateway: Any) -> dict:
    prompt = f"""Book: "{brief.title}" by {brief.author_name}
Promise: {brief.promise[:400]}
Genre: {brief.genre} | Audience: {brief.target_audience or 'readers'}

Write 4 short marketing assets. Return ONLY JSON with these exact keys:

{{
  "goodreads": "100-word Goodreads author update announcing the book. Personal and conversational.",
  "podcast_pitch": "100-word email pitch to podcast hosts explaining why {brief.author_name} would be a great guest.",
  "podcast_talking_points": ["talking point 1","talking point 2","talking point 3","talking point 4","talking point 5"],
  "newsletter_blurb": "80-word blurb other newsletter writers can copy-paste to feature the book.",
  "review_request": "120-word ARC reader review request template. Warm, grateful, no pressure. Uses [ARC Reader Name] placeholder. Asks for honest review on Amazon/Goodreads."
}}"""

    resp = gateway.complete(
        messages=_msg(
            "You are a book marketing specialist. Write authentic, non-salesy copy. Match the author's professional but warm voice.",
            prompt,
        ),
        task_type="draft",
        agent_id="book-launch",
        max_tokens=2000,
    )
    try:
        return _extract_json(resp.text)
    except Exception as exc:
        logger.warning("Extended assets JSON parse failed: %s", exc)
        return {
            "goodreads": "", "podcast_pitch": "", "podcast_talking_points": [],
            "newsletter_blurb": "", "review_request": resp.text[:500],
        }


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def generate_launch_assets(
    brief: BookBrief,
    gateway: Any,
    trigger: str = "pre_launch",
) -> dict:
    """
    Generate all launch asset types. Each type is isolated — a failure in one
    does not abort the others. Returns a complete assets dict (status may be
    'partial' if some generators errored).
    """
    assets: dict[str, Any] = {}
    errors: dict[str, str] = {}

    generators = [
        ("twitter",        lambda: _generate_twitter(brief, gateway)),
        ("linkedin",       lambda: _generate_linkedin(brief, gateway)),
        ("press_release",  lambda: _generate_press_release(brief, gateway)),
        ("emails",         lambda: _generate_emails(brief, gateway)),
        ("amazon_copy",    lambda: _generate_amazon_copy(brief, gateway)),
        ("extended",       lambda: _generate_extended(brief, gateway)),
    ]

    for key, fn in generators:
        try:
            logger.info("Generating %s for %s…", key, brief.slug)
            assets[key] = fn()
        except Exception as exc:
            logger.error("Failed to generate %s for %s: %s", key, brief.slug, exc)
            errors[key] = str(exc)
            # Store empty placeholder so the UI has a consistent shape
            assets[key] = [] if key in ("twitter", "linkedin", "emails") else (
                {} if key in ("amazon_copy", "extended") else ""
            )

    # Flatten extended into top-level for easier UI consumption
    extended = assets.pop("extended", {})
    assets["goodreads"]               = extended.get("goodreads", "")
    assets["podcast_pitch"]           = extended.get("podcast_pitch", "")
    assets["podcast_talking_points"]  = extended.get("podcast_talking_points", [])
    assets["newsletter_blurb"]        = extended.get("newsletter_blurb", "")
    assets["review_request"]          = extended.get("review_request", "")

    status = "failed" if len(errors) == len(generators) else (
        "partial" if errors else "complete"
    )

    result = {
        "book_slug":    brief.slug,
        "title":        brief.title,
        "author":       brief.author_name,
        "generated_at": _now_iso(),
        "trigger":      trigger,
        "status":       status,
        "errors":       errors,
        "assets":       assets,
    }
    save_assets(brief.slug, result)
    return result
