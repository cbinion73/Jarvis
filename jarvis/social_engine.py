"""
social_engine.py — Social Media Publishing Engine
===================================================
Autonomous content generation, scheduling, approval, deployment,
and performance learning loop for JARVIS book launches.

Agents:
  jjj          — Social Media Manager (content generation + scheduling)
  quicksilver  — Platform Deployment Lead (posting + execution)
  sage         — Performance Analytics + Learning Loop
  loki         — Marketing Director (strategy + adaptation)

Persistent storage: ~/.jarvis/publishing/
  posts.jsonl        — ContentPost records
  schedules.jsonl    — LaunchSchedule records
  engagement.jsonl   — SocialEngagement snapshots
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_json, atomic_write_jsonl

logger = logging.getLogger("jarvis.social_engine")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ContentPost:
    post_id: str
    project_id: str
    platform: str           # "instagram" | "facebook" | "youtube" | "tiktok" | "twitter" | "linkedin"
    content_type: str       # "text" | "image" | "video" | "reel" | "story" | "short"
    caption: str
    hashtags: list[str] = field(default_factory=list)
    media_prompt: str = ""
    scheduled_at: str = ""
    status: str = "draft"   # "draft" | "pending_approval" | "approved" | "posted" | "failed"
    approval_id: str = ""
    posted_at: str = ""
    platform_post_id: str = ""
    engagement: dict = field(default_factory=dict)  # likes, comments, shares, views

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ContentPost":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LaunchSchedule:
    schedule_id: str
    project_id: str
    phase: str              # "pre_launch" | "launch_week" | "post_launch"
    start_date: str
    end_date: str
    posts: list[str] = field(default_factory=list)  # post_ids
    total_posts: int = 0
    approved_posts: int = 0
    posted_posts: int = 0
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LaunchSchedule":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SocialEngagement:
    snapshot_id: str
    project_id: str
    platform: str
    captured_at: str
    followers: int = 0
    total_reach: int = 0
    total_engagement: int = 0
    top_post_id: str = ""
    top_post_engagement: int = 0
    sentiment_score: float = 0.0  # 0-1
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SocialEngagement":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Persistent store
# ---------------------------------------------------------------------------

class SocialEngineStore:
    ROOT = Path.home() / ".jarvis" / "publishing"

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or self.ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._posts_path = self._root / "posts.jsonl"
        self._schedules_path = self._root / "schedules.jsonl"
        self._engagement_path = self._root / "engagement.jsonl"
        self._posts_log_path = self._posts_path.with_name("posts_log.jsonl")
        self._posts_state_log_path = self._posts_path.with_name("posts_state_log.jsonl")
        self._schedules_log_path = self._schedules_path.with_name("schedules_log.jsonl")
        self._schedules_state_log_path = self._schedules_path.with_name("schedules_state_log.jsonl")
        self._engagement_log_path = self._engagement_path.with_name("engagement_log.jsonl")
        self._engagement_state_log_path = self._engagement_path.with_name("engagement_state_log.jsonl")

    # --- generic JSONL helpers ---

    def _legacy_log_path_for(self, path: Path) -> Path:
        if path == self._posts_path:
            return self._posts_log_path
        if path == self._schedules_path:
            return self._schedules_log_path
        if path == self._engagement_path:
            return self._engagement_log_path
        return path.with_name(f"{path.stem}_log.jsonl")

    def _state_log_path_for(self, path: Path) -> Path:
        if path == self._posts_path:
            return self._posts_state_log_path
        if path == self._schedules_path:
            return self._schedules_state_log_path
        if path == self._engagement_path:
            return self._engagement_state_log_path
        return path.with_name(f"{path.stem}_state_log.jsonl")

    def _load_jsonl(self, path: Path) -> list[dict]:
        if path.exists():
            records = []
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(record, dict):
                        records.append(record)
            except OSError:
                records = []
            if records:
                return records
        records = self._load_jsonl_from_state_log(path)
        if records:
            return records
        return self._load_jsonl_from_log(path)

    def _load_jsonl_from_log(self, path: Path) -> list[dict]:
        log_path = self._legacy_log_path_for(path)
        if not log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except OSError:
            return []
        return latest

    def _load_jsonl_from_state_log(self, path: Path) -> list[dict]:
        log_path = self._state_log_path_for(path)
        if not log_path.exists():
            return []
        latest: list[dict] = []
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                records = payload.get("records")
                if isinstance(records, list):
                    latest = [dict(item) for item in records if isinstance(item, dict)]
        except OSError:
            return []
        return latest

    def _save_jsonl(self, path: Path, records: list[dict]) -> None:
        try:
            append_jsonl(
                self._legacy_log_path_for(path),
                {
                    "saved_at": _now_iso(),
                    "records": records,
                },
                ensure_ascii=False,
            )
            append_jsonl(
                self._state_log_path_for(path),
                {
                    "saved_at": _now_iso(),
                    "records": records,
                },
                ensure_ascii=False,
            )
            atomic_write_jsonl(path, records, ensure_ascii=False)
        except OSError as exc:
            logger.warning("SocialEngineStore: failed to write %s: %s", path.name, exc)

    def _upsert_jsonl(self, path: Path, record: dict, key: str) -> None:
        records = self._load_jsonl(path)
        for i, r in enumerate(records):
            if r.get(key) == record[key]:
                records[i] = record
                self._save_jsonl(path, records)
                return
        records.append(record)
        self._save_jsonl(path, records)

    # --- Posts ---

    def save_post(self, post: ContentPost) -> None:
        self._upsert_jsonl(self._posts_path, post.to_dict(), "post_id")

    def get_post(self, post_id: str) -> ContentPost | None:
        for r in self._load_jsonl(self._posts_path):
            if r.get("post_id") == post_id:
                try:
                    return ContentPost.from_dict(r)
                except Exception:
                    return None
        return None

    def list_posts(self, project_id: str | None = None, status: str | None = None) -> list[ContentPost]:
        posts = []
        for r in self._load_jsonl(self._posts_path):
            try:
                p = ContentPost.from_dict(r)
                if project_id and p.project_id != project_id:
                    continue
                if status and p.status != status:
                    continue
                posts.append(p)
            except Exception:
                pass
        return posts

    # --- Schedules ---

    def save_schedule(self, schedule: LaunchSchedule) -> None:
        self._upsert_jsonl(self._schedules_path, schedule.to_dict(), "schedule_id")

    def get_schedule(self, schedule_id: str) -> LaunchSchedule | None:
        for r in self._load_jsonl(self._schedules_path):
            if r.get("schedule_id") == schedule_id:
                try:
                    return LaunchSchedule.from_dict(r)
                except Exception:
                    return None
        return None

    def list_schedules(self, project_id: str | None = None) -> list[LaunchSchedule]:
        result = []
        for r in self._load_jsonl(self._schedules_path):
            try:
                s = LaunchSchedule.from_dict(r)
                if project_id and s.project_id != project_id:
                    continue
                result.append(s)
            except Exception:
                pass
        return result

    # --- Engagement ---

    def save_engagement(self, snap: SocialEngagement) -> None:
        self._upsert_jsonl(self._engagement_path, snap.to_dict(), "snapshot_id")

    def list_engagement(self, project_id: str | None = None, platform: str | None = None) -> list[SocialEngagement]:
        result = []
        for r in self._load_jsonl(self._engagement_path):
            try:
                s = SocialEngagement.from_dict(r)
                if project_id and s.project_id != project_id:
                    continue
                if platform and s.platform != platform:
                    continue
                result.append(s)
            except Exception:
                pass
        return result


# ---------------------------------------------------------------------------
# Platform content templates
# ---------------------------------------------------------------------------

_PLATFORM_TEMPLATES: dict[str, dict] = {
    "instagram": {
        "style": "visual, punchy, emotion-first. Use line breaks. 3-5 sentences max per block.",
        "cta": "Drop a comment below or tap the link in bio.",
        "content_types": ["image", "reel", "story", "video"],
    },
    "facebook": {
        "style": "storytelling, conversational, longer-form. Build context before the payoff.",
        "cta": "Share this if it resonated. What's your experience?",
        "content_types": ["text", "image", "video"],
    },
    "youtube": {
        "style": "video script prompt — hook (0-30s), problem, solution, proof, CTA.",
        "cta": "Subscribe and hit the bell. Comment your biggest takeaway.",
        "content_types": ["video", "short"],
    },
    "tiktok": {
        "style": "fast hook in first 2 seconds, pattern interrupt, trend-aware, raw energy.",
        "cta": "Follow for more. Comment if this hit different.",
        "content_types": ["short", "video"],
    },
    "twitter": {
        "style": "punchy, provocative, single insight per tweet. Can thread.",
        "cta": "Retweet if you agree. Reply with your take.",
        "content_types": ["text"],
    },
    "linkedin": {
        "style": "professional insight, first-person story, data or framework. Build credibility.",
        "cta": "Follow for weekly insights. What's worked for you?",
        "content_types": ["text", "image", "video"],
    },
}

_HASHTAG_SETS: dict[str, list[str]] = {
    "pre_launch": [
        "#comingsoon", "#newbook", "#authorlife", "#writingcommunity",
        "#booklaunch", "#preorder", "#readerscommunity", "#amwriting",
        "#booknerd", "#selfpublishing", "#indieauthor", "#bookstagram",
        "#authorpreneur", "#creativeentrepreneur", "#buildingpublicly",
    ],
    "launch_week": [
        "#newrelease", "#booklaunch", "#itslive", "#availablenow",
        "#buyit", "#kindleunlimited", "#amazon", "#selfpublished",
        "#bookrecommendation", "#mustread", "#leadership", "#personaldevelopment",
        "#businessbook", "#entrepreneurship", "#growthmindset",
    ],
    "post_launch": [
        "#readerreview", "#bookreviews", "#testimonialtuesdays",
        "#whatpeoplearesaying", "#readersofinstagram", "#bookclub",
        "#authorcoach", "#lessonlearned", "#businessleadership",
        "#successmindset", "#bookworm", "#nonfiction",
    ],
}


def _build_hashtags(phase: str, platform: str, book_title: str, count: int = 12) -> list[str]:
    base = _HASHTAG_SETS.get(phase, _HASHTAG_SETS["launch_week"])
    title_slug = book_title.replace(" ", "").lower()[:20]
    extras = [f"#{title_slug}", "#jarvis", "#chrisb"]
    combined = (extras + base)[:count]
    # Twitter fewer hashtags
    if platform == "twitter":
        combined = combined[:5]
    return combined


def _build_media_prompt(platform: str, content_type: str, topic: str, book_title: str, phase: str) -> str:
    phase_mood = {
        "pre_launch": "mysterious, anticipatory, warm golden tones",
        "launch_week": "bold, energetic, celebratory, vibrant colors",
        "post_launch": "credible, trustworthy, social-proof, warm community feel",
    }.get(phase, "clean, professional, book-themed")

    if platform == "instagram" and content_type in ("reel", "story"):
        return (
            f"Vertical 9:16 short-form video thumbnail. Subject: {topic} related to '{book_title}'. "
            f"Mood: {phase_mood}. Typography overlay with bold sans-serif title text. "
            f"Professional author brand aesthetic. No text overlap on subject face."
        )
    if platform == "youtube":
        return (
            f"YouTube thumbnail 16:9. Subject: {topic} from '{book_title}'. "
            f"High-contrast, bold text overlay, expressive face or relevant visual. "
            f"Mood: {phase_mood}. Click-worthy but not clickbait."
        )
    if platform == "tiktok":
        return (
            f"TikTok cover frame 9:16. Raw authentic feel. {topic} for '{book_title}'. "
            f"Mood: {phase_mood}. Strong visual hook visible in first frame."
        )
    # Default square/landscape
    return (
        f"Social media graphic 1:1 or 4:5. Topic: {topic} for the book '{book_title}'. "
        f"Mood: {phase_mood}. Clean typography, author brand colors. "
        f"Professional but approachable design."
    )


def _build_caption(platform: str, content_type: str, topic: str, book_title: str,
                   author_name: str, phase: str) -> str:
    tmpl = _PLATFORM_TEMPLATES.get(platform, _PLATFORM_TEMPLATES["instagram"])
    style = tmpl["style"]
    cta = tmpl["cta"]

    phase_hooks = {
        "pre_launch": {
            "instagram": f"Something big is coming.\n\n'{book_title}' — a book that will change how you think about {topic}.\n\nI've been working on this for months. And it's almost ready.\n\n{cta}",
            "facebook": f"I want to let you in on something I've been building...\n\nFor the past several months, I've been writing a book called '{book_title}'. It's about {topic} — and more importantly, it's about the transformation that becomes possible when you get this right.\n\nI'll be sharing more soon. Stay close.\n\n{cta}",
            "linkedin": f"I'm about to publish something I'm genuinely proud of.\n\n'{book_title}' — a deep dive into {topic} built from years of real-world experience.\n\nIf you're a leader who wants to {topic}, this was written for you.\n\nMore details coming. Follow along.\n\n{cta}",
            "twitter": f"Something I've been building for months is almost ready.\n\n'{book_title}' — {topic}.\n\nDrop a 🔥 if you want to be first to know when it drops.",
            "tiktok": f"POV: You're about to read the book that changes how you think about {topic}.\n\n'{book_title}' is dropping soon. Follow so you don't miss it.",
            "youtube": f"COMING SOON: I wrote a book called '{book_title}' and it's about to drop. Here's why I wrote it and what's inside — {topic}. Hit subscribe so you're first to know.",
        },
        "launch_week": {
            "instagram": f"IT'S LIVE.\n\n'{book_title}' is officially available now.\n\nThis book is for anyone who's ever struggled with {topic}. I wrote every word of it for you.\n\nLink in bio to get your copy.\n\n{cta}",
            "facebook": f"Today is the day.\n\n'{book_title}' is now available — and I couldn't be more excited to share it with you.\n\nThis book covers {topic} in a way that's practical, direct, and built for real life — not theory.\n\nGrab your copy: [link]\n\n{cta}",
            "linkedin": f"My new book '{book_title}' is now published.\n\nIf you've ever faced the challenge of {topic}, this book gives you a clear framework and the exact steps to move forward.\n\nAvailable now on Amazon. Link in comments.\n\n{cta}",
            "twitter": f"'{book_title}' is LIVE. 🚀\n\nEverything I know about {topic} — in one book.\n\nLink below 👇",
            "tiktok": f"THE BOOK IS LIVE. '{book_title}' is out now. If you struggle with {topic}, this one's for you. Link in bio.",
            "youtube": f"It's finally here — '{book_title}' is now available. In this video I'm breaking down {topic} and what makes this book different. Watch to the end.",
        },
        "post_launch": {
            "instagram": f"The messages keep coming in.\n\nReaders of '{book_title}' are already using what they learned about {topic}.\n\nHere's what one reader said: [add quote]\n\nGet your copy — link in bio.\n\n{cta}",
            "facebook": f"Here's what readers are saying about '{book_title}':\n\n[Reader quote about {topic}]\n\nIf this resonates with you, the book is available now. Real stories, real results.\n\n{cta}",
            "linkedin": f"A week after publishing '{book_title}', here's what I'm hearing from readers:\n\nThe section on {topic} is getting the most response.\n\nLeadership isn't complex — but it does require clarity. This book gives you that.\n\nStill available. Link in comments.\n\n{cta}",
            "twitter": f"A week in and '{book_title}' readers are already seeing results with {topic}.\n\nThis is why I write. ❤️",
            "tiktok": f"One week since '{book_title}' launched. Readers are ALREADY getting results with {topic}. This is everything. Link in bio.",
            "youtube": f"One week since '{book_title}' launched — here's what readers are saying about {topic} and how this book is helping them take action.",
        },
    }

    platform_captions = phase_hooks.get(phase, phase_hooks["launch_week"])
    caption = platform_captions.get(platform, f"'{book_title}' — {topic}. By {author_name}. {cta}")
    return caption


# ---------------------------------------------------------------------------
# JJJAgent — Social Media Manager
# ---------------------------------------------------------------------------

class JJJAgent:
    """
    J. Jonah Jameson: relentless, driven, wants results yesterday.
    Generates content, builds schedules, and keeps the pipeline full.
    """

    PLATFORMS = ["instagram", "facebook", "youtube", "tiktok", "twitter", "linkedin"]

    def __init__(self, store: SocialEngineStore) -> None:
        self._store = store

    def generate_post(
        self,
        project_id: str,
        platform: str,
        content_type: str,
        topic: str,
        book_title: str,
        phase: str,
        author_name: str = "Chris Binion",
        scheduled_at: str = "",
    ) -> ContentPost:
        """
        Generate a single ContentPost for a given platform, topic, and phase.
        Status is set to 'pending_approval'.
        """
        caption = _build_caption(platform, content_type, topic, book_title, author_name, phase)
        hashtags = _build_hashtags(phase, platform, book_title, count=13)
        media_prompt = _build_media_prompt(platform, content_type, topic, book_title, phase)

        post = ContentPost(
            post_id=str(uuid.uuid4()),
            project_id=project_id,
            platform=platform,
            content_type=content_type,
            caption=caption,
            hashtags=hashtags,
            media_prompt=media_prompt,
            scheduled_at=scheduled_at or _now_iso(),
            status="pending_approval",
            approval_id=str(uuid.uuid4()),
        )
        self._store.save_post(post)
        logger.debug("JJJAgent: generated post %s for %s (%s)", post.post_id, platform, phase)
        return post

    def generate_launch_schedule(
        self,
        project_id: str,
        book_title: str,
        launch_date_iso: str,
        author_name: str = "Chris Binion",
    ) -> LaunchSchedule:
        """
        Build a full 90-day launch schedule:
          - Pre-launch: 30 days before, 3 posts/week (teaser content)
          - Launch week: daily posts across all platforms
          - Post-launch: 2 posts/week for 60 days

        Returns a LaunchSchedule with all ContentPost objects created as drafts.
        """
        launch_dt = _parse_dt(launch_date_iso)
        if launch_dt is None:
            launch_dt = datetime.now(timezone.utc) + timedelta(days=30)
        launch_dt = _utc(launch_dt)

        pre_start = launch_dt - timedelta(days=30)
        post_end = launch_dt + timedelta(days=60)

        all_post_ids: list[str] = []

        # --- Pre-launch: 30 days, 3x/week ---
        pre_launch_topics = [
            "the journey of writing this book",
            "what inspired the core idea",
            "the transformation readers will experience",
            "a powerful insight from chapter one",
            "why now is the time to read this",
            "the author's personal story behind the book",
            "a behind-the-scenes look at the writing process",
            "the key problem this book solves",
            "a quote from the book that says it all",
            "what readers are saying before launch",
            "the research and frameworks inside",
            "who this book was written for",
        ]
        platforms_rotation = ["instagram", "facebook", "linkedin", "twitter", "instagram", "tiktok"]
        content_types_map = {
            "instagram": "image",
            "facebook": "text",
            "linkedin": "text",
            "twitter": "text",
            "tiktok": "short",
            "youtube": "video",
        }

        day_offset = 0
        topic_idx = 0
        platform_idx = 0
        while day_offset < 30:
            # 3 posts per week = every ~2-3 days
            for _ in range(3):
                if day_offset >= 30:
                    break
                platform = platforms_rotation[platform_idx % len(platforms_rotation)]
                topic = pre_launch_topics[topic_idx % len(pre_launch_topics)]
                ct = content_types_map.get(platform, "text")
                sched = _iso(_utc(pre_start + timedelta(days=day_offset, hours=9)))
                post = self.generate_post(
                    project_id=project_id,
                    platform=platform,
                    content_type=ct,
                    topic=topic,
                    book_title=book_title,
                    phase="pre_launch",
                    author_name=author_name,
                    scheduled_at=sched,
                )
                post.status = "draft"
                self._store.save_post(post)
                all_post_ids.append(post.post_id)
                topic_idx += 1
                platform_idx += 1
                day_offset += 2 if day_offset % 3 == 0 else 3

        # --- Launch week: daily across all platforms ---
        launch_week_topics = [
            "the book is live — here's what's inside",
            "why I wrote this book",
            "the first thing readers are saying",
            "the core framework explained",
            "the most important chapter",
            "results readers are already getting",
            "final 24 hours of launch pricing",
        ]
        for day_num in range(7):
            platform = self.PLATFORMS[day_num % len(self.PLATFORMS)]
            topic = launch_week_topics[day_num]
            ct = content_types_map.get(platform, "text")
            sched = _iso(_utc(launch_dt + timedelta(days=day_num, hours=8)))
            post = self.generate_post(
                project_id=project_id,
                platform=platform,
                content_type=ct,
                topic=topic,
                book_title=book_title,
                phase="launch_week",
                author_name=author_name,
                scheduled_at=sched,
            )
            post.status = "draft"
            self._store.save_post(post)
            all_post_ids.append(post.post_id)

        # --- Post-launch: 2x/week for 60 days ---
        post_launch_topics = [
            "reader testimonials and results",
            "an actionable tip from the book",
            "the most-shared quote from the book",
            "a follow-up insight the book sparked",
            "a reader's transformation story",
            "answering the top question readers ask",
            "what's next after reading this book",
            "the research behind the main framework",
            "a concept that applies to everyday leadership",
            "connecting the book to current events",
            "an honest reflection on the writing journey",
            "the impact readers are reporting",
            "a deeper dive into chapter three",
            "pairing this book with a complementary resource",
            "the community forming around this book",
            "six weeks later — what readers are saying",
        ]
        post_day_offset = 0
        post_topic_idx = 0
        post_platform_idx = 0
        while post_day_offset < 60:
            for _ in range(2):
                if post_day_offset >= 60:
                    break
                platform = self.PLATFORMS[post_platform_idx % len(self.PLATFORMS)]
                topic = post_launch_topics[post_topic_idx % len(post_launch_topics)]
                ct = content_types_map.get(platform, "text")
                sched = _iso(_utc(launch_dt + timedelta(days=7 + post_day_offset, hours=10)))
                post = self.generate_post(
                    project_id=project_id,
                    platform=platform,
                    content_type=ct,
                    topic=topic,
                    book_title=book_title,
                    phase="post_launch",
                    author_name=author_name,
                    scheduled_at=sched,
                )
                post.status = "draft"
                self._store.save_post(post)
                all_post_ids.append(post.post_id)
                post_topic_idx += 1
                post_platform_idx += 1
                post_day_offset += 3 if post_day_offset % 2 == 0 else 4

        schedule = LaunchSchedule(
            schedule_id=str(uuid.uuid4()),
            project_id=project_id,
            phase="pre_launch",
            start_date=_iso(pre_start),
            end_date=_iso(post_end),
            posts=all_post_ids,
            total_posts=len(all_post_ids),
            approved_posts=0,
            posted_posts=0,
            status="active",
        )
        self._store.save_schedule(schedule)
        logger.info(
            "JJJAgent: generated launch schedule %s — %d posts for project %s",
            schedule.schedule_id,
            len(all_post_ids),
            project_id,
        )
        return schedule

    def get_posts_due_for_approval(self, project_id: str) -> list[ContentPost]:
        """Posts scheduled within the next 72 hours with status 'pending_approval'."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=72)
        result = []
        for post in self._store.list_posts(project_id=project_id, status="pending_approval"):
            sched = _parse_dt(post.scheduled_at)
            if sched is None:
                continue
            sched = _utc(sched)
            if now <= sched <= cutoff:
                result.append(post)
        result.sort(key=lambda p: p.scheduled_at)
        return result

    def get_posts_approved_and_ready(self, project_id: str) -> list[ContentPost]:
        """Posts with status 'approved' scheduled within the next 24 hours."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=24)
        result = []
        for post in self._store.list_posts(project_id=project_id, status="approved"):
            sched = _parse_dt(post.scheduled_at)
            if sched is None:
                continue
            sched = _utc(sched)
            if sched <= cutoff:
                result.append(post)
        result.sort(key=lambda p: p.scheduled_at)
        return result


# ---------------------------------------------------------------------------
# QuicksilverAgent — Platform Deployment Lead
# ---------------------------------------------------------------------------

class QuicksilverAgent:
    """
    Quicksilver: blink-and-you'll-miss-it execution.
    Posts go out exactly when they're supposed to, no delays.
    """

    def __init__(self, store: SocialEngineStore) -> None:
        self._store = store

    # --- Platform stubs ---

    def _post_facebook(self, post: ContentPost) -> dict:
        page_id = os.environ.get("FACEBOOK_PAGE_ID", "")
        token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        if not page_id or not token:
            return {"ok": False, "reason": "not_configured", "platform": "facebook"}

        url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        full_text = post.caption + "\n\n" + " ".join(post.hashtags)
        payload = json.dumps({"message": full_text, "access_token": token}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "ok": True,
                    "platform_post_id": data.get("id", ""),
                    "posted_at": _now_iso(),
                }
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
            return {"ok": False, "reason": str(exc), "platform": "facebook"}

    def _post_instagram(self, post: ContentPost) -> dict:
        ig_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
        token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        if not ig_account_id or not token:
            return {"ok": False, "reason": "not_configured", "platform": "instagram"}

        # Step 1: create media container
        url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media"
        full_caption = post.caption + "\n\n" + " ".join(post.hashtags)
        payload = json.dumps({
            "caption": full_caption,
            "access_token": token,
            "media_type": "IMAGE",
            "image_url": post.media_prompt[:200],  # placeholder until real image URL available
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                creation_id = data.get("id", "")

            # Step 2: publish the container
            pub_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media_publish"
            pub_payload = json.dumps({"creation_id": creation_id, "access_token": token}).encode("utf-8")
            pub_req = urllib.request.Request(
                pub_url, data=pub_payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(pub_req, timeout=10) as pub_resp:
                pub_data = json.loads(pub_resp.read().decode("utf-8"))
                return {"ok": True, "platform_post_id": pub_data.get("id", ""), "posted_at": _now_iso()}
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
            return {"ok": False, "reason": str(exc), "platform": "instagram"}

    def _post_youtube(self, post: ContentPost) -> dict:
        api_key = os.environ.get("YOUTUBE_API_KEY", "")
        if not api_key:
            return {"ok": False, "reason": "not_configured", "platform": "youtube"}

        # YouTube Data API v3 — video insert (stub: returns simulated success for non-video content)
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,status&key={api_key}"
        payload = json.dumps({
            "snippet": {
                "title": post.caption[:100],
                "description": post.caption + "\n\n" + " ".join(post.hashtags),
                "tags": [h.lstrip("#") for h in post.hashtags],
            },
            "status": {"privacyStatus": "public"},
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "platform_post_id": data.get("id", ""), "posted_at": _now_iso()}
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as exc:
            return {"ok": False, "reason": str(exc), "platform": "youtube"}

    def _post_generic_stub(self, post: ContentPost) -> dict:
        """Graceful no-op for platforms without full API integration yet."""
        return {"ok": False, "reason": "not_configured", "platform": post.platform}

    def post_to_platform(self, post: ContentPost) -> dict:
        """Dispatch a ContentPost to its target platform."""
        platform = post.platform.lower()

        if platform == "facebook":
            result = self._post_facebook(post)
        elif platform == "instagram":
            result = self._post_instagram(post)
        elif platform == "youtube":
            result = self._post_youtube(post)
        else:
            # tiktok, twitter, linkedin — stub for now
            result = self._post_generic_stub(post)

        if result.get("ok"):
            post.status = "posted"
            post.posted_at = result.get("posted_at", _now_iso())
            post.platform_post_id = result.get("platform_post_id", "")
        else:
            logger.info(
                "QuicksilverAgent: post %s not deployed to %s (%s)",
                post.post_id,
                platform,
                result.get("reason"),
            )
            if result.get("reason") not in ("not_configured",):
                post.status = "failed"

        self._store.save_post(post)
        return result

    def execute_scheduled_posts(self, project_id: str) -> dict:
        """
        Run all approved + due posts for the project.
        Returns a summary with counts and per-post results.
        """
        jjj = JJJAgent(self._store)
        due_posts = jjj.get_posts_approved_and_ready(project_id)

        if not due_posts:
            return {
                "project_id": project_id,
                "executed": 0,
                "succeeded": 0,
                "failed": 0,
                "not_configured": 0,
                "results": [],
                "message": "No approved posts are due in the next 24 hours.",
            }

        results = []
        succeeded = 0
        failed = 0
        not_configured = 0

        for post in due_posts:
            result = self.post_to_platform(post)
            result["post_id"] = post.post_id
            result["platform"] = post.platform
            result["scheduled_at"] = post.scheduled_at
            results.append(result)

            if result.get("ok"):
                succeeded += 1
            elif result.get("reason") == "not_configured":
                not_configured += 1
            else:
                failed += 1

        # Refresh schedule counters
        for schedule in self._store.list_schedules(project_id=project_id):
            posted = len(self._store.list_posts(project_id=project_id, status="posted"))
            approved = len(self._store.list_posts(project_id=project_id, status="approved"))
            schedule.posted_posts = posted
            schedule.approved_posts = approved
            self._store.save_schedule(schedule)

        return {
            "project_id": project_id,
            "executed": len(due_posts),
            "succeeded": succeeded,
            "failed": failed,
            "not_configured": not_configured,
            "results": results,
        }


# ---------------------------------------------------------------------------
# SageAgent (social) — Performance Analytics + Learning Loop
# ---------------------------------------------------------------------------

class SageAgent:
    """
    Sage: reads the data so the team doesn't have to guess.
    Turns engagement numbers into sharp, actionable direction.
    """

    def __init__(self, store: SocialEngineStore) -> None:
        self._store = store

    def capture_engagement_snapshot(self, project_id: str, platform: str) -> SocialEngagement:
        """
        Capture an engagement snapshot for a platform.
        Stubs gracefully if API keys are not set.
        """
        snap = SocialEngagement(
            snapshot_id=str(uuid.uuid4()),
            project_id=project_id,
            platform=platform,
            captured_at=_now_iso(),
        )

        if platform == "facebook":
            page_id = os.environ.get("FACEBOOK_PAGE_ID", "")
            token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
            if not page_id or not token:
                snap.notes = "Facebook Insights not configured"
                self._store.save_engagement(snap)
                return snap

            url = (
                f"https://graph.facebook.com/v18.0/{page_id}/insights"
                f"?metric=page_fans,page_impressions,page_engaged_users"
                f"&access_token={token}"
            )
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    metrics = {item["name"]: item["values"][-1]["value"] for item in data.get("data", [])}
                    snap.followers = int(metrics.get("page_fans", 0))
                    snap.total_reach = int(metrics.get("page_impressions", 0))
                    snap.total_engagement = int(metrics.get("page_engaged_users", 0))
            except Exception as exc:
                snap.notes = f"Facebook Insights error: {exc}"

        elif platform == "instagram":
            token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
            ig_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
            if not token or not ig_account_id:
                snap.notes = "Instagram Basic Display not configured"
                self._store.save_engagement(snap)
                return snap

            url = (
                f"https://graph.facebook.com/v18.0/{ig_account_id}"
                f"?fields=followers_count,media_count&access_token={token}"
            )
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    snap.followers = int(data.get("followers_count", 0))
            except Exception as exc:
                snap.notes = f"Instagram API error: {exc}"

        else:
            snap.notes = f"{platform} analytics not yet configured"

        # Augment with local post data
        posted_posts = self._store.list_posts(project_id=project_id, status="posted")
        platform_posts = [p for p in posted_posts if p.platform == platform]
        if platform_posts:
            def _engagement_score(p: ContentPost) -> int:
                e = p.engagement
                return e.get("likes", 0) + e.get("comments", 0) * 2 + e.get("shares", 0) * 3 + e.get("views", 0)

            top = max(platform_posts, key=_engagement_score)
            snap.top_post_id = top.post_id
            snap.top_post_engagement = _engagement_score(top)
            snap.total_engagement = max(snap.total_engagement, sum(_engagement_score(p) for p in platform_posts))

        self._store.save_engagement(snap)
        logger.debug("SageAgent: captured %s snapshot for project %s", platform, project_id)
        return snap

    def analyze_performance(self, project_id: str) -> dict:
        """
        Analyze all engagement snapshots + post data for a project.
        Returns: top_performing_platform, content_type, best_posting_time,
                 avg_engagement_rate, sentiment_trend, recommended_adjustments.
        """
        snaps = self._store.list_engagement(project_id=project_id)
        posts = self._store.list_posts(project_id=project_id, status="posted")

        # Platform engagement totals
        platform_engagement: dict[str, int] = {}
        for snap in snaps:
            platform_engagement[snap.platform] = (
                platform_engagement.get(snap.platform, 0) + snap.total_engagement
            )

        top_platform = max(platform_engagement, key=lambda k: platform_engagement[k]) if platform_engagement else "instagram"

        # Content type performance
        type_engagement: dict[str, list[int]] = {}
        posting_hour_engagement: dict[int, list[int]] = {}
        total_reach = 0
        total_eng = 0

        for post in posts:
            score = (
                post.engagement.get("likes", 0)
                + post.engagement.get("comments", 0) * 2
                + post.engagement.get("shares", 0) * 3
                + post.engagement.get("views", 0)
            )
            ct = post.content_type
            type_engagement.setdefault(ct, []).append(score)

            sched = _parse_dt(post.scheduled_at)
            if sched:
                hr = _utc(sched).hour
                posting_hour_engagement.setdefault(hr, []).append(score)

            total_eng += score
            total_reach += post.engagement.get("views", post.engagement.get("likes", 0)) or 1

        top_content_type = "video"
        if type_engagement:
            top_content_type = max(type_engagement, key=lambda k: sum(type_engagement[k]) / max(len(type_engagement[k]), 1))

        best_hour = 19  # default 7pm
        if posting_hour_engagement:
            best_hour = max(posting_hour_engagement, key=lambda h: sum(posting_hour_engagement[h]) / max(len(posting_hour_engagement[h]), 1))

        # Map hour to human-readable best time
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        hour_str = f"{best_hour % 12 or 12}{'am' if best_hour < 12 else 'pm'}"
        # Simple heuristic: mid-week if no data, else parse from most active posts
        best_day = "Tuesday"
        if posts:
            day_counts: dict[int, int] = {}
            for post in posts:
                sched = _parse_dt(post.scheduled_at)
                if sched:
                    day_counts[_utc(sched).weekday()] = day_counts.get(_utc(sched).weekday(), 0) + 1
            if day_counts:
                best_day = weekdays[max(day_counts, key=lambda d: day_counts[d])]

        best_posting_time = f"{best_day} {hour_str}"

        avg_engagement_rate = round(total_eng / max(total_reach, 1) * 100, 2)

        # Sentiment trend from snapshots
        if len(snaps) >= 2:
            recent_scores = [s.sentiment_score for s in sorted(snaps, key=lambda s: s.captured_at)[-5:]]
            if recent_scores[-1] > recent_scores[0] + 0.05:
                sentiment_trend = "improving"
            elif recent_scores[-1] < recent_scores[0] - 0.05:
                sentiment_trend = "declining"
            else:
                sentiment_trend = "stable"
        else:
            sentiment_trend = "stable"

        # Recommendations
        recommended_adjustments: list[str] = []
        if top_platform != "instagram":
            recommended_adjustments.append(f"Double down on {top_platform} — it's your top performer")
        if top_content_type != "video":
            recommended_adjustments.append("Increase video content — typically 2-3x higher organic reach")
        if avg_engagement_rate < 2.0:
            recommended_adjustments.append("Engagement rate is below 2% — test stronger hooks in captions")
        if best_hour < 6 or best_hour > 22:
            recommended_adjustments.append("Post between 7am-9pm to maximize audience availability")
        if sentiment_trend == "declining":
            recommended_adjustments.append("Sentiment declining — pivot to more storytelling and value-first content")
        if not recommended_adjustments:
            recommended_adjustments.append("Performance is strong — maintain current cadence and test new formats quarterly")

        return {
            "project_id": project_id,
            "top_performing_platform": top_platform,
            "top_performing_content_type": top_content_type,
            "best_posting_time": best_posting_time,
            "avg_engagement_rate": avg_engagement_rate,
            "sentiment_trend": sentiment_trend,
            "recommended_adjustments": recommended_adjustments,
            "total_posts_analyzed": len(posts),
            "snapshots_analyzed": len(snaps),
            "generated_at": _now_iso(),
        }

    def generate_adaptation_report(self, project_id: str) -> str:
        """
        Markdown-formatted report covering what worked, what didn't,
        and specific recommendations for the next launch.
        Stored and surfaced in the briefing.
        """
        analysis = self.analyze_performance(project_id)
        posts = self._store.list_posts(project_id=project_id, status="posted")

        def _score(p: ContentPost) -> int:
            e = p.engagement
            return e.get("likes", 0) + e.get("comments", 0) * 2 + e.get("shares", 0) * 3 + e.get("views", 0)

        posts_by_score = sorted(posts, key=_score, reverse=True)
        top3 = posts_by_score[:3]
        bottom3 = posts_by_score[-3:] if len(posts_by_score) >= 6 else []

        lines = [
            f"# Social Media Adaptation Report",
            f"**Project:** `{project_id}`  ",
            f"**Generated:** {_now_iso()[:10]}",
            "",
            "---",
            "",
            "## What Worked",
            "",
            f"**Top Platform:** {analysis['top_performing_platform'].capitalize()} — this delivered the highest engagement across all tracked activity.",
            f"**Best Content Type:** {analysis['top_performing_content_type'].capitalize()} posts outperformed all other formats.",
            f"**Best Posting Time:** {analysis['best_posting_time']} consistently showed the strongest engagement windows.",
            "",
            "### Top 3 Posts",
        ]
        if top3:
            for i, p in enumerate(top3, 1):
                lines.append(f"{i}. **{p.platform.capitalize()}** ({p.content_type}) — score {_score(p)} | `{p.post_id[:8]}`")
                lines.append(f"   > {p.caption[:120]}...")
                lines.append("")
        else:
            lines.append("No posted data available yet.")
            lines.append("")

        lines += [
            "---",
            "",
            "## What Didn't Work",
            "",
        ]
        if bottom3:
            for p in bottom3:
                lines.append(f"- **{p.platform.capitalize()}** ({p.content_type}) — low engagement (score {_score(p)})")
        else:
            lines.append("- Insufficient data to identify low performers yet.")
        lines.append("")

        lines += [
            "---",
            "",
            "## Recommendations for Next Launch",
            "",
        ]
        for i, rec in enumerate(analysis["recommended_adjustments"], 1):
            lines.append(f"{i}. {rec}")
        lines += [
            "",
            f"**Average Engagement Rate:** {analysis['avg_engagement_rate']}%",
            f"**Sentiment Trend:** {analysis['sentiment_trend'].capitalize()}",
            "",
            "---",
            "_Report generated by Sage (JARVIS Performance Analytics)_",
        ]

        report = "\n".join(lines)

        # Persist the report
        reports_path = SocialEngineStore.ROOT / "adaptation_reports.jsonl"
        try:
            record = {
                "report_id": str(uuid.uuid4()),
                "project_id": project_id,
                "generated_at": _now_iso(),
                "report": report,
            }
            with reports_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("SageAgent: could not persist adaptation report: %s", exc)

        return report

    def get_amazon_sales_snapshot(self, asin: str) -> dict:
        """
        Fetch Amazon sales/rank data via Product Advertising API.
        Stubs gracefully if not configured.
        """
        access_key = os.environ.get("AMAZON_ACCESS_KEY", "")
        affiliate_tag = os.environ.get("AMAZON_AFFILIATE_TAG", "")
        if not access_key:
            return {
                "asin": asin,
                "configured": False,
                "note": "Set AMAZON_ACCESS_KEY to enable",
                "captured_at": _now_iso(),
            }

        # Product Advertising API v5 stub
        url = (
            f"https://webservices.amazon.com/paapi5/getitems"
            f"?keywords={asin}&PartnerTag={affiliate_tag}&PartnerType=Associates"
        )
        try:
            req = urllib.request.Request(
                url,
                headers={"x-api-key": access_key, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "asin": asin,
                    "configured": True,
                    "data": data,
                    "captured_at": _now_iso(),
                }
        except Exception as exc:
            return {
                "asin": asin,
                "configured": True,
                "error": str(exc),
                "captured_at": _now_iso(),
            }

    def get_coursera_snapshot(self, course_id: str) -> dict:
        """
        Fetch Coursera course metrics via API.
        Stubs gracefully if not configured.
        """
        api_key = os.environ.get("COURSERA_API_KEY", "")
        if not api_key:
            return {
                "course_id": course_id,
                "configured": False,
                "note": "Set COURSERA_API_KEY to enable",
                "captured_at": _now_iso(),
            }

        url = f"https://api.coursera.org/api/courses.v1/{course_id}?fields=enrolledCount,rating"
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "course_id": course_id,
                    "configured": True,
                    "data": data,
                    "captured_at": _now_iso(),
                }
        except Exception as exc:
            return {
                "course_id": course_id,
                "configured": True,
                "error": str(exc),
                "captured_at": _now_iso(),
            }


# ---------------------------------------------------------------------------
# LokiAgent (social) — Marketing Director
# ---------------------------------------------------------------------------

class LokiAgent:
    """
    Loki: the god of narrative leverage.
    Builds the strategy, adapts when the battlefield changes.
    """

    def __init__(self, store: SocialEngineStore) -> None:
        self._store = store
        self._strategies_path = store._root / "launch_strategies.json"
        self._strategies_log_path = self._strategies_path.with_name("launch_strategies_log.jsonl")
        self._strategies_state_log_path = self._strategies_path.with_name("launch_strategies_state_log.jsonl")

    def _load_strategies(self) -> dict:
        if self._strategies_path.exists():
            try:
                payload = json.loads(self._strategies_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except (OSError, json.JSONDecodeError):
                pass
        payload = self._load_strategies_from_state_log()
        if payload:
            return payload
        return self._load_strategies_from_log()

    def _load_strategies_from_log(self) -> dict:
        if not self._strategies_log_path.exists():
            return {}
        latest: dict[str, Any] = {}
        try:
            for line in self._strategies_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = payload.get("strategies")
                if isinstance(data, dict):
                    latest = data
        except OSError:
            return {}
        return latest

    def _load_strategies_from_state_log(self) -> dict:
        if not self._strategies_state_log_path.exists():
            return {}
        latest: dict[str, Any] = {}
        try:
            for line in self._strategies_state_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data = payload.get("strategies")
                if isinstance(data, dict):
                    latest = data
        except OSError:
            return {}
        return latest

    def _save_strategies(self, data: dict) -> None:
        try:
            append_jsonl(
                self._strategies_log_path,
                {
                    "saved_at": _now_iso(),
                    "strategies": data,
                },
                ensure_ascii=False,
            )
            append_jsonl(
                self._strategies_state_log_path,
                {
                    "saved_at": _now_iso(),
                    "strategies": data,
                },
                ensure_ascii=False,
            )
            atomic_write_json(self._strategies_path, data, ensure_ascii=False)
        except OSError as exc:
            logger.warning("LokiAgent: failed to save strategies: %s", exc)

    def build_launch_strategy(
        self,
        project_id: str,
        book_title: str,
        launch_date: str,
        author_bio: str,
        key_themes: list[str],
    ) -> dict:
        """
        Build a comprehensive multi-platform launch strategy.
        """
        themes_str = ", ".join(key_themes[:5]) if key_themes else "leadership and personal development"

        strategy = {
            "strategy_id": str(uuid.uuid4()),
            "project_id": project_id,
            "book_title": book_title,
            "launch_date": launch_date,
            "created_at": _now_iso(),
            "pre_launch_strategy": [
                f"Build a 'founding readers' waitlist 30 days out — target 500 signups via Instagram and LinkedIn bio links",
                f"Create a 5-part email nurture sequence about {key_themes[0] if key_themes else 'the core topic'} — builds trust before the ask",
                f"Recruit 10-15 advance readers via direct outreach — offer free PDF, request honest review on Amazon at launch",
                f"Produce a 60-second 'why I wrote this book' Reel — pin it across Instagram and TikTok for pre-launch period",
                f"Partner with 2-3 complementary creators/podcasters for launch day cross-promotion",
            ],
            "launch_day_plan": {
                "06:00": "Email blast to full list — personal, story-driven, direct buy link",
                "07:00": "Instagram main feed post — launch announcement with bold visual",
                "08:00": "LinkedIn long-form post — professional framing of book thesis",
                "09:00": "Twitter/X thread — 7-tweet thread unpacking the core framework",
                "10:00": "TikTok — raw, energetic 30-second announcement video",
                "11:00": "Facebook — full launch story post with reader transformation hook",
                "12:00": "Instagram Story series — 5-slide countdown recap + swipe-up link",
                "14:00": "YouTube community post + pin comment on main channel video",
                "16:00": "Second email to unopens — different subject line, same CTA",
                "18:00": "LinkedIn comment engagement push — respond to all early comments",
                "20:00": "Instagram Live or TikTok Live — 15-min Q&A, thank early readers",
                "22:00": "Day-end recap story — 'Day 1 results' transparency post",
            },
            "post_launch_strategy": {
                "week_1": [
                    "Share first 5 reader testimonials — 1 per day across rotating platforms",
                    "Run a 72-hour 'early bird' discount or bonus bundle",
                    "Pitch to 3 podcast hosts in your niche — offer free review copy",
                ],
                "weeks_2_4": [
                    "Publish a 'reader results' case study post weekly",
                    "Start a weekly LinkedIn newsletter series pulling chapters from the book",
                    "Begin retargeting ads using the top-performing organic post as creative",
                ],
                "weeks_5_8": [
                    "Launch a 'book club' challenge — 5-day free content series",
                    "Apply for inclusion in 3 curated book lists (leadership, business, self-help)",
                    "Evergreen YouTube video using book content — targets discovery search",
                ],
            },
            "platform_priority": [
                {"platform": "instagram", "rationale": "Highest visual ROI for books; Reels drive discovery"},
                {"platform": "linkedin", "rationale": f"Ideal for {key_themes[0] if key_themes else 'professional'} content; high-intent audience"},
                {"platform": "tiktok", "rationale": "Unmatched organic reach for first-time authors; BookTok is real"},
                {"platform": "youtube", "rationale": "Long-term evergreen discovery; builds deepest trust"},
                {"platform": "facebook", "rationale": "Best for community building and retargeting ads"},
                {"platform": "twitter", "rationale": "Ideas platform; best for thought leadership positioning"},
            ],
            "content_mix": {
                "video": 40,
                "image": 25,
                "text": 20,
                "story": 10,
                "reel": 5,
            },
            "kpi_targets": {
                "followers_target": 500,
                "engagement_rate_target": 3.5,
                "sales_week1_target": 100,
                "email_list_growth_target": 250,
                "reviews_target_week4": 20,
            },
            "author_bio_snippet": author_bio[:200] if author_bio else "",
            "key_themes": key_themes,
        }

        strategies = self._load_strategies()
        strategies[project_id] = strategy
        self._save_strategies(strategies)

        logger.info("LokiAgent: built launch strategy for project %s (%s)", project_id, book_title)
        return strategy

    def adapt_strategy(self, project_id: str, sage_analysis: dict) -> dict:
        """
        Adapt the launch strategy based on Sage's performance analysis.
        Returns targeted recommendations keyed to observed data.
        """
        strategies = self._load_strategies()
        current_strategy = strategies.get(project_id, {})

        top_platform = sage_analysis.get("top_performing_platform", "instagram")
        top_content = sage_analysis.get("top_performing_content_type", "video")
        best_time = sage_analysis.get("best_posting_time", "Tuesday 7pm")
        avg_rate = sage_analysis.get("avg_engagement_rate", 0.0)
        sentiment = sage_analysis.get("sentiment_trend", "stable")
        recs = sage_analysis.get("recommended_adjustments", [])

        adaptations: list[str] = []

        if avg_rate < 1.0:
            adaptations.append(f"Engagement critically low ({avg_rate}%) — pause scheduling, rewrite hooks for next 5 posts")
        elif avg_rate < 2.5:
            adaptations.append(f"Engagement below target ({avg_rate}%) — A/B test 2 different caption styles this week")

        adaptations.append(f"Shift 60% of new content budget to {top_platform} — currently top performer")
        adaptations.append(f"Prioritize {top_content} format — outperforming other types in current data")
        adaptations.append(f"Reschedule remaining posts to {best_time} window where possible")

        if sentiment == "declining":
            adaptations.append("Sentiment declining — introduce 'behind the scenes' and gratitude content to re-humanize brand")
        elif sentiment == "improving":
            adaptations.append("Sentiment improving — this is the moment to ask for reviews and referrals")

        adaptations.extend(recs[:3])

        adapted = {
            "project_id": project_id,
            "adapted_at": _now_iso(),
            "based_on_analysis": sage_analysis.get("generated_at", ""),
            "adaptations": adaptations,
            "priority_platform": top_platform,
            "priority_content_type": top_content,
            "recommended_post_time": best_time,
            "original_strategy_id": current_strategy.get("strategy_id", ""),
        }

        # Persist the adaptation
        strategies[f"{project_id}_adapted"] = adapted
        self._save_strategies(strategies)

        return adapted


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_SEED_PROJECT_ID = "intentional-leader-001"
_SEED_BOOK_TITLE = "The Intentional Leader"
_SEED_AUTHOR = "Chris Binion"
_SEED_LAUNCH_DATE = "2026-07-01T09:00:00+00:00"


def _seed_social_engine(store: SocialEngineStore) -> bool:
    """
    Seed one example LaunchSchedule for 'The Intentional Leader'
    with 10 pre-generated posts (mix of platforms, all 'draft' status).
    Returns True if seeding occurred.
    """
    existing = store.list_schedules(project_id=_SEED_PROJECT_ID)
    if existing:
        return False

    launch_dt = datetime(2026, 7, 1, 9, 0, 0, tzinfo=timezone.utc)
    pre_start = launch_dt - timedelta(days=30)
    post_end = launch_dt + timedelta(days=60)

    seed_posts_data = [
        ("instagram", "image",   "the vision behind intentional leadership",  "pre_launch",  pre_start + timedelta(days=2,  hours=9)),
        ("linkedin",  "text",    "why most leaders lead reactively",           "pre_launch",  pre_start + timedelta(days=5,  hours=8)),
        ("facebook",  "text",    "a 3-question self-assessment for leaders",   "pre_launch",  pre_start + timedelta(days=9,  hours=10)),
        ("tiktok",    "short",   "the one shift that changes your leadership", "pre_launch",  pre_start + timedelta(days=12, hours=7)),
        ("twitter",   "text",    "what intentional leadership actually means", "pre_launch",  pre_start + timedelta(days=16, hours=9)),
        ("instagram", "reel",    "behind-the-scenes writing the book",        "pre_launch",  pre_start + timedelta(days=20, hours=8)),
        ("youtube",   "video",   "the framework inside the book",             "pre_launch",  pre_start + timedelta(days=25, hours=9)),
        ("instagram", "image",   "the book is officially live",               "launch_week", launch_dt + timedelta(hours=0)),
        ("linkedin",  "text",    "what readers are saying after day one",     "launch_week", launch_dt + timedelta(days=1, hours=8)),
        ("facebook",  "text",    "results leaders are already reporting",     "post_launch", launch_dt + timedelta(days=10, hours=10)),
    ]

    jjj = JJJAgent(store)
    post_ids = []

    for platform, ct, topic, phase, sched_dt in seed_posts_data:
        post = jjj.generate_post(
            project_id=_SEED_PROJECT_ID,
            platform=platform,
            content_type=ct,
            topic=topic,
            book_title=_SEED_BOOK_TITLE,
            phase=phase,
            author_name=_SEED_AUTHOR,
            scheduled_at=_iso(_utc(sched_dt)),
        )
        post.status = "draft"
        store.save_post(post)
        post_ids.append(post.post_id)

    schedule = LaunchSchedule(
        schedule_id=str(uuid.uuid4()),
        project_id=_SEED_PROJECT_ID,
        phase="pre_launch",
        start_date=_iso(pre_start),
        end_date=_iso(post_end),
        posts=post_ids,
        total_posts=len(post_ids),
        approved_posts=0,
        posted_posts=0,
        status="active",
    )
    store.save_schedule(schedule)

    logger.info(
        "SocialEngine seeded: schedule %s with %d posts for '%s'",
        schedule.schedule_id,
        len(post_ids),
        _SEED_BOOK_TITLE,
    )
    return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

@dataclass
class SocialEngine:
    store: SocialEngineStore
    jjj: JJJAgent
    quicksilver: QuicksilverAgent
    sage: SageAgent
    loki: LokiAgent


_social_engine_singleton: SocialEngine | None = None


def init_social_engine() -> SocialEngine:
    """
    Initialise the module-level SocialEngine singleton.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _social_engine_singleton
    if _social_engine_singleton is not None:
        return _social_engine_singleton

    store = SocialEngineStore()
    seeded = _seed_social_engine(store)
    if seeded:
        logger.info("SocialEngine: seeded initial data")

    engine = SocialEngine(
        store=store,
        jjj=JJJAgent(store),
        quicksilver=QuicksilverAgent(store),
        sage=SageAgent(store),
        loki=LokiAgent(store),
    )
    _social_engine_singleton = engine
    logger.info("SocialEngine singleton initialised")
    return engine


def get_social_engine() -> SocialEngine | None:
    """Return the module-level SocialEngine singleton if initialised."""
    return _social_engine_singleton
