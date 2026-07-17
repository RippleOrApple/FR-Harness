# FR-Harness Agent Log

Chronological records of skills, context, subagent work, human interventions, and lessons learned will be added here.

## 2026-07-16 — Task 1: package foundation and domain models

- Skills used: `using-git-worktrees`, `executing-plans`, `test-driven-development`.
- Context: implemented the approved Task 1 on isolated branch `setup-scaffold`; no subagent was used because the user requested current-session execution.
- RED evidence: `python -m pytest tests/test_models.py -v` initially could not import `fr_harness`; after installing local `pytest`, the same test failed with `ModuleNotFoundError: No module named 'fr_harness'`.
- GREEN evidence: `.venv\\Scripts\\python.exe -m pytest tests/test_models.py -v` passed with 2 tests.
- Human intervention: user selected package path `src/fr_harness/` over the generic `src/safepatch/` example.
- Lesson: project dependencies must be installed in the isolated virtual environment before a TDD red/green cycle can run.

## 2026-07-16 — Task 2: SQLite task and audit persistence

- Skills used: `executing-plans`, `test-driven-development`.
- RED evidence: `.venv\\Scripts\\python.exe -m pytest tests/test_db.py -v` failed because `Database` was not exported by `fr_harness.db`.
- GREEN evidence: the Task 2 tests passed (2 passed), then the full suite passed (4 passed).
- Implementation: SQLite now initializes `tasks`, `events`, `approvals`, and `memory_entries`; the completed public methods are task creation/read and ordered JSON audit event persistence.

## 2026-07-16 — Task 3: injectable LLM interfaces

- Skills used: `executing-plans`, `test-driven-development`.
- RED evidence: `.venv\\Scripts\\python.exe -m pytest tests/test_llm.py -v` failed because `MockLLM` and `OpenAICompatibleLLM` were absent.
- GREEN evidence: Task 3 tests passed (3 passed), then the full suite passed (7 passed).
- Implementation: `LLMClient` is a minimal protocol; MockLLM consumes deterministic action queues; the OpenAI-compatible client parses structured action JSON using an injected `httpx.Client` for offline tests.
