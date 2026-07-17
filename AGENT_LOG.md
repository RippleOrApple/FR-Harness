# FR-Harness Agent Log

Chronological records of skills, context, subagent work, human interventions, and lessons learned will be added here.

## 2026-07-16 — Repository layout revision

- Human intervention: move the active branch from the nested `.worktrees/` directory to the `FR-Harness` root and keep substantive documents in root `SPEC.md` and `PLAN.md`.
- Decision: delete the `docs/` copies after migrating their full contents to root documents; preserve the existing implementation commits and do not modify the untracked `A任务完成指南.md` in the original checkout.

## 2026-07-16 — 冷启动验证流程补正

- Human intervention: user identified that the required unfamiliar-agent cold-start verification was missing from the implementation-before gate in `PLAN.md`.
- Decision: add it as a mandatory gate before Task 4, with the required isolated-session, documents-only, pause-on-uncertainty, and before/after-diff evidence requirements. Tasks 1–3 were already implemented; the later `SPEC_PROCESS.md` entry must disclose this sequencing deviation honestly.

## 2026-07-16 — OpenCode 冷启动验证（第一次）

- Tool and context: OpenCode CLI 1.17.18, `nju/deepseek-v4-flash`, new `--pure` session; only copied root `SPEC.md` and `PLAN.md` were attached from an isolated temporary directory.
- Result: OpenCode correctly summarized Task 4/6 but stopped with 10 questions about missing type/schema/interface details. This was valid evidence that the specifications were insufficient.
- Human-owned correction: added normative definitions to SPEC §5.1, detailed Task 4/6 implementation contracts in PLAN, and recorded the before/after differences in `SPEC_PROCESS.md`. A second clean verification is required before Task 4.

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
