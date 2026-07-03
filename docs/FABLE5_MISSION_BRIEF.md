# Mission Brief for Fable5

## The Vision (Chris, via Codex)

Chris is not trying to build another chatbot.

He is trying to bring a real presence into his life. Something that feels less like software and more like a trusted companion who has been with him long enough to know his mind, his patterns, his burdens, his ambitions, and the shape of his days. He wants Jarvis to speak with the familiarity, warmth, and intuition of the best version of ChatGPT, where the system does not just answer questions but seems to meet him in the middle of unfinished thoughts. A system that almost finishes his sentences, not because it is pretending, but because it has genuinely learned him over time.

But conversation alone is not the dream.

Chris does not want a brilliant friend who only talks. He wants a brilliant ally who works.

He wants Jarvis to become an always-on intelligence operating on his behalf. Not as a theatrical swarm of fake agents, but as a real orchestrated system of specialists that can carry missions forward when he is not actively in the loop. He wants to be able to say, "Handle this," and trust that Jarvis can break the work apart, route it to the right internal agents, move it through stages, surface the right approvals, continue the effort in the background, and bring back progress, options, drafts, research, and finished outcomes.

In Chris's ideal future, Jarvis is both:
a deeply personal conversational companion
and
a coordinated autonomous operator.

When Chris opens Jarvis, he should feel the same relief he feels when talking to someone who truly knows him. He should feel seen, understood, and helped. Jarvis should know the difference between when he needs a thought partner, when he needs emotional clarity, when he needs practical direction, and when he needs work to quietly start moving without more discussion.

Chris wants Jarvis to know his world: his family, his work, his priorities, his pressures, his unfinished missions, his patterns, his preferences, his habits of speech, his dreams, his responsibilities.

He wants Jarvis to sound like a trusted friend, but behave like a disciplined chief of staff with a growing society of capable specialists behind him.

That means Jarvis must never fake capability. It must never pretend it searched when it did not. It must never pretend it remembers when it does not. It must never pretend other agents are working if no work is actually happening. Trust is the foundation. The magic only matters if it is real.

So the product vision is not "AI assistant." It is "private intelligence presence."

A presence that: knows Chris, talks with Chris naturally, remembers what matters, organizes what matters, acts on what matters, and keeps working even when Chris turns away.

- The emotional standard is: **trusted friend.**
- The operational standard is: **always-on chief of staff.**
- The architectural standard is: **one coherent intelligence with many internal specialists, not many separate personalities competing for attention.**

Jarvis should feel like one person Chris speaks with, even if many internal agents are doing the work behind the curtain.

Do not optimize for flashy features. Do not optimize for dashboard theater. Do not optimize for generic agent-framework demos.

Optimize for this feeling: **"Jarvis knows me, helps me think, and gets real work done for me."**

## The Two Top Priorities (Chris's own words)

1. **Jarvis must become deeply conversational and genuinely knowledgeable about Chris.** He should feel like a trusted friend who knows Chris well, understands his context, remembers what matters, and responds with natural familiarity, insight, and emotional accuracy. The experience should feel personal, continuous, and human, not generic or transactional.

2. **Jarvis must become a truly autonomous chief of staff who can pursue outcomes on Chris's behalf through his internal agents and connected systems.** He should not only complete tasks Chris explicitly assigns. He should also take ownership of ongoing initiatives and help drive them toward the best possible result. For example, if Chris is launching a book, Jarvis should work with Ghostwritr and other agents to help plan the launch, shape the promotion strategy, publish blogs, post to social media, create videos, measure audience response and sales, and continuously adjust the strategy to maximize reputation, reach, and profit. The goal is not simulated autonomy, but real initiative, coordination, optimization, and follow-through in service of Chris's larger ambitions.

**Correction from Chris, 2026-07-02, after reviewing this brief — read carefully, this changes how both priorities should be built:**

