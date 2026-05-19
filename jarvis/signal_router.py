"""JARVIS Signal Router — classifies signals and routes them to home projects."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

_OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL = "gpt-4.1-mini"

_EMAIL_PROMPT_TEMPLATE = """\
You are JARVIS, a home intelligence assistant. Analyze this email and determine:
1. Is it relevant to any of the user's home projects?
2. If yes, which project (by ID)?
3. What classification is it? (contractor_quote, bill, scheduling, project_update, family, other)
4. What tasks should be created from this email? (list with title, priority, due_date if mentioned)

Projects: {projects_json}
Email: Subject: {subject}, From: {sender}, Body: {body_preview}

Respond as JSON: {{"relevant": bool, "project_id": "uuid or null", "classification": "...", \
"extracted_tasks": [{{"title": "...", "priority": "medium", "due_date": "YYYY-MM-DD or null"}}], \
"summary": "one line summary of what this email means for the project"}}"""

_CALENDAR_PROMPT_TEMPLATE = """\
You are JARVIS, a home intelligence assistant. Analyze this calendar event and determine:
1. Is it relevant to any of the user's home projects?
2. If yes, which project (by ID)?
3. Is this event a direct project signal (e.g., contractor visit, inspection, delivery)?

Projects: {projects_json}
Event: Title: {title}, Description: {description}, Start: {start_time}

