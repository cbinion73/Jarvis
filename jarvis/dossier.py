from __future__ import annotations

"""
JARVIS Dossier System
Builds fully-formed research dossiers using real web data.
Overnight agents dream, research, write — morning Chris reviews.
"""

import json
import logging
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .persistence import append_jsonl, atomic_write_jsonl

logger = logging.getLogger("jarvis.dossier")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Dossier dataclass
# ---------------------------------------------------------------------------

@dataclass
class Dossier:
    dossier_id: str
    work_id: str                         # links to AgentWorkStore WorkItem
    agent_id: str
    title: str
    status: str = "building"             # "building" | "ready" | "qa_failed" | "presented"
    executive_summary: str = ""
    market_opportunity: str = ""
    competitive_landscape: str = ""
    technical_requirements: str = ""
    revenue_model: str = ""
    risk_assessment: str = ""
    implementation_plan: str = ""        # 90-day concrete steps
    first_action: str = ""              # single thing Chris approves to start
    web_sources: list[str] = field(default_factory=list)      # URLs researched
    confidence_score: float = 0.0       # 0–10, based on quality/quantity of web data
    revenue_estimate_low: int = 0        # monthly USD
    revenue_estimate_high: int = 0       # monthly USD
    effort_hours: int = 0               # hours to build MVP
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    presented_at: str = ""
    session_id: str = ""                 # which party session built this
    build_log: list[str] = field(default_factory=list)  # step-by-step research notes
    # QA fields — populated by DossierQA adversarial review
    qa_passed: bool = True
    qa_issues: list[str] = field(default_factory=list)   # each failed check + critique
    qa_retries: int = 0                                   # total regeneration attempts


# ---------------------------------------------------------------------------
# DossierStore
# ---------------------------------------------------------------------------

