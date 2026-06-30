# Epic 5 Slice 1: Search and Retrieval Proof

## Scope reviewed

- Main-repo search and retrieval truth posture in the default OpenAI response path.
- Companion capability wording where Jarvis explains what it can actually do.
- Regression coverage for truthful search claims, truthful local-context wording, and plain limitation wording when live retrieval is not wired.

## Object lanes reviewed

- Not applicable for this slice.

## Search and retrieval truth findings

1. The browser-search seam in `jarvis/openai_tasks.py` was wired, but the injected context label did not clearly prove that live search actually ran in the current turn.
2. The system prompt did not explicitly distinguish between:
   - real live web search that happened in this turn
   - local context only
   - plain reasoning without live retrieval
3. The grounded capability reply in `jarvis/companion_spine.py` did not describe the bounded web-search lane, which risked under-specifying the truth boundary for current-info asks.
4. Existing Epic 3 memory wording and Epic 4 object truth boundaries already stayed appropriately separate from live web search and were preserved.

## Bounded fixes made

1. Replaced the loose browser-search context label with a structured proof block in `jarvis/openai_tasks.py`:
   - `Search proof:`
   - explicit statement that live browser web search ran for this request
   - count of returned web result summaries in this turn
   - separate `Retrieved web context:` section
2. Added a search/retrieval truth rule to the injected system prompt when that proof block is present:
   - the model may describe search only when the proof block exists
   - otherwise it must not say it searched, found, looked up, or retrieved live web results
3. Added explicit bounded capability wording in `jarvis/companion_spine.py` so Jarvis now says it can use a web-search path for current info when that path is actually triggered, and that it will be explicit about whether it really searched or is reasoning from local context.
4. Added focused regression coverage for:
   - capability replies that do and do not include the web-search lane
   - browser-search proof formatting
   - system-prompt search truth guard presence and absence

## Tests run

```bash
python3 -m compileall jarvis/openai_tasks.py jarvis/companion_spine.py tests/test_companion_spine.py tests/test_openai_tasks_search_truth.py
python3 -m compileall tests/test_companion_spine.py tests/test_openai_tasks_search_truth.py
python3 -m pytest -q tests/test_companion_spine.py tests/test_openai_tasks_search_truth.py
python3 -m pytest -q tests/test_companion_spine.py tests/test_openai_tasks_search_truth.py
```

## Results

- `compileall`: passed
- `pytest`: `63 passed in 0.29s`

## Residual risks

1. This slice hardens the browser-search proof seam and the companion capability wording, but it does not yet audit every other possible future retrieval or tool pathway in the repo.
2. The search-proof count is summary-oriented, not provenance-heavy; it proves that the current path returned browser-search text, but it is not a full citation UI.
3. If new retrieval paths are added later without reusing this proof pattern, truth drift could reappear outside this bounded lane.

## Recommendation

Epic 5 slice 1 appears ready for Architect Office review. The main remaining work is broader Epic 5 surface auditing beyond this bounded search/retrieval seam, not additional changes inside this slice.
