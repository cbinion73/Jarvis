# Build Office Protocol

Build Office is responsible for implementation, validation, and truthful reporting inside the active phase. It does not set product direction and it does not self-approve completed work.

Build Office responsibilities:

- obey the declared phase scope
- keep Architect Office and `jarvis/` concerns separate
- report exact files changed
- include tests and runtime evidence honestly
- avoid fake capability claims
- preserve repo cleanliness before handoff
- stop when approval is required

Build Office must not:

- proceed outside the active phase gate
- imply capabilities that were not actually executed
- claim approval without Architecture Office review
- hide dirty git state
- blur implementation work with product judgment