class DossierStore:
    """
    Persists dossiers to ~/.jarvis/dossiers/dossiers.jsonl.
    All methods are thread-safe.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".jarvis" / "dossiers"
        base_dir.mkdir(parents=True, exist_ok=True)
        self._path = base_dir / "dossiers.jsonl"
        self._log_path = base_dir / "dossiers_log.jsonl"
        self._state_log_path = base_dir / "dossiers_state_log.jsonl"
        self._lock = threading.Lock()
        self._items: list[Dossier] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> list[Dossier]:
        if not self._path.exists():
            items = self._load_from_state_log()
            if items:
                return items
            return self._load_from_log()
        items = self._load_from_projection(self._path)
        if items:
            return items
        items = self._load_from_state_log()
        if items:
            return items
        return self._load_from_log()

    def _load_from_projection(self, path: Path) -> list[Dossier]:
        if not path.exists():
            return []
        items: list[Dossier] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    d = Dossier(
                        dossier_id=data.get("dossier_id", str(uuid.uuid4())),
                        work_id=data.get("work_id", ""),
                        agent_id=data.get("agent_id", ""),
                        title=data.get("title", ""),
                        status=data.get("status", "building"),
                        executive_summary=data.get("executive_summary", ""),
                        market_opportunity=data.get("market_opportunity", ""),
                        competitive_landscape=data.get("competitive_landscape", ""),
                        technical_requirements=data.get("technical_requirements", ""),
                        revenue_model=data.get("revenue_model", ""),
                        risk_assessment=data.get("risk_assessment", ""),
                        implementation_plan=data.get("implementation_plan", ""),
                        first_action=data.get("first_action", ""),
                        web_sources=data.get("web_sources", []),
                        confidence_score=float(data.get("confidence_score", 0.0)),
                        revenue_estimate_low=int(data.get("revenue_estimate_low", 0)),
                        revenue_estimate_high=int(data.get("revenue_estimate_high", 0)),
                        effort_hours=int(data.get("effort_hours", 0)),
                        created_at=data.get("created_at", _now_iso()),
                        updated_at=data.get("updated_at", _now_iso()),
                        presented_at=data.get("presented_at", ""),
                        session_id=data.get("session_id", ""),
                        build_log=data.get("build_log", []),
                        qa_passed=data.get("qa_passed", True),
                        qa_issues=data.get("qa_issues", []),
                        qa_retries=int(data.get("qa_retries", 0)),
                    )
                    items.append(d)
                except Exception:
                    pass
        except OSError:
            pass
        return items

    def _load_from_log(self) -> list[Dossier]:
        if not self._log_path.exists():
            return []
        latest: list[dict[str, Any]] = []
        try:
            for line in self._log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                items = payload.get("items")
                if isinstance(items, list):
                    latest = items
        except OSError:
            return []
        if not latest:
            return []
        temp_path = self._log_path.with_name(f"{self._log_path.stem}_replay.tmp")
        try:
            temp_path.write_text(
                "\n".join(json.dumps(item) for item in latest) + ("\n" if latest else ""),
                encoding="utf-8",
            )
            return self._load_from_projection(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _load_from_state_log(self) -> list[Dossier]:
        if not self._state_log_path.exists():
            return []
        latest: list[dict[str, Any]] = []
        try:
            for line in self._state_log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                items = payload.get("items")
                if isinstance(items, list):
                    latest = items
        except OSError:
            return []
        if not latest:
            return []
        temp_path = self._state_log_path.with_name(
            f"{self._state_log_path.stem}_replay.tmp"
        )
        try:
            temp_path.write_text(
                "\n".join(json.dumps(item) for item in latest) + ("\n" if latest else ""),
                encoding="utf-8",
            )
            return self._load_from_projection(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _flush(self) -> None:
        try:
            items = [asdict(d) for d in self._items]
            append_jsonl(
                self._log_path,
                {
                    "saved_at": _now_iso(),
                    "items": items,
                },
                ensure_ascii=False,
            )
            append_jsonl(
                self._state_log_path,
                {
                    "saved_at": _now_iso(),
                    "items": items,
                },
                ensure_ascii=False,
            )
            atomic_write_jsonl(self._path, items, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Failed to flush dossier store: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, dossier: Dossier) -> None:
        """Insert or update a dossier."""
        dossier.updated_at = _now_iso()
        with self._lock:
            for i, existing in enumerate(self._items):
                if existing.dossier_id == dossier.dossier_id:
                    self._items[i] = dossier
                    self._flush()
                    return
            self._items.append(dossier)
            self._flush()

    def get(self, dossier_id: str) -> Dossier | None:
        with self._lock:
            for d in self._items:
                if d.dossier_id == dossier_id:
                    return d
        return None

    def get_by_work_id(self, work_id: str) -> Dossier | None:
        with self._lock:
            for d in self._items:
                if d.work_id == work_id:
                    return d
        return None

    def get_ready(self) -> list[Dossier]:
        with self._lock:
            return [d for d in self._items if d.status == "ready"]

    def get_all(self) -> list[Dossier]:
        with self._lock:
            return list(self._items)

    def mark_presented(self, dossier_id: str) -> bool:
        with self._lock:
            for d in self._items:
                if d.dossier_id == dossier_id:
                    d.status = "presented"
                    d.presented_at = _now_iso()
                    d.updated_at = _now_iso()
                    self._flush()
                    return True
        return False

    def count_by_status(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for d in self._items:
                counts[d.status] = counts.get(d.status, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# DossierQA — adversarial critic agent
# ---------------------------------------------------------------------------

class DossierQA:
    """
    Adversarial reviewer that checks every generated section before it's
    accepted.  Every check is a binary PASS / FAIL verdict from a second
    independent LLM call.  Failed sections are returned with a critique so
    the generator can retry with the specific problem as context.

    Checks run:
      1. Section relevance  — does each section actually describe THIS business?
      2. First-action sanity — does the action make sense for the idea?
      3. Cross-section coherence — do exec-summary, comp-landscape, and first-
         action all describe the same product?
    """

    MAX_RETRIES = 2  # how many times a failed section can be regenerated

    def __init__(self, gateway: Any) -> None:
        self._gw = gateway

    def _ask(self, prompt: str) -> str:
        """Single binary QA call.  Returns raw LLM text, never raises."""
        if self._gw is None:
            return "PASS"
        try:
            result = self._gw.simple_complete(prompt, max_tokens=80, task_type="converse")
            return (result or "").strip()
        except Exception:
            return "PASS"   # fail-open: don't block on LLM errors

    # ------------------------------------------------------------------
    # Individual section check
    # ------------------------------------------------------------------

    # Sections where broad market/industry coverage is correct and expected.
    # These use a relevance prompt rather than a business-specificity prompt.
    _MARKET_SECTIONS = {"competitive landscape", "market opportunity"}

    def check_section(self, title: str, section_name: str, text: str) -> tuple[bool, str]:
        """
        Returns (passed, critique).
        critique is empty string when passed=True.

        Uses two different prompts:
          • Market/competitive sections  → checks relevance to the industry/market
          • Business-focused sections    → checks specificity to the business idea
        """
        if not text or len(text.strip()) < 30:
            return False, f"{section_name} is too short or empty."

        is_market_section = section_name.lower() in self._MARKET_SECTIONS

        if is_market_section:
            prompt = (
                f"You are a strict business analyst quality-checking an investment dossier.\n\n"
                f"Business idea: \"{title}\"\n"
                f"Section ({section_name}):\n\"{text[:400]}\"\n\n"
                f"Is this section relevant to the \"{title}\" industry and market? "
                f"A PASS means it discusses the correct industry, market players, or demand "
                f"context for \"{title}\". "
                f"A FAIL means it discusses a completely unrelated industry or market.\n\n"
                f"Reply with exactly one of:\n"
                f"PASS\n"
                f"FAIL: <one sentence explaining which unrelated industry it describes instead>"
            )
        else:
            prompt = (
                f"You are a strict business analyst quality-checking an investment dossier.\n\n"
                f"Business idea: \"{title}\"\n"
                f"Section ({section_name}):\n\"{text[:400]}\"\n\n"
                f"Does this section specifically describe the business \"{title}\"? "
                f"Or does it describe a completely different product, market, or industry?\n\n"
                f"Reply with exactly one of:\n"
                f"PASS\n"
                f"FAIL: <one sentence explaining the specific problem>"
            )

        verdict = self._ask(prompt)
        if verdict.upper().startswith("PASS"):
            return True, ""
        # Extract critique after "FAIL:"
        critique = verdict
        if ":" in verdict:
            critique = verdict.split(":", 1)[1].strip()
        return False, critique or f"{section_name} did not pass relevance check."

    # ------------------------------------------------------------------
    # First-action sanity check
    # ------------------------------------------------------------------

    def check_first_action(self, title: str, first_action: str) -> tuple[bool, str]:
        """Verifies the first action is grounded in the actual business idea."""
        if not first_action or len(first_action.strip()) < 10:
            return False, "First action is missing or too vague."

        prompt = (
            f"Business idea: \"{title}\"\n"
            f"Proposed first action: \"{first_action}\"\n\n"
            f"Is this first action directly relevant to starting \"{title}\"? "
            f"Or does it reference a completely different business, person, or industry?\n\n"
            f"Reply with exactly one of:\n"
            f"PASS\n"
            f"FAIL: <one sentence explaining the problem>"
        )
        verdict = self._ask(prompt)
        if verdict.upper().startswith("PASS"):
            return True, ""
        critique = verdict.split(":", 1)[1].strip() if ":" in verdict else verdict
        return False, critique or "First action is not relevant to this business idea."

    # ------------------------------------------------------------------
    # Cross-section coherence check
    # ------------------------------------------------------------------

    def check_coherence(self, title: str, dossier: "Dossier") -> tuple[bool, list[str]]:
        """
        Checks that executive summary, competitive landscape, and first action
        all describe the same coherent business.
        Returns (passed, list_of_issues).
        """
        issues: list[str] = []

        prompt = (
            f"You are checking internal consistency of an investment dossier.\n\n"
            f"Title: \"{title}\"\n"
            f"Executive Summary: \"{(dossier.executive_summary or '')[:250]}\"\n"
            f"Competitive Landscape: \"{(dossier.competitive_landscape or '')[:200]}\"\n"
            f"First Action: \"{(dossier.first_action or '')[:150]}\"\n\n"
            f"Do all three sections describe the same coherent business as \"{title}\"? "
            f"Reply with exactly one of:\n"
            f"PASS\n"
            f"FAIL: <one sentence naming which section(s) are inconsistent and why>"
        )
        verdict = self._ask(prompt)
        if not verdict.upper().startswith("PASS"):
            critique = verdict.split(":", 1)[1].strip() if ":" in verdict else verdict
            issues.append(f"Coherence: {critique}")

        return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# DossierBuilder
# ---------------------------------------------------------------------------

class DossierBuilder:
    """Builds a fully-formed research dossier for a WorkItem using web research + LLM."""

    def __init__(self, gateway: Any, timeout_ms: int = 12000) -> None:
        self.gateway = gateway
        self.timeout_ms = timeout_ms
        self._qa = DossierQA(gateway)

    def build(self, work_item: Any, session_id: str = "") -> Dossier:
        """
        Full pipeline — returns a completed Dossier.

        Pipeline:
          1. Web research (Wikipedia API)
          2. Generate each section with LLM
          3. DossierQA adversarial check on every section
             — failed sections are regenerated with critique as context
             — max DossierQA.MAX_RETRIES attempts per section
          4. Cross-section coherence check
          5. Revenue extraction + confidence score
        """
        title = getattr(work_item, "title", "Unknown Idea")
        work_id = getattr(work_item, "work_id", str(uuid.uuid4()))
        agent_id = getattr(work_item, "agent_id", "mantis")

        dossier = Dossier(
            dossier_id=str(uuid.uuid4()),
            work_id=work_id,
            agent_id=agent_id,
            title=title,
            status="building",
            session_id=session_id,
        )

        def _log(msg: str) -> None:
            ts = datetime.now(timezone.utc).strftime("%H:%M")
            entry = f"{ts} — {msg}"
            dossier.build_log.append(entry)
            logger.debug("[dossier] %s", msg)

        _log(f"Starting dossier build for: {title}")

        # ------------------------------------------------------------------
        # 1. Web research
        # ------------------------------------------------------------------
        _search = None
        _fetch = None
        try:
            from .browser_search import search as _s, fetch_page_text as _f
            _search = _s
            _fetch = _f
            _log("Browser search available — using Wikipedia API")
        except Exception as exc:
            _log(f"Browser search unavailable ({exc}) — LLM-only mode")

        _words = [w for w in title.split() if len(w) > 3 and w.lower() not in
                  ('with','that','this','from','have','will','into','your')]
        _core = " ".join(_words[:4]) if _words else title[:30]

        search_queries = [
            f"{_core} market size revenue",
            f"{_core} software business SaaS",
            f"passive income {_core} developer",
            f"{_core} startup founder",
            f"{_core} competitors alternatives",
        ]

        web_sources: list[str] = []
        corpus_snippets: list[str] = []

        if _search is not None and _fetch is not None:
            for query in search_queries:
                try:
                    _log(f"Searching: {query[:60]}…")
                    results = _search(query, num_results=3)
                    if results:
                        top = results[0]
                        url = top.url if hasattr(top, "url") else str(top)
                        if url and url not in web_sources:
                            web_sources.append(url)
                            try:
                                page_text = _fetch(url)
                                snippet = (page_text or "").strip()[:600]
                                if snippet:
                                    corpus_snippets.append(f"[SOURCE: {url}]\n{snippet}")
                                    _log(f"Fetched content from {url[:50]}… ({len(snippet)} chars)")
                            except Exception as fetch_exc:
                                _log(f"Could not fetch {url[:50]}: {fetch_exc}")
                        for r in results[1:3]:
                            extra_url = r.url if hasattr(r, "url") else str(r)
                            if extra_url and extra_url not in web_sources:
                                web_sources.append(extra_url)
                except Exception as search_exc:
                    _log(f"Search failed for '{query[:40]}': {search_exc}")
        else:
            _log("Skipping web search — no browser available")

        dossier.web_sources = web_sources
        research_corpus = "\n\n".join(corpus_snippets) if corpus_snippets else ""
        corpus_preview = research_corpus[:2000] if research_corpus else "(no web data — use general knowledge)"
        work_item_context_parts = [
            f"Idea: {str(getattr(work_item, 'idea', '')).strip()}",
            f"Research notes: {str(getattr(work_item, 'research', '')).strip()}",
            f"Proposal: {str(getattr(work_item, 'proposal', '')).strip()}",
        ]
        work_item_context = "\n".join(part for part in work_item_context_parts if not part.endswith(": "))
        _log(f"Corpus: {len(corpus_snippets)} snippets, {len(web_sources)} sources")

        # ------------------------------------------------------------------
        # 2. LLM generation helpers
        # ------------------------------------------------------------------
        gw = self.gateway

        def _complete(prompt: str, max_tokens: int = 400) -> str:
            if gw is None:
                return ""
            for attempt in range(2):
                try:
                    result = gw.simple_complete(prompt, max_tokens=max_tokens, task_type="converse")
                    if result and result.strip():
                        return result.strip()
                except Exception as exc:
                    _log(f"LLM call failed (attempt {attempt+1}): {exc}")
            return ""

        ctx = corpus_preview[:1200] if corpus_preview else "(use your general knowledge)"
        if work_item_context:
            ctx = f"{ctx}\n\nStored work-item context:\n{work_item_context[:800]}"

        # ------------------------------------------------------------------
        # 3. Generate + QA each section with retry loop
        # ------------------------------------------------------------------
        def _generate_and_verify(
            section_name: str,
            base_prompt: str,
            max_tokens: int = 400,
        ) -> str:
            """
            Generate a section, run QA, retry with critique if it fails.
            Returns the best text produced (even if QA still fails after retries).
            """
            critique = ""
            text = ""
            for attempt in range(DossierQA.MAX_RETRIES + 1):
                if attempt == 0:
                    prompt = base_prompt
                else:
                    # Retry: prepend critique so the LLM knows what was wrong
                    prompt = (
                        f"[QA REJECTION — attempt {attempt}]\n"
                        f"The previous answer was rejected by the quality reviewer.\n"
                        f"Problem: {critique}\n\n"
                        f"Fix this issue and rewrite the {section_name} specifically "
                        f"for the business idea \"{title}\". Do NOT describe a different product.\n\n"
                        + base_prompt
                    )
                    dossier.qa_retries += 1

                text = _complete(prompt, max_tokens=max_tokens)
                if not text:
                    _log(f"  QA: {section_name} — empty response, skipping check")
                    break

                passed, critique = self._qa.check_section(title, section_name, text)
                if passed:
                    if attempt > 0:
                        _log(f"  QA: {section_name} PASSED on retry {attempt}")
                    break
                else:
                    _log(f"  QA: {section_name} FAILED — {critique[:80]}")
                    if attempt < DossierQA.MAX_RETRIES:
                        _log(f"  QA: regenerating {section_name} (attempt {attempt+1}/{DossierQA.MAX_RETRIES})…")
                    else:
                        # Exhausted retries — flag but keep best text
                        issue = f"{section_name}: {critique}"
                        dossier.qa_issues.append(issue)
                        dossier.qa_passed = False
                        _log(f"  QA: {section_name} failed all {DossierQA.MAX_RETRIES} retries — flagged")

            return text

        _log("Generating + verifying: market opportunity…")
        dossier.market_opportunity = _generate_and_verify(
            "Market Opportunity",
            f"Research context:\n{ctx}\n\n"
            f"Write a 120-word market opportunity for '{title}'. "
            f"Include market size, growth rate, and 2-3 demand signals. "
            f"Use specific numbers. Every sentence must be about '{title}'.",
        )

        _log("Generating + verifying: competitive landscape…")
        dossier.competitive_landscape = _generate_and_verify(
            "Competitive Landscape",
            f"Research context:\n{ctx}\n\n"
            f"Write a 120-word competitive landscape for '{title}'. "
            f"Name 3-4 specific competitors in the '{title}' market, their pricing, "
            f"and one gap a new entrant could exploit. "
            f"Only name competitors that operate in this specific market.",
        )

        _log("Generating + verifying: technical requirements…")
        dossier.technical_requirements = _generate_and_verify(
            "Technical Requirements",
            f"Write technical requirements to build '{title}' as a solo developer. "
            f"Cover: stack (languages/frameworks), key APIs, hosting, estimated MVP hours. "
            f"120 words max. Context: {work_item_context[:400]}",
        )

        _log("Generating + verifying: revenue model…")
        dossier.revenue_model = _generate_and_verify(
            "Revenue Model",
            f"Write a revenue model for '{title}'. "
            f"Give: pricing (e.g. $X/mo per customer), realistic customer counts at "
            f"3mo/6mo/12mo, and projected MRR at month 12. Show math. 120 words. "
            f"Context: {work_item_context[:300]}",
        )

        _log("Generating + verifying: risk assessment…")
        dossier.risk_assessment = _generate_and_verify(
            "Risk Assessment",
            f"List 4 key risks for '{title}' with one mitigation each. "
            f"Cover: market, technical, competition, execution. Be specific to this idea. "
            f"120 words max.",
        )

        _log("Generating + verifying: 90-day implementation plan…")
        dossier.implementation_plan = _generate_and_verify(
            "Implementation Plan",
            f"Write a 90-day plan to launch '{title}'. "
            f"Days 1-30: validate + design. Days 31-60: build MVP. "
            f"Days 61-90: launch + first customers. "
            f"3-4 concrete deliverables per phase specific to '{title}'. 150 words max.",
        )

        _log("Generating + verifying: first action…")
        dossier.first_action = _generate_and_verify(
            "First Action",
            f"What is the ONE thing Chris Binion should do TODAY to start '{title}'? "
            f"One sentence, specific to this business, actionable. No fluff.",
            max_tokens=100,
        )
        # Extra dedicated check for first action sanity
        if dossier.first_action:
            fa_ok, fa_critique = self._qa.check_first_action(title, dossier.first_action)
            if not fa_ok:
                _log(f"  QA: First Action sanity FAILED — {fa_critique}")
                dossier.qa_issues.append(f"First Action: {fa_critique}")
                dossier.qa_passed = False
                # One more regeneration attempt with explicit guidance
                dossier.first_action = _complete(
                    f"[QA REJECTION] The first action was rejected: {fa_critique}\n"
                    f"Write ONE specific, actionable first step to start the business '{title}'. "
                    f"It must be directly about '{title}' — nothing else.",
                    max_tokens=100,
                )
                dossier.qa_retries += 1

        _log("Building executive summary (final — uses verified sections)…")
        mkt  = (dossier.market_opportunity  or "")[:200]
        rev  = (dossier.revenue_model       or "")[:200]
        tech = (dossier.technical_requirements or "")[:150]
        dossier.executive_summary = _generate_and_verify(
            "Executive Summary",
            f"Write a 3-sentence executive summary for '{title}'.\n"
            f"Sentence 1: What '{title}' is (describe this specific product). "
            f"Sentence 2: Market opportunity with numbers. "
            f"Sentence 3: Revenue potential and effort.\n\n"
            f"Data — Market: {mkt} | Revenue: {rev} | Tech: {tech}",
            max_tokens=200,
        )

        # ------------------------------------------------------------------
        # 4. Cross-section coherence check
        # ------------------------------------------------------------------
        _log("Running cross-section coherence check…")
        coherent, coherence_issues = self._qa.check_coherence(title, dossier)
        if not coherent:
            for issue in coherence_issues:
                _log(f"  QA coherence: {issue}")
                dossier.qa_issues.append(issue)
            dossier.qa_passed = False
            _log(f"  QA: coherence check FAILED — {len(coherence_issues)} issue(s)")
        else:
            _log("  QA: coherence check PASSED")

        # ------------------------------------------------------------------
        # 5. Revenue extraction
        # ------------------------------------------------------------------
        _log("Extracting revenue estimates…")
        revenue_raw = dossier.revenue_model
        if revenue_raw and gw is not None:
            try:
                extract_prompt = (
                    f"From this revenue model text, extract the monthly revenue estimates.\n\n"
                    f"Text: {revenue_raw[:800]}\n\n"
                    f"Return ONLY a JSON object: {{\"low\": 500, \"high\": 3000}}\n"
                    f"Where low = conservative monthly USD, high = optimistic monthly USD. "
                    f"No explanation."
                )
                raw = gw.simple_complete(extract_prompt, max_tokens=100, task_type="converse")
                raw = (raw or "").strip()
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    parsed = json.loads(raw[start:end])
                    dossier.revenue_estimate_low  = int(parsed.get("low", 0))
                    dossier.revenue_estimate_high = int(parsed.get("high", 0))
                    _log(f"Revenue: ${dossier.revenue_estimate_low:,}–${dossier.revenue_estimate_high:,}/mo")
            except Exception as exc:
                _log(f"Revenue parse failed: {exc}")
                amounts = re.findall(r"\$[\d,]+", revenue_raw)
                nums = []
                for a in amounts:
                    try:
                        nums.append(int(a.replace("$","").replace(",","")))
                    except ValueError:
                        pass
                if len(nums) >= 2:
                    nums.sort()
                    dossier.revenue_estimate_low  = nums[0]
                    dossier.revenue_estimate_high = nums[-1]

        if dossier.technical_requirements:
            hour_matches = re.findall(r"(\d+)\s*(?:hours?|hrs?)", dossier.technical_requirements, re.IGNORECASE)
            if hour_matches:
                try:
                    dossier.effort_hours = int(hour_matches[0])
                except ValueError:
                    pass

        # ------------------------------------------------------------------
        # 6. Confidence score (0–10), penalised for QA failures
        # ------------------------------------------------------------------
        source_count = len(web_sources)
        all_text = " ".join(filter(None, [
            dossier.market_opportunity, dossier.competitive_landscape,
            dossier.technical_requirements, dossier.revenue_model,
            dossier.risk_assessment, dossier.implementation_plan,
        ]))
        has_dollar_numbers = bool(re.search(r"\$[\d,]+", all_text))
        has_pct_numbers    = bool(re.search(r"\d+%", all_text))
        has_time_numbers   = bool(re.search(r"\d+\s*(month|week|day|hour)", all_text, re.I))
        has_web_data       = len(corpus_snippets) > 0

        web_score     = min(3.0, source_count * 0.75)
        filled        = sum(1 for s in [
            dossier.market_opportunity, dossier.competitive_landscape,
            dossier.technical_requirements, dossier.revenue_model,
            dossier.risk_assessment, dossier.implementation_plan,
        ] if len(s or "") > 50)
        content_score = min(4.0, filled * 0.67)
        data_bonus    = (
            (1.0 if has_dollar_numbers else 0.0)
            + (0.5 if has_pct_numbers else 0.0)
            + (0.5 if has_time_numbers else 0.0)
            + (1.0 if has_web_data else 0.0)
        )
        raw_score = min(10.0, web_score + content_score + data_bonus)

        # QA penalty: each unresolved issue costs 1 point, max -3
        qa_penalty = min(3.0, len(dossier.qa_issues) * 1.0)
        dossier.confidence_score = round(max(0.0, raw_score - qa_penalty), 1)

        qa_summary = (
            f"QA: PASSED (retries={dossier.qa_retries})" if dossier.qa_passed
            else f"QA: {len(dossier.qa_issues)} issue(s) flagged (retries={dossier.qa_retries})"
        )
        _log(f"Confidence score: {dossier.confidence_score:.1f}/10 — {qa_summary}")

        # ------------------------------------------------------------------
        # 7. Finalize
        # ------------------------------------------------------------------
        dossier.status = "ready"
        dossier.updated_at = _now_iso()
        _log(f"Dossier complete: {title}")

        return dossier


# ---------------------------------------------------------------------------
# Module-level singleton store
# ---------------------------------------------------------------------------

_dossier_store: DossierStore | None = None
_store_lock = threading.Lock()


def get_dossier_store() -> DossierStore:
    global _dossier_store
    with _store_lock:
        if _dossier_store is None:
            _dossier_store = DossierStore()
        return _dossier_store


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def build_dossier_for_work_item(work_item: Any, gateway: Any, session_id: str = "") -> Dossier:
    """Build and save a dossier for the given WorkItem. Returns the completed Dossier."""
    builder = DossierBuilder(gateway)
    dossier = builder.build(work_item, session_id=session_id)
    store = get_dossier_store()
    store.save(dossier)
    return dossier