Respond as JSON: {{"relevant": bool, "project_id": "uuid or null", "is_project_signal": bool}}"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SignalRouter:
    """Classifies emails and calendar events and routes them to home projects."""

    def __init__(self, home_db, openai_api_key: str) -> None:
        self._db = home_db
        self._api_key = openai_api_key

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_active_projects(self) -> list[dict]:
        """Return active home projects from the DB."""
        try:
            conn = self._db._connect()
            if conn is None:
                return []
            import psycopg2.extras  # type: ignore

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, title, track, category, status
                    FROM home_projects
                    WHERE status IN ('active', 'planning')
                    ORDER BY created_at DESC
                    """,
                )
                rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception as exc:
            logger.error("signal_router._get_active_projects: %s", exc)
            return []

    def _call_openai(self, prompt: str) -> dict | None:
        """Call OpenAI chat completions and return parsed JSON response."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": _OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = requests.post(
                _OPENAI_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except requests.RequestException as exc:
            logger.error("signal_router._call_openai request error: %s", exc)
            return None
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            logger.error("signal_router._call_openai parse error: %s", exc)
            return None

    def _create_signal(
        self,
        sig_type: str,
        source: str,
        subject: str | None,
        body: str | None,
        sender: str | None,
        external_id: str | None,
        project_id: str | None,
        classification: str | None,
        extracted_tasks: list | None,
        signal_date: str | None,
    ) -> str | None:
        """Insert a home_signals record. Returns new signal UUID or None."""
        try:
            conn = self._db._connect()
            if conn is None:
                return None
            new_id = str(uuid.uuid4())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO home_signals
                        (id, type, source, subject, body, sender, external_id,
                         project_id, classified, classification, extracted_tasks,
                         signal_date, created_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s,
                         %s, NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        new_id,
                        sig_type,
                        source,
                        subject,
                        body,
                        sender,
                        external_id,
                        project_id,
                        bool(project_id),
                        classification,
                        json.dumps(extracted_tasks or []),
                        signal_date,
                    ),
                )
                conn.commit()
            conn.close()
            logger.debug("signal_router: created signal %s (%s/%s)", new_id, sig_type, source)
            return new_id
        except Exception as exc:
            logger.error("signal_router._create_signal: %s", exc)
            return None

    def _create_tasks_from_signal(
        self,
        project_id: str,
        extracted_tasks: list[dict],
        source_signal_id: str,
        task_source: str = "email_signal",
    ) -> int:
        """Create project_tasks from classification results. Returns count created."""
        created = 0
        try:
            conn = self._db._connect()
            if conn is None:
                return 0
            with conn.cursor() as cur:
                for task in extracted_tasks:
                    title = task.get("title", "").strip()
                    if not title:
                        continue
                    cur.execute(
                        """
                        INSERT INTO project_tasks
                            (id, project_id, title, status, priority, due_date,
                             source, source_signal_id, created_at, updated_at)
                        VALUES
                            (%s, %s, %s, 'open', %s, %s, %s, %s, NOW(), NOW())
                        """,
                        (
                            str(uuid.uuid4()),
                            project_id,
                            title,
                            task.get("priority", "medium"),
                            task.get("due_date") or None,
                            task_source,
                            source_signal_id,
                        ),
                    )
                    created += 1
                conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("signal_router._create_tasks_from_signal: %s", exc)
        return created

    def _mark_email_processed(self, email_id: str, project_id: str | None, signal_id: str | None) -> None:
        """Update email_cache row: processed=true, project_id, signal_id."""
        try:
            conn = self._db._connect()
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE email_cache
                    SET processed = TRUE,
                        project_id = %s,
                        signal_id  = %s,
                        synced_at  = NOW()
                    WHERE external_id = %s
                    """,
                    (project_id, signal_id, email_id),
                )
                conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("signal_router._mark_email_processed: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────────────

    def process_unprocessed_emails(self, limit: int = 20) -> int:
        """Fetch unprocessed emails from email_cache, classify, create signals/tasks.

        Returns the count of emails processed.
        """
        try:
            conn = self._db._connect()
            if conn is None:
                logger.warning("signal_router: no DB connection")
                return 0
            import psycopg2.extras  # type: ignore

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT external_id, source, thread_id, subject,
                           sender_email, sender_name, snippet, body_text,
                           received_at, importance, labels
                    FROM email_cache
                    WHERE processed = FALSE
                    ORDER BY received_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                emails = [dict(r) for r in cur.fetchall()]
            conn.close()
        except Exception as exc:
            logger.error("signal_router.process_unprocessed_emails DB read: %s", exc)
            return 0

        if not emails:
            logger.info("signal_router: no unprocessed emails found")
            return 0

        projects = self._get_active_projects()
        processed_count = 0

        for email in emails:
            try:
                classification = self.classify_email(email, projects)
                signal_id = None

                if classification.get("relevant"):
                    signal_data = {
                        "type": "email",
                        "source": email.get("source", "gmail"),
                        "subject": email.get("subject"),
                        "body": email.get("body_text") or email.get("snippet"),
                        "sender": email.get("sender_email"),
                        "external_id": email.get("external_id"),
                        "project_id": classification.get("project_id"),
                        "classification": classification.get("classification"),
                        "extracted_tasks": classification.get("extracted_tasks", []),
                        "signal_date": str(email.get("received_at", _now_iso())),
                    }
                    routed = self.route_signal(signal_data)
                    signal_id = routed.get("signal_id")

                self._mark_email_processed(
                    email_id=email.get("external_id", ""),
                    project_id=classification.get("project_id"),
                    signal_id=signal_id,
                )
                processed_count += 1
            except Exception as exc:
                logger.error(
                    "signal_router: error processing email %s: %s",
                    email.get("external_id"),
                    exc,
                )

        logger.info("signal_router: processed %d emails", processed_count)
        return processed_count

    def classify_email(self, email: dict, projects: list[dict]) -> dict:
        """Use OpenAI to classify an email against known projects.

        Returns:
            {
                relevant: bool,
                project_id: str | None,
                classification: str,
                extracted_tasks: list,
                summary: str,
            }
        """
        default: dict = {
            "relevant": False,
            "project_id": None,
            "classification": "other",
            "extracted_tasks": [],
            "summary": "",
        }

        if not self._api_key:
            logger.warning("signal_router.classify_email: no OpenAI API key configured")
            return default

        body_preview = (email.get("body_text") or email.get("snippet") or "")[:1500]
        projects_json = json.dumps(
            [
                {
                    "id": str(p.get("id", "")),
                    "title": p.get("title", ""),
                    "track": p.get("track", ""),
                    "category": p.get("category", ""),
                }
                for p in projects
            ],
            indent=None,
        )

        prompt = _EMAIL_PROMPT_TEMPLATE.format(
            projects_json=projects_json,
            subject=email.get("subject", "(no subject)"),
            sender=email.get("sender_email", "unknown"),
            body_preview=body_preview,
        )

        result = self._call_openai(prompt)
        if not result:
            return default

        # Sanitize and fill defaults
        return {
            "relevant": bool(result.get("relevant", False)),
            "project_id": result.get("project_id") or None,
            "classification": result.get("classification", "other"),
            "extracted_tasks": result.get("extracted_tasks") or [],
            "summary": result.get("summary", ""),
        }

    def process_calendar_event(self, event: dict, projects: list[dict]) -> dict:
        """Classify a calendar event — is it related to a home project?

        Returns:
            {relevant: bool, project_id: str | None, is_project_signal: bool}
        """
        default: dict = {"relevant": False, "project_id": None, "is_project_signal": False}

        if not self._api_key:
            logger.warning("signal_router.process_calendar_event: no OpenAI API key configured")
            return default

        projects_json = json.dumps(
            [
                {
                    "id": str(p.get("id", "")),
                    "title": p.get("title", ""),
                    "track": p.get("track", ""),
                    "category": p.get("category", ""),
                }
                for p in projects
            ],
            indent=None,
        )

        prompt = _CALENDAR_PROMPT_TEMPLATE.format(
            projects_json=projects_json,
            title=event.get("title", "(untitled)"),
            description=(event.get("description") or "")[:500],
            start_time=event.get("start_time", ""),
        )

        result = self._call_openai(prompt)
        if not result:
            return default

        return {
            "relevant": bool(result.get("relevant", False)),
            "project_id": result.get("project_id") or None,
            "is_project_signal": bool(result.get("is_project_signal", False)),
        }

    def route_signal(self, signal_data: dict) -> dict:
        """Create a signal record and optionally create tasks from it.

        Returns:
            {signal_id: str | None, tasks_created: int, project_id: str | None}
        """
        result: dict = {"signal_id": None, "tasks_created": 0, "project_id": None}

        project_id = signal_data.get("project_id")
        extracted_tasks = signal_data.get("extracted_tasks") or []

        signal_id = self._create_signal(
            sig_type=signal_data.get("type", "email"),
            source=signal_data.get("source", "gmail"),
            subject=signal_data.get("subject"),
            body=signal_data.get("body"),
            sender=signal_data.get("sender"),
            external_id=signal_data.get("external_id"),
            project_id=project_id,
            classification=signal_data.get("classification"),
            extracted_tasks=extracted_tasks,
            signal_date=signal_data.get("signal_date"),
        )

        result["signal_id"] = signal_id
        result["project_id"] = project_id

        if signal_id and project_id and extracted_tasks:
            task_source = (
                "calendar_signal" if signal_data.get("type") == "calendar" else "email_signal"
            )
            count = self._create_tasks_from_signal(
                project_id=project_id,
                extracted_tasks=extracted_tasks,
                source_signal_id=signal_id,
                task_source=task_source,
            )
            result["tasks_created"] = count
            logger.info(
                "signal_router: routed signal %s → project %s, %d tasks created",
                signal_id,
                project_id,
                count,
            )

        return result

    def run_full_scan(self) -> dict:
        """Process all unprocessed emails. Returns summary of what was found."""
        logger.info("signal_router: starting full scan")
        processed = self.process_unprocessed_emails(limit=50)
        return {
            "emails_processed": processed,
            "scanned_at": _now_iso(),
        }


# ── Module-level singleton ─────────────────────────────────────────────────────

_router: SignalRouter | None = None


def get_signal_router() -> SignalRouter | None:
    """Return the module-level SignalRouter singleton, or None if not initialized."""
    return _router


def init_signal_router(home_db, openai_api_key: str) -> SignalRouter:
    """Initialize and return the module-level SignalRouter singleton."""
    global _router
    _router = SignalRouter(home_db, openai_api_key)
    logger.info("signal_router: initialized")
    return _router
