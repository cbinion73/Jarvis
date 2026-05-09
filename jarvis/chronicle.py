from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig
from .openai_tasks import JarvisOpenAIClient
from .persona import build_specialist_prompt


@dataclass(slots=True)
class ChronicleEntry:
    timestamp: str
    actor: str
    theme: str
    note: str
    reflection: str


class ChronicleStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.entries_path = self.root / "entries.jsonl"

    def add(self, entry: ChronicleEntry) -> None:
        with self.entries_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry)) + "\n")

    def list_recent(self, limit: int = 10) -> list[dict]:
        if not self.entries_path.exists():
            return []
        lines = self.entries_path.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        return list(reversed(records[-limit:]))


class ChronicleSupport:
    def __init__(self, config: AppConfig, openai_client: JarvisOpenAIClient, store: ChronicleStore) -> None:
        self.config = config
        self.openai_client = openai_client
        self.store = store
        self.profile = config.load_json_profile(
            config.chronicle_profile_path,
            {
                "theologicalProfile": "Scripture-first, transparent, pastoral without manipulation.",
                "voiceNotes": [],
                "uncertaintyNotes": [],
                "familyDevotionalNotes": [],
            },
        )

    def devotional_pause(self, actor: str, theme: str, mode: str = "scripture") -> str:
        system = build_specialist_prompt(
            "Chronicle and devotional",
            "Prepare a short devotional pause that is Scripture-grounded, gentle, direct, and grounded.",
            extra_guidance=(
                "Distinguish Scripture from interpretation explicitly. "
                "Include a brief Uncertainty or Confidence Note whenever interpretation or application may reasonably vary. "
                f"Theological profile: {self.profile.get('theologicalProfile', '')} "
                f"Voice notes: {' '.join(self.profile.get('voiceNotes', []))} "
                f"Uncertainty notes: {' '.join(self.profile.get('uncertaintyNotes', []))}"
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Theme: {theme}\n"
            f"Requested devotional mode: {mode}\n"
            "Return a short devotional pause with labeled sections: Scripture, Interpretation, Prayer, Silence, Next Step, Uncertainty Note. "
            "If a section does not apply, say so plainly."
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=450)

    def chronicle_capture(self, actor: str, theme: str, note: str) -> dict:
        reflection = self.openai_client.prompt_text(
            system_prompt=build_specialist_prompt(
                "Chronicle reflection",
                "Turn the note into a short reflective entry that helps the user remember how God met them over time.",
                extra_guidance="Do not overstate certainty.",
            ),
            user_prompt=f"Actor: {actor}\nTheme: {theme}\nNote:\n{note}",
            max_output_tokens=220,
        )
        entry = ChronicleEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            theme=theme,
            note=note,
            reflection=reflection,
        )
        self.store.add(entry)
        return asdict(entry)

    def prayer_timeline(self, limit: int = 10) -> list[dict]:
        return self.store.list_recent(limit=limit)

    def prayer_theme_summary(self, limit: int = 25) -> dict:
        entries = self.store.list_recent(limit=limit)
        counts: dict[str, int] = {}
        recent_notes: dict[str, list[str]] = {}
        for entry in entries:
            theme = entry.get("theme", "unknown")
            counts[theme] = counts.get(theme, 0) + 1
            recent_notes.setdefault(theme, [])
            if len(recent_notes[theme]) < 2:
                recent_notes[theme].append(entry.get("reflection", ""))
        themes = [
            {
                "theme": theme,
                "count": count,
                "recent_reflections": recent_notes.get(theme, []),
            }
            for theme, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "themes": themes,
            "entries_considered": len(entries),
        }

    def family_devotional_prep(self, actor: str, theme: str, context: str = "") -> str:
        system = build_specialist_prompt(
            "family devotional preparation",
            "Prepare a family devotional that is Scripture-grounded, practical for a household, and gentle rather than preachy.",
            extra_guidance=(
                "Distinguish Scripture from interpretation and add a short uncertainty note where appropriate. "
                "Return labeled sections: Theme, Scripture, Reflection, Family Questions, Prayer, Uncertainty Note. "
                f"Theological profile: {self.profile.get('theologicalProfile', '')} "
                f"Family devotional notes: {' '.join(self.profile.get('familyDevotionalNotes', []))}"
            ),
        )
        user = (
            f"Actor: {actor}\n"
            f"Theme: {theme}\n"
            f"Context:\n{context or 'General family devotional preparation.'}"
        )
        return self.openai_client.prompt_text(system, user, max_output_tokens=520)
