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

## 2026-07-16 — OpenCode 冷启动验证（复验）

- Tool and context: another new OpenCode `--pure` session; only updated SPEC/PLAN copies from a second isolated temporary directory were attached.
- Result: OpenCode found no blocking ambiguity, correctly identified Task 4 path/approval tests and Task 6 context-role/recent-memory tests.
- Decision: cold-start gate is now complete; Task 4 may begin. The original sequencing deviation remains documented rather than concealed.

## 2026-07-16 — Task 4：治理护栏与一次性审批

- Skills used: `test-driven-development`.
- RED evidence: `tests/test_guardrails.py` first failed because `ApprovalStateMachine` and other guardrail interfaces were absent.
- GREEN evidence: Task 4 tests passed (6 passed); full suite passed (13 passed).
- Implementation: `resolve_workspace_path()` rejects `..` and resolved symlink escapes; action classification distinguishes allowed, blocked and approval-required actions; the in-memory approval state machine permits exactly one consume after approval and never after rejection.

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

## 2026-07-17 — Task 5：受限工具与 pytest 反馈解析

- Skills used: `planning-with-files`, `test-driven-development`.
- Process files: `temp/task-05/GOAL.md`, `task_plan.md`, `findings.md`, `progress.md`.
- RED evidence: the first run exposed missing interfaces; after adding only `NotImplementedError` skeletons, all 8 behavior tests failed for the expected unimplemented behavior.
- GREEN evidence: Task 5 tests passed (8 passed), then the full suite passed (21 passed).
- Implementation: UTF-8 reads/writes are workspace-confined; pytest always uses the fixed current-interpreter command with `shell=False`; feedback parses failed node IDs, combines both streams and caps summaries at 2,000 characters.

## 2026-07-17 — Task 6：记忆仓储与上下文构建

- Skills used: `planning-with-files`, `test-driven-development`.
- Process files: `temp/task-06/GOAL.md`, `task_plan.md`, `findings.md`, `progress.md`.
- RED evidence: after an import-only failure, minimal interfaces were introduced and all 3 behavior tests failed with `NotImplementedError`.
- GREEN evidence: Task 6 tests passed (3 passed), then the full suite passed (24 passed).
- Implementation: task memories are isolated and returned newest-first using the SQLite row id; Chat context has deterministic safety/memory/feedback/goal ordering; common key/token/secret assignments and OpenAI-style keys are redacted both before persistence and before injection.

## 2026-07-17 — Task 7：自建 Agent 主循环

- Skills used: `planning-with-files`, `test-driven-development`.
- Process files: `temp/task-07/GOAL.md`, `task_plan.md`, `findings.md`, `progress.md`.
- RED evidence: after adding an interface-only `Agent` skeleton, 6 behavior tests failed with `NotImplementedError`.
- GREEN evidence: Task 7 tests passed (6 passed), then the full suite passed (30 passed).
- Implementation: the handwritten loop persists state/iterations, builds context from durable events and memory, records redacted audit events, pauses dangerous actions, fails blocked/repeated/over-budget behavior, and only succeeds when `complete` follows passing pytest feedback.
- Boundary: Task 7 records an in-process approval request marker only; SQLite action persistence and post-decision resume are intentionally deferred to Task 8.

## 2026-07-17 — Task 8：持久化审批与恢复执行

- Skills used: `planning-with-files`, `test-driven-development`, `systematic-debugging`.
- Process files: `temp/task-08/GOAL.md`, `task_plan.md`, `findings.md`, `progress.md`.
- RED evidence: all 4 approval integration tests failed because the Database approval repository was absent.
- GREEN evidence: Task 8 approval tests passed (4 passed); regression selection passed (6 passed); the full suite passed (35 passed).
- Implementation: approval actions and decisions survive SQLite restart; `approved → consumed` is a conditional atomic update; resume executes only after obtaining that transition; rejected actions cancel without side effects; all lifecycle transitions are audited.
- Security: approval JSON is redacted before persistence via the shared `security.py` helper.
- Debugging lesson: the full suite exposed same-second, same-size Python rewrites reusing stale `.pyc`; evidence from audit outputs confirmed the second pytest still imported `wrong`. A red regression test now requires Python rewrites to advance the integer mtime cache key, restoring deterministic feedback repair.

## 2026-07-17 — Task 9：FastAPI 与三页极简 WebUI

- Skills used: `planning-with-files`, `test-driven-development`.
- Process files: `temp/task-09/GOAL.md`, `task_plan.md`, `findings.md`, `progress.md`.
- RED evidence: with only the application-factory skeleton present, all 5 initial route tests returned 404; the added key-display regression then failed by exposing its test secret.
- GREEN evidence: Web tests passed (6 passed), then the full suite passed cleanly (41 passed).
- Implementation: URL-encoded task creation validates an existing directory and runs synchronously to a stop; detail pages HTML-escape goal/workspace/audit JSON; pending approvals can be approved or rejected and return 303 after resume; task goals are redacted before SQLite persistence.
- Dependency note: current Starlette emits a deprecation warning for its httpx-backed TestClient; pytest suppresses only that exact upstream warning category/message so project test output remains clean.

## 2026-07-17 — Task 10：CLI、安全配置与 Docker 分发

- Skills used: `planning-with-files`, `test-driven-development`.
- Process files: `temp/task-10/GOAL.md`, `task_plan.md`, `findings.md`, `progress.md`.
- RED evidence: 4 tests failed because CLI symbols and Docker distribution content were absent.
- GREEN evidence: Task 10 tests passed (4 passed), then the full suite passed (45 passed).
- Implementation: `init` initializes SQLite, `serve` reads only the named environment settings and starts Uvicorn without echoing them, and `test` uses a fixed interpreter/pytest argument list with `shell=False`; container context excludes Git, env files, virtualenvs, caches, SQLite and process docs.
- Docker evidence: Docker Desktop Engine 29.6.1 was started in the background after the first daemon connection failed; `docker build -t fr-harness:local .` then completed successfully and produced `fr-harness:local` from `python:3.12-slim`.
