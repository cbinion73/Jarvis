from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REQUIRED_SECTIONS = (
    "## A. Start State",
    "## B. Scope",
    "## C. Files Changed",
    "## D. Tests / Validation",
    "## E. Runtime Evidence",
    "## F. Truthfulness / Safety",
    "## G. Risks / Limitations",
    "## H. Commit",
    "## I. Ready for Architecture Review",
)


@dataclass(frozen=True)
class ReportCheckResult:
    path: Path
    exists: bool
    missing_sections: list[str]
    present_sections: list[str]
    text: str

    @property
    def complete(self) -> bool:
        return self.exists and not self.missing_sections


def check_report(report_path: str | Path) -> ReportCheckResult:
    path = Path(report_path)
    if not path.exists():
        return ReportCheckResult(
            path=path,
            exists=False,
            missing_sections=list(REQUIRED_SECTIONS),
            present_sections=[],
            text="",
        )

    text = path.read_text(encoding="utf-8")
    present_sections = [section for section in REQUIRED_SECTIONS if section in text]
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in text]
    return ReportCheckResult(
        path=path,
        exists=True,
        missing_sections=missing_sections,
        present_sections=present_sections,
        text=text,
    )
