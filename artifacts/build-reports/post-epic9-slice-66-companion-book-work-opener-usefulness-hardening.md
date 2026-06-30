# Post-Epic 9 Slice 66: Companion Book-Work Opener Usefulness Hardening

Ready for Architect Office review: yes

## Exact prompts tested

Repo-truth defect prompts:
- `I need help with my book.`
- `I need to write my book.`
- `I need help outlining my book.`
- `I'm stuck on my book.`
- `I need to revise my book.`
- `Help me with this book chapter.`

Existing in-bounds prompts rechecked:
- `Help me work on my latest book.`
- `I need to work on my book.`

Nearby non-book control:
- `I need help writing this article.`

## Whether a defect was found

Yes.

The standalone book-work opener only caught:
- `latest book`
- `book` plus `work on`

That meant nearby natural book-writing asks were falling through to the generic practical fallback:
- `I need help with my book.`
- `I need to write my book.`
- `I need help outlining my book.`
- `I'm stuck on my book.`
- `I need to revise my book.`
- `Help me with this book chapter.`

After the bounded repair, all of those prompts now route to the existing book-work fork:

`Good. What's the book, and do you need help outlining, writing, revising, or getting unstuck?`

## Exact code/tests changed

Code change:
- [jarvis/companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/jarvis/companion_spine.py:380)
  - Expanded the standalone book-work opener matcher just enough to include:
    - `book chapter`
    - `help with my book`
    - `write my book`
    - `outline my book`
    - `outlining my book`
    - `stuck on my book`
    - `revise my book`
    - `revising my book`
  - Kept the change inside the existing first-turn companion opener branch only.

Test changes:
- [tests/test_companion_spine.py](/Users/chris/Desktop/CODE/JARVIS/tests/test_companion_spine.py:1651)
  - Added focused opener tests for:
    - `I need help with my book.`
    - `I need to write my book.`
    - `I need help outlining my book.`
    - `I'm stuck on my book.`
    - `I need to revise my book.`
    - `Help me with this book chapter.`
  - Added one nearby non-book control:
    - `I need help writing this article.`

## Exact verification commands run

```bash
python3 -m py_compile jarvis/companion_spine.py tests/test_companion_spine.py
python3 -m pytest -q tests/test_companion_spine.py -k "help_with_my_book_prompt_gets_book_work_fork or write_my_book_prompt_gets_book_work_fork or outline_my_book_prompt_gets_book_work_fork or stuck_on_my_book_prompt_gets_book_work_fork or revise_my_book_prompt_gets_book_work_fork or book_chapter_prompt_gets_book_work_fork or article_prompt_does_not_get_book_work_fork"
python3 - <<'PY'
from jarvis.companion_spine import generate_companion_fallback
packet = {"available_capabilities": ["ongoing conversation in this shell", "conversation turn persistence"]}
prompts = [
    "I need help with my book.",
    "I need to write my book.",
    "I need help outlining my book.",
    "I'm stuck on my book.",
    "I need to revise my book.",
    "Help me with this book chapter.",
    "Help me work on my latest book.",
    "I need to work on my book.",
    "I need help writing this article.",
]
for prompt in prompts:
    print(f"PROMPT: {prompt}\nREPLY: {generate_companion_fallback(prompt, packet)}\n")
PY
```

## Verification results

- `py_compile`: passed
- focused pytest: `7 passed, 191 deselected`
- in-process smoke:
  - all six repaired book-work prompts now hit the book-work fork
  - existing in-bounds prompts still hit the same fork
  - `I need help writing this article.` stays out of the book-work fork and continues to use the generic practical fallback

## Recommendation

Approve.

This slice repairs the exact repo-truth defect in the standalone book-work opener without widening into generic writing help or broader authoring behavior. A separate acceptance pass would be the right next bounded move if Architect Office wants to probe for any remaining nearby book-opener aliases.