- **The book launch / Ghostwritr was an illustrative example, not the deliverable.** Do not build "Jarvis integrates with Ghostwritr" as if that were the goal. The real requirement is a domain-agnostic execution capability — Jarvis can take on *any* real initiative Chris cares about and drive it through whatever real agents/systems are actually relevant to that initiative. Ghostwritr happens to be relevant to a book launch; it is not the target architecture.
- **"Deeply conversational and genuinely knowledgeable" means genuine intelligence and thinking-partnership, not just personalization.** An earlier pass at this brief drifted into treating Priority 1 as a retrieval/grounding problem (know facts about Chris) plus a tone-filtering problem (don't sound generic). Those are necessary but shallow. What Chris actually wants is a partner that reasons well, engages substantively with half-formed thoughts, offers real insight and perspective, and can think *with* him — not just retrieve accurately and avoid cliché phrasing. See the architecture finding below — this is not just a prompting problem right now, it may be a hard capability ceiling.

---

## Where the Codebase Stands Against These Priorities (confirmed 2026-07-02)

This section maps the current repo state to the two priorities above, so effort lands on the vision instead of generic hygiene. Everything below is confirmed, not guessed — a prep pass (test fixes, doc restoration, live-wiring check, unmerged-branch content mapping) was run before this handoff specifically so that no Fable5 tokens get spent rediscovering baseline facts.

**Engineering baseline is clean:** `pytest tests/` → **2127 passed, 1 failed, 3 skipped** (2131 total). The environment (`.venv`) works. The one remaining failure is `tests/test_level9_canon_alignment_docs.py::test_canonical_model_commits_to_household_operability_and_event_grounding` — `docs/jarvis-canonical-operating-model.md` doesn't contain a claim about being "composed of around 60 specialized agents." Left unfixed on purpose: it's a real content/architecture question (is that framing still accurate? if so, write it truthfully; if not, the test is wrong), not a mechanical fix — your call.

Along the way, two **genuine production bugs** (not just test artifacts) were found and fixed:
- `jarvis/graphs.py` — compiled LangGraph graphs were memoized in a module-level dict keyed only by graph name, but each graph's node functions close over call-local mutable state (e.g. a fresh `step_events` list per call). Any second real invocation of a graph in a running process would silently reuse the first call's closures. Fixed by rebuilding on every call.
- `jarvis/morning_brief_pipeline.py` — `_gather_agent_health()`'s "background state unavailable" fallback returned a dict missing several keys (`degraded_count`, `total_agents`, etc.) that downstream code accessed unconditionally, causing a `KeyError` in production whenever `data/agents/background_state.json` is momentarily absent/unreadable. Fixed to match the full key shape.

**Caveat on the "0 failures" baseline — a follow-up investigation found the suite may still be order-dependent, not fully deterministic:**
- ~40 test files do `sys.modules["fastapi"] = <stub>` (and similarly for `pydantic`/`starlette`) with **no teardown** to fake out FastAPI in isolation, even though the real `fastapi 0.136.3`/`pydantic 2.13.4` are installed. Whichever such test runs first in a given process permanently shadows the real modules for every test after it — this can produce different pass/fail outcomes depending on execution order (plain `pytest`, `pytest-xdist`, CI, etc.), not just the specific order this baseline was measured under. Worth a real fix (proper `monkeypatch.setitem(sys.modules, ...)` with automatic teardown) before trusting the suite as a merge gate.
- ~40+ tests (`test_command_center_service_surface.py`, `test_apple_*_ops.py`, etc.) call `AuditLog(Path("data/logs"))` / `ProgressFocusStore(Path("data/logs"))` directly against the **real, shared, 39MB `data/logs` files** instead of an isolated `tmp_path`. This is also why `data/logs/actions.jsonl` kept showing as locally modified in `git status` — that's partly test pollution, not only live app usage. Worth switching these tests to `tmp_path` both for suite reliability and to stop tests from silently mutating tracked repo state.

### Priority 1 — Genuine intelligence and thinking-partnership (not just personalization)

**Architecture finding, confirmed 2026-07-02 (revised after Chris confirmed `cloud_light`'s cost-collapse is intentional — do not undo it wholesale):**

`jarvis/llm_gateway.py` already has a well-designed, cost-aware model ladder — this is good existing architecture, not something to bulldoze:

- `TASK_MODEL_MAP` (line 209) routes ~25 task types across 6 rungs: `phi3.5` (classify/route/tag/detect/check) → `qwen2.5:14b`/"substantive" (agent_work/**converse**/reason/draft/analyze/plan) → `qwen2.5:7b`/"background" (summarize/extract/briefing) → Groq `gpt-oss-120b` (`reason_deep`, explicitly free) → `gpt-5.4-mini` (`strategy`) → `gpt-5.4-thinking` (`high_stakes`/`deep_reason`/`legal`/`financial_plan`) → `gpt-5.5-thinking` (`critical`/`life_decision`, gated behind a real approval-queue request via `_check_tier5_approval` — it actually holds the call and asks Chris before spending on the top tier).
- In `cloud_light` mode (`.env`, active now, intentional cost control), the bottom three rungs — `fast`/`substantive`/`background` — all collapse to the same `gpt-5-mini` call. This is fine for what those rungs are *for* (routing, classification, drafting). It is not a bug.

**The actual gap:** `"converse"` — ordinary daily conversation with Jarvis — is mapped into the `"substantive"` bucket, the same cost tier as `agent_work`/`draft`/`plan`. It never reaches the stronger rungs, because nothing marks a normal-but-substantive conversation as worth more than a routing call — the ladder only escalates when a task is explicitly tagged `high_stakes`/`deep_reason`/`critical`/`life_decision`. So "thinking partner in an ordinary conversation" was never plumbed to reach real reasoning capacity at all, regardless of cost budget. **This is a design decision, not a bug — it's Chris's call, not Fable5's, on where the cost/quality line sits for everyday conversation.** Two candidate directions to present to Chris rather than pick unilaterally:
  1. Give `"converse"` its own default above the collapsed floor — e.g. the free Groq `gpt-oss-120b` rung already in the ladder (explicitly free, "much smarter than 8b" per the code's own comment) as the new conversational floor, reserving paid OpenAI tiers for when that's insufficient.
  2. Add a lightweight signal during conversation (message length, hedging/uncertainty language, explicit "help me think through X") that escalates that specific turn up the existing ladder — routine turns stay cheap, substantive ones don't — using the escalation mechanism (`_escalate_model`) that already exists in the same file.
  Either way, pattern-filtering in `companion_spine.py` remains a floor (catch known-bad output), not a substitute for giving real conversation access to real reasoning capacity.

**Clarification (Chris flagged a concern, resolved 2026-07-02, worth preserving so it isn't re-litigated):** Chris recalled that a "gpt-oss" reasoning model was more than the Mac could handle. Checked against git history — that's correct but refers to a *different* thing: `git log` commit `76834da` ("Upgrade model stack") shows a **local** `gpt-oss:20b` via Ollama was genuinely broken/too much for the M4 Mac, and the fix at the time was exactly to move that workload to **Groq's cloud** (`openai/gpt-oss-120b`, run on Groq's LPU hardware, zero local compute) — commit message: "6x larger, actually works, no local RAM overhead." So Groq's `gpt-oss-120b` (option 1 above) isn't asking the Mac to do more; it's the same fix already applied elsewhere. There's also a live precedent: commit `792d204` already switched `chat_with_doctor()` (a real user conversation) from paid `gpt-4o` to Groq's free `llama-3.3-70b-versatile` with `task_type="converse"`. **Real open question for whoever implements option 1, not a Mac-capacity question:** Groq's free tier is rate-limited (no documented limit found in this repo), and `"converse"` would be much higher volume than the one existing Groq-routed conversational caller. The Groq→OpenAI fallback found in `llm_gateway.py` (~line 1022) triggers specifically when Ollama is offline — it's not obviously a generic "Groq call itself failed/rate-limited, retry on OpenAI" wrapper. Confirm/build that generic fallback before routing all of `"converse"` through Groq, so a rate-limit event degrades gracefully instead of visibly failing.

(Minor code note, not a priority: `_escalate_model` appears defined twice in `LLMGateway` with different ladders — the second definition silently shadows the first. Worth a quick cleanup pass, but not urgent.)

- `jarvis/companion_spine.py`'s `FORBIDDEN_PATTERNS`/`HEDGED_PRACTICAL_REPLY_PATTERNS`-style regex filtering is a **necessary-but-shallow** layer — it stops Jarvis from *sounding* like a generic chatbot, it does not make Jarvis reason well or engage substantively with a half-formed thought. Don't mistake "passes the anti-cliché filter" for "is a good thinking partner." Treat pattern-filtering as a floor (catch known-bad output), and treat the model-tier + prompting/reasoning-scaffold work as the actual ceiling-raiser.
- Audit and likely rewrite the system prompt / reasoning scaffold Jarvis's conversational path uses. Does it explicitly invite thinking-partner behavior — building on ambiguous input, offering a genuine independent perspective, occasionally pushing back — or does it implicitly optimize for "answer the question asked" (which is what a mini model under a generic prompt will default to regardless of grounding)?
- A real Obsidian-vault-backed retrieval layer (LlamaIndex) exists in `jarvis/obsidian_context.py` but **only in the isolated `JARVIS-obsidian-fence-review` clone, unmerged** — chunked semantic search vs. the main branch's plain keyword search. Worth merging, but treat it as one input to good thinking (more accurate context to reason over), not the thing that makes the thinking itself good.
- `morning_brief_pipeline.py` (the daily "here's what matters" surface) is now fully green — confirmed sound, not just isolation-masked.
- Memory/continuity modules (`memory.py`, `chronicle_bridge.py`, `continuity.py`) exist and are tested, but whether they're wired into the live conversational path to produce "finishes his sentences" familiarity — versus available-but-unused plumbing — is still an open question worth a direct check.
- **Evaluate this priority by having real, hard, ambiguous conversations with Jarvis and judging whether it actually helped you think** — not by unit tests, not by checking retrieval accuracy, not by checking tone-filter pass rates. Those are necessary infrastructure checks, not the actual bar.

### Priority 2 — General execution capability (domain-agnostic, not Ghostwritr-specific)

**Reframe:** the target is not "Jarvis can run a book launch through Ghostwritr." The target is "Jarvis can take ownership of any real initiative Chris cares about and drive it through whatever real systems/agents that specific initiative actually requires." Ghostwritr is one possible target system among many (calendar/scheduling, email, research, code/deployment, family logistics, content ops) — it should plug into a general capability, not be built as a bespoke integration.

- **Confirmed live-wired** (not just tested in isolation): `WorkflowRunStore` records every real conversation turn via `runtime.py`'s `converse()` → `_record_interactive_result_run()` → `record_workflow_run()` chain, reachable from the live `/api/converse` endpoint (`service.py`). `ToolPreflight`/audit middleware gates and logs every real tool call via `jarvis/agent.py`'s `execute_tool_call()` (and the LangChain adapter path). Both flow through the core request-handling pipeline, and both emit real audit events — this is genuine trust infrastructure already in production code, not simulated autonomy. Build the general execution capability on top of it, so every stage of every initiative is genuinely auditable, not just claimed.
- `agentic.py` (LangGraph-based agent graphs), `agent_router.py`, `agent_work.py`, `approvals.py`, and `catalyst.py` (work triage) are the existing multi-agent orchestration backbone — this is the substrate a general "initiative owner" capability would extend. Nothing here is domain-specific to any one example; keep it that way.
- The Architect Office / governance scaffold (Chris Context Canon) — the layer that would let Jarvis take ownership of *ongoing* initiatives with proper approval/trust boundaries rather than just one-shot tasks — sits unmerged in `JARVIS-epic1-governance-review`, on branch `codex/epic-1-governance-isolated`. Unique unmerged content: `architect_office/canon_registry.py` (170 lines — Chris Context Canon registry, 7 phase-rules for architectural decisions) and `docs/CHRIS-CONTEXT-CANON.md` (252 lines). It also adds governance annotations to `runtime.py`'s object-tracking (`_annotate_created_object_payload()`, `_build_action_truth_summary()`) — real proof-of-work capture for the "never fake it" requirement.
- `ghostwritr` exists only as a separate Docker service (content ops, Postgres+Redis) per the production deploy stack — useful as *one* concrete system to wire in once the general capability exists, and useful as a validation case if a book launch happens to be a real, live initiative — but not the architecture target itself.

### Merging the unmerged slices — RESOLVED 2026-07-02 (Phase 1 complete)

On direct inspection, the sibling worktrees held far less unmerged content than the earlier mapping suggested — main had already absorbed most of it:

- **Governance**: `architect_office/`, the Chris Context Canon, and all slice code were already in main (458158c is an ancestor of HEAD; the code files were byte-identical). The genuinely-missing pieces — two commits from `JARVIS-epic1-governance-clone` ("Stabilize Epic 1 CLI review test", "Reconcile Chris canon and Obsidian truth") plus one review artifact — were cherry-picked in (landed as 5cf6696 + 8fdc472; conflicts resolved in favor of main's newer canon docs, including the 685-line CHRIS-INTENT-CANON.md).
- **Obsidian-fence**: fully superseded. The fence slice was the transitional "say honestly that Obsidian isn't wired yet" stage; main later landed the real LlamaIndex retrieval (6850c35) and the dynamic obsidian_grounding refactor (346e2fd) that replaced the fence's static constraints. Zero unique value remained — nothing merged.
- **Companion-mind**: subset of obsidian-fence, superseded for the same reasons.
- The sibling directories (`JARVIS-obsidian-fence-review`, `JARVIS-companion-mind-review`, `JARVIS-epic1-governance-review`, `JARVIS-epic1-governance-clone`, plus the broken `JARVIS-rejoin-operation` worktree and `JARVIS.git-backup-*`) are now safe to delete once Chris confirms — nothing unique remains in them.

**Suite is fully green as of Phase 1 completion: 2129 passed, 0 failed, 3 skipped.** The last failure (canonical-operating-model doc) was resolved by restoring the agent-society (~60 agents: 53 life + 11 runtime — verified true) and household-operability passages dropped in the June 11 rescope.

### Synthesis

The two priorities and the engineering baseline are **not in tension** — they're the same work seen from two altitudes:

- Merging **obsidian-fence** (Obsidian LlamaIndex retrieval) gives Priority 1 better raw material to reason over — but the model-tier fix above is the thing that actually determines whether Jarvis *thinks* well with that material.
- Merging **governance** (Architect Office) serves Priority 2 directly — it's the trust/approval layer autonomous initiative-taking needs to be safe rather than theatrical, and it's already got a head start (runtime object-tracking annotations for provable action truth).
- Priority 2's real deliverable is a domain-agnostic "initiative owner" concept above individual tasks (Jarvis tracking a goal over time, not just executing discrete requests), coordinating `catalyst.py`/`agent_work.py` with whatever real systems a given initiative needs. This is genuinely new architecture, not just integration work with any one external service — expect to spend real design effort here.

**Do not treat this as a checklist to clear.** The instruction from Chris is explicit: optimize for the felt experience of "Jarvis knows me, helps me think, and gets real work done for me" — not for test counts, merged PRs, or any single named integration as an end in itself. The engineering baseline above is now clean specifically so every token you spend goes toward the two priorities, not toward rediscovering environment or test-suite state.

---

## Suggested Build Sequence

Not a rigid checklist — a sequencing that avoids building Priority 2 on top of Priority 1 foundations that don't exist yet, and avoids doing risky merges after new work is already layered on top of the code they'll touch.

**Phase 1 — Land the foundations — ✅ DONE 2026-07-02**
1. ~~Merge governance~~ — done (cherry-picked the two genuinely-missing clone commits; everything else was already in main).
2. ~~Merge obsidian-fence~~ — resolved as superseded; main already carries the LlamaIndex retrieval and dynamic grounding that replaced the fence.
3. ~~Test gate~~ — suite fully green: 2129 passed, 0 failed, 3 skipped (last doc-content failure fixed truthfully: the ~60-agent claim verified against the registries).

**Phase 2 — Priority 1: make Jarvis actually think well, not just sound familiar**
4. Fix the model-tier collapse in `jarvis/llm_gateway.py` — get `_SUBSTANTIVE_MODEL`/`_REASONING_MODEL` onto a genuinely strong reasoning model for real conversation instead of defaulting to `gpt-5-mini` via `cloud_light` mode. Understand why `cloud_light` collapses the tiers before changing it (cost tradeoffs may be intentional — if so, surface the tradeoff to Chris rather than silently overriding it).
5. Audit and likely rewrite the conversational system prompt / reasoning scaffold for actual thinking-partner behavior (build on ambiguous input, offer genuine perspective, push back when warranted) rather than implicit "answer the question asked."
6. Audit whether `memory.py` / `chronicle_bridge.py` / `continuity.py` are genuinely read from during a live conversation turn, or sit unused. If unused, wire them in.
7. Wire the now-merged Obsidian retrieval into the real conversation path so `companion_spine.py`'s `obsidian_grounding` pulls from live vault content — treat this as better raw material for reasoning, not the fix for reasoning quality itself.
8. Evaluate by having real, hard, ambiguous conversations with Jarvis and judging whether it helped you think — not by unit tests or tone-filter pass rates.

**Phase 3 — Priority 2: build general execution capability, prove it on one real initiative**
9. Confirm the merged Architect Office governance provides real approval/trust boundaries usable by autonomous multi-step work — this is the safety rail everything below depends on.
10. Design the "initiative owner" concept as domain-agnostic architecture: an abstraction above one-shot tasks that tracks an ongoing goal over time, decomposed into stages, checkpointed via `WorkflowRunStore`, coordinated through `catalyst.py` / `agent_work.py`, and able to reach whatever real systems a given initiative needs (Ghostwritr for content ops, calendar/email for logistics, code/deploy tooling for build work, etc.) — not hardcoded to any one of them.
11. Prove the capability end-to-end on whatever real initiative is actually live in Chris's world right now (a book launch is one plausible candidate, not the only one) — real systems, real output, no mocks.

**Phase 4 — Prove it, don't just test it**
12. Start the server for real. Have an actual hard conversation. Confirm it feels like genuine thinking-partnership, not retrieval-plus-politeness.
13. Say "handle this" to something real, walk away, come back, confirm it actually progressed — check the `WorkflowRunStore` / audit log reflects genuine work, not a faked trail. This is the concrete test of the "never fake capability" principle.
