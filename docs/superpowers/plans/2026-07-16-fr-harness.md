# FR-Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python coding-agent harness that safely edits a constrained Python workspace, runs pytest, feeds objective failures back to an LLM, and pauses dangerous actions for WebUI approval.

**Architecture:** A FastAPI process owns the task API and minimal HTML UI. `Agent.run_once()` is the self-built control loop: it reads persisted task state, calls an injected LLM, validates an action, applies guardrails, dispatches a tool, persists audit events, and returns a state transition. SQLite stores tasks, approvals, memory, and events; MockLLM makes all core mechanisms deterministic offline.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic v2, SQLite (`sqlite3`), pytest, httpx, python-dotenv, Docker.

## Global Constraints

- Support Python workspaces only; objective repair feedback comes from `pytest`.
- Do not use LangChain, AutoGen, CrewAI, LlamaIndex Agent, or any prebuilt agent loop.
- All action schemas and core mechanisms must be testable with `MockLLM` and no network access.
- All filesystem paths must resolve inside each task's configured workspace root.
- API keys must never be persisted in SQLite, source code, audit events, or response bodies.
- Default maximum loop count is 8; repeated identical actions fail a task after 2 repeats.
- Dangerous actions require an explicit, one-time user approval before execution.
- Keep the first release single-process and single-task-at-a-time; do not add queues or subagents.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `pyproject.toml` | package metadata, runtime/test dependencies, pytest configuration |
| `src/fr_harness/models.py` | enums and Pydantic models for tasks, actions, feedback, approvals, events |
| `src/fr_harness/db.py` | SQLite connection, schema initialization, repositories |
| `src/fr_harness/llm.py` | LLM protocol, MockLLM, OpenAI-compatible HTTP adapter |
| `src/fr_harness/guardrails.py` | path containment and approval state rules |
| `src/fr_harness/tools.py` | constrained read/write/pytest tool dispatcher |
| `src/fr_harness/feedback.py` | pytest result conversion to a compact deterministic feedback object |
| `src/fr_harness/memory.py` | project conventions and failed-attempt lookup/write operations |
| `src/fr_harness/agent.py` | self-built one-step Agent control loop and stop policy |
| `src/fr_harness/web.py` | FastAPI API and three minimal HTML pages |
| `src/fr_harness/cli.py` | `init`, `serve`, `test` commands |
| `tests/` | isolated unit and API tests; no test calls an external LLM |
| `demo/mock_repair_demo.py` | reproducible end-to-end MockLLM mechanism demonstration |
| `Dockerfile`, `.dockerignore` | reproducible container distribution |
| `.gitlab-ci.yml` | required `unit-test` CI job |
| `README.md` | setup, safe credential configuration, tests, Docker, limitations |

## Task 1: Create package foundation and domain models — completed; see `AGENT_LOG.md`

**Files:**
- Create: `pyproject.toml`
- Create: `src/fr_harness/__init__.py`
- Create: `src/fr_harness/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces `TaskStatus`, `ActionKind`, `ApprovalDecision`, `Action`, `Task`, `Feedback`, and `ToolResult` for all later tasks.

- [x] **Step 1: Write the failing model tests**

```python
from fr_harness.models import Action, ActionKind, TaskStatus

def test_action_requires_payload_for_write_file() -> None:
    action = Action(kind=ActionKind.WRITE_FILE, path="app.py", content="print('ok')")
    assert action.path == "app.py"
    assert action.content == "print('ok')"

def test_task_status_has_pending_approval() -> None:
    assert TaskStatus.PENDING_APPROVAL.value == "pending_approval"
```

- [x] **Step 2: Run the tests to verify failure**

Run: `python -m pytest tests/test_models.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'fr_harness'`.

- [x] **Step 3: Add package metadata and minimal models**

```toml
[project]
name = "fr-harness"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn>=0.30", "pydantic>=2.9", "httpx>=0.27", "python-dotenv>=1.0"]

[project.optional-dependencies]
dev = ["pytest>=8.3"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/fr_harness/models.py
from enum import StrEnum
from pydantic import BaseModel

class TaskStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ActionKind(StrEnum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    RUN_PYTEST = "run_pytest"
    REQUEST_APPROVAL = "request_approval"
    COMPLETE = "complete"

class ApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Action(BaseModel):
    kind: ActionKind
    path: str | None = None
    content: str | None = None
    reason: str | None = None

class Feedback(BaseModel):
    passed: bool
    summary: str
    failed_tests: list[str] = []

class ToolResult(BaseModel):
    ok: bool
    output: str
    feedback: Feedback | None = None
```

- [x] **Step 4: Run the model tests to verify success**

Run: `python -m pytest tests/test_models.py -v`  
Expected: PASS (2 passed).

- [x] **Step 5: Commit**

```bash
git add pyproject.toml src/fr_harness tests/test_models.py
git commit -m "feat: add domain models"
```

## Task 2: Add SQLite schema and audit repositories — completed; see `AGENT_LOG.md`

**Files:**
- Create: `src/fr_harness/db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Consumes: `TaskStatus` from `models.py`.
- Produces: `Database.initialize()`, `create_task(goal, workspace)`, `get_task(task_id)`, `append_event(task_id, kind, payload)`, `list_events(task_id)`.

- [x] **Step 1: Write the failing persistence test**

```python
from fr_harness.db import Database

def test_create_task_persists_a_created_task(tmp_path) -> None:
    db = Database(tmp_path / "fr.sqlite3")
    db.initialize()
    task = db.create_task("fix greeting", tmp_path)
    assert db.get_task(task.id).status == "created"
```

- [x] **Step 2: Verify the test fails**

Run: `python -m pytest tests/test_db.py::test_create_task_persists_a_created_task -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'fr_harness.db'`.

- [x] **Step 3: Implement the minimal SQLite repository**

Implement a `Database` class using one `sqlite3.connect(..., check_same_thread=False)` per operation. `initialize()` must create `tasks`, `events`, `approvals`, and `memory_entries` tables. Store task ids as UUID strings; `tasks` must include `id`, `goal`, `workspace`, `status`, `iteration`, and `created_at`. `append_event` serializes a JSON payload and `list_events` returns entries ordered by id ascending.

- [x] **Step 4: Verify repository behavior**

Run: `python -m pytest tests/test_db.py -v`  
Expected: PASS; include assertions that appended events retain their task id and JSON payload.

- [x] **Step 5: Commit**

```bash
git add src/fr_harness/db.py tests/test_db.py
git commit -m "feat: persist tasks and audit events"
```

## Task 3: Implement injectable LLM interfaces — completed; see `AGENT_LOG.md`

**Files:**
- Create: `src/fr_harness/llm.py`
- Create: `tests/test_llm.py`

**Interfaces:**
- Consumes: `Action` from `models.py`.
- Produces: `LLMClient.next_action(context: list[dict[str, str]]) -> Action`, `MockLLM(actions: list[Action])`, `OpenAICompatibleLLM(base_url, model, api_key)`.

- [x] **Step 1: Write the failing MockLLM test**

```python
from fr_harness.llm import MockLLM
from fr_harness.models import Action, ActionKind

def test_mock_llm_returns_actions_in_order() -> None:
    expected = Action(kind=ActionKind.COMPLETE, reason="tests pass")
    client = MockLLM([expected])
    assert client.next_action([]) == expected
```

- [x] **Step 2: Verify failure**

Run: `python -m pytest tests/test_llm.py::test_mock_llm_returns_actions_in_order -v`  
Expected: FAIL with import error.

- [x] **Step 3: Implement clients**

Define a `Protocol` named `LLMClient`. `MockLLM` pops actions from a private list and raises `RuntimeError("mock action queue exhausted")` when empty. `OpenAICompatibleLLM` must use `httpx.Client`, send `POST {base_url}/chat/completions`, pass the key only in an Authorization header, parse the first message content as JSON, and validate it with `Action.model_validate_json`. Do not log the key or response headers.

- [x] **Step 4: Verify MockLLM and adapter parsing**

Run: `python -m pytest tests/test_llm.py -v`  
Expected: PASS; use `httpx.MockTransport` to assert adapter JSON parsing without network traffic.

- [x] **Step 5: Commit**

```bash
git add src/fr_harness/llm.py tests/test_llm.py
git commit -m "feat: add injectable llm clients"
```

## Task 4: Build guardrails and one-time approval state machine

**Files:**
- Create: `src/fr_harness/guardrails.py`
- Create: `tests/test_guardrails.py`

**Interfaces:**
- Consumes: `Action`, `ActionKind`, `ApprovalDecision`.
- Produces: `resolve_workspace_path(root: Path, value: str) -> Path`, `classify(action, root) -> GuardDecision`, `ApprovalStateMachine.approve(id)`, `ApprovalStateMachine.reject(id)`.

- [ ] **Step 1: Write failing safety tests**

```python
import pytest
from fr_harness.guardrails import resolve_workspace_path

def test_workspace_path_rejects_escape(tmp_path) -> None:
    with pytest.raises(ValueError, match="outside workspace"):
        resolve_workspace_path(tmp_path, "../secret.txt")
```

```python
def test_pending_approval_cannot_execute() -> None:
    machine = ApprovalStateMachine()
    approval = machine.create("write_file", "overwrite app.py")
    assert machine.can_execute(approval.id) is False
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_guardrails.py -v`  
Expected: FAIL with import error.

- [ ] **Step 3: Implement deterministic guardrails**

Resolve `root / value` with `Path.resolve()` and reject when `resolved.is_relative_to(root.resolve())` is false. Classify writes to an existing file and `RUN_PYTEST` as `requires_approval`; classify paths outside root as `blocked`; classify reads and new-file writes as `allowed`. Model approvals as `pending`, `approved`, `rejected`, `consumed`; `consume()` must only transition an approved record once.

- [ ] **Step 4: Verify safety behavior**

Run: `python -m pytest tests/test_guardrails.py -v`  
Expected: PASS; include tests for approve-once, reject-never-executes, and overwriting an existing file requiring approval.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/guardrails.py tests/test_guardrails.py
git commit -m "feat: add guardrails and approval state machine"
```

## Task 5: Build constrained tools and pytest feedback parser

**Files:**
- Create: `src/fr_harness/feedback.py`
- Create: `src/fr_harness/tools.py`
- Create: `tests/test_tools.py`
- Create: `tests/test_feedback.py`

**Interfaces:**
- Consumes: `Action`, `ToolResult`, `Feedback`, `resolve_workspace_path`.
- Produces: `ToolDispatcher.execute(action, workspace) -> ToolResult`, `parse_pytest_result(returncode, stdout, stderr) -> Feedback`.

- [ ] **Step 1: Write failing test and feedback tests**

```python
from fr_harness.feedback import parse_pytest_result

def test_failed_pytest_result_contains_failed_node_id() -> None:
    feedback = parse_pytest_result(1, "FAILED test_app.py::test_greeting - AssertionError", "")
    assert feedback.passed is False
    assert feedback.failed_tests == ["test_app.py::test_greeting"]
```

```python
def test_read_file_returns_workspace_content(tmp_path) -> None:
    (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")
    result = ToolDispatcher().execute(Action(kind="read_file", path="app.py"), tmp_path)
    assert result.output == "x = 1"
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_tools.py tests/test_feedback.py -v`  
Expected: FAIL with import errors.

- [ ] **Step 3: Implement tools and parser**

`ToolDispatcher` must support only read, write, and pytest actions. File reads/writes use UTF-8 and the guardrail path resolver. Pytest runs `subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=workspace, capture_output=True, text=True, timeout=60, check=False)`; it must never execute arbitrary shell strings. `parse_pytest_result` returns `passed=True` only for code 0, extracts lines beginning with `FAILED `, and keeps summary to at most 2,000 characters.

- [ ] **Step 4: Verify behavior**

Run: `python -m pytest tests/test_tools.py tests/test_feedback.py -v`  
Expected: PASS; include a temporary failing pytest project to prove test feedback is objective.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/feedback.py src/fr_harness/tools.py tests/test_tools.py tests/test_feedback.py
git commit -m "feat: add constrained tools and pytest feedback"
```

## Task 6: Add memory repository and context builder

**Files:**
- Create: `src/fr_harness/memory.py`
- Create: `tests/test_memory.py`

**Interfaces:**
- Consumes: `Database`.
- Produces: `MemoryStore.add(task_id, category, content)`, `MemoryStore.relevant(task_id, limit=5) -> list[str]`, `build_context(goal, memories, feedback) -> list[dict[str, str]]`.

- [ ] **Step 1: Write failing memory test**

```python
def test_context_contains_goal_and_only_recent_memories(tmp_path) -> None:
    store = MemoryStore(Database(tmp_path / "db.sqlite3"))
    store.db.initialize()
    store.add("t1", "failed_attempt", "first patch failed")
    context = build_context("fix greeting", store.relevant("t1"), None)
    assert context[-1]["content"] == "fix greeting"
    assert "first patch failed" in str(context)
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_memory.py -v`  
Expected: FAIL with import error.

- [ ] **Step 3: Implement minimal memory**

Persist category and content through the `memory_entries` table. `relevant()` returns the newest `limit` entries only. Context order is system safety constraints, memories, last feedback, then user goal; do not return or persist credentials.

- [ ] **Step 4: Verify behavior**

Run: `python -m pytest tests/test_memory.py -v`  
Expected: PASS; include a test that `limit=2` excludes older entries.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/memory.py tests/test_memory.py
git commit -m "feat: add task memory context"
```

## Task 7: Implement the self-built Agent control loop

**Files:**
- Create: `src/fr_harness/agent.py`
- Create: `tests/test_agent.py`

**Interfaces:**
- Consumes: `Database`, `LLMClient`, `ToolDispatcher`, `MemoryStore`, guardrails, feedback.
- Produces: `Agent.run_once(task_id) -> TaskStatus` and `Agent.resume_after_approval(task_id, approval_id) -> TaskStatus`.

- [ ] **Step 1: Write failing feedback-loop test**

```python
def test_agent_retries_after_pytest_feedback_then_succeeds(project_with_failing_test, db) -> None:
    llm = MockLLM([
        Action(kind="write_file", path="app.py", content="def greet(): return 'bad'"),
        Action(kind="run_pytest"),
        Action(kind="write_file", path="app.py", content="def greet(): return 'hello'"),
        Action(kind="run_pytest"),
        Action(kind="complete", reason="objective test passed"),
    ])
    task = db.create_task("fix greeting", project_with_failing_test)
    agent = make_agent(db, llm)
    assert agent.run_until_stopped(task.id).value == "succeeded"
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_agent.py::test_agent_retries_after_pytest_feedback_then_succeeds -v`  
Expected: FAIL with import error.

- [ ] **Step 3: Implement loop and stop policy**

Implement `run_once()` so it increments iteration, appends an LLM action event, validates and classifies action, and executes only allowed actions. A blocked action marks the task failed. A dangerous action creates an approval, records an event, and sets task state to `pending_approval`. A failed pytest result is persisted as memory and leaves the task `running`; only a passing pytest followed by `COMPLETE` marks success. Track normalized `Action.model_dump_json()` values and fail after two consecutive identical actions or iteration 8.

- [ ] **Step 4: Verify loop behavior**

Run: `python -m pytest tests/test_agent.py -v`  
Expected: PASS; include tests for maximum iterations, repeated action failure, blocked path, and no success when complete occurs after failed pytest.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/agent.py tests/test_agent.py
git commit -m "feat: add agent feedback control loop"
```

## Task 8: Persist and resume WebUI approvals

**Files:**
- Modify: `src/fr_harness/db.py`
- Modify: `src/fr_harness/agent.py`
- Create: `tests/test_approvals_integration.py`

**Interfaces:**
- Produces: `Database.create_approval(task_id, action_json)`, `Database.decide_approval(id, decision)`, `Database.get_pending_approval(task_id)`.

- [ ] **Step 1: Write failing approval-resume test**

```python
def test_agent_does_not_overwrite_until_approval_then_executes(tmp_path, db) -> None:
    target = tmp_path / "app.py"
    target.write_text("old", encoding="utf-8")
    task = db.create_task("update app", tmp_path)
    agent = make_agent(db, MockLLM([Action(kind="write_file", path="app.py", content="new")]))
    assert agent.run_once(task.id).value == "pending_approval"
    assert target.read_text(encoding="utf-8") == "old"
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_approvals_integration.py -v`  
Expected: FAIL because approval persistence/resume does not exist.

- [ ] **Step 3: Persist one-time approval and resume**

Store the complete action JSON in `approvals`. On approval, atomically transition `pending` to `approved`; `resume_after_approval()` atomically consumes it, dispatches its stored action, and appends approval/execution events. Rejection transitions task to `cancelled`; a consumed approval cannot run a second time.

- [ ] **Step 4: Verify all approval paths**

Run: `python -m pytest tests/test_approvals_integration.py -v`  
Expected: PASS; add tests for rejection, one-time consumption, and restart-safe retrieval from SQLite.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/db.py src/fr_harness/agent.py tests/test_approvals_integration.py
git commit -m "feat: persist approval workflow"
```

## Task 9: Add FastAPI API and minimal three-page WebUI

**Files:**
- Create: `src/fr_harness/web.py`
- Create: `tests/test_web.py`

**Interfaces:**
- Produces: `create_app(database_path: Path, llm: LLMClient) -> FastAPI`.
- Routes: `GET /`, `POST /tasks`, `GET /tasks/{task_id}`, `GET /approvals`, `POST /approvals/{approval_id}/approve`, `POST /approvals/{approval_id}/reject`.

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient

def test_create_task_returns_task_id(app, workspace) -> None:
    client = TestClient(app)
    response = client.post("/tasks", data={"goal": "fix greeting", "workspace": str(workspace)})
    assert response.status_code == 303
    assert "/tasks/" in response.headers["location"]
```

```python
def test_approval_page_can_reject_pending_action(client, pending_approval) -> None:
    response = client.post(f"/approvals/{pending_approval}/reject", follow_redirects=False)
    assert response.status_code == 303
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_web.py -v`  
Expected: FAIL with import error.

- [ ] **Step 3: Implement routes and HTML**

Use FastAPI `Form` inputs and `HTMLResponse`; do not add a frontend build system. `/` has a task form, task detail displays task status plus ordered audit event JSON in escaped `<pre>` text, and `/approvals` lists only pending approvals with separate approve/reject POST forms. Validate workspace path exists and is a directory before creating a task. Route handlers must never render keys.

- [ ] **Step 4: Verify WebUI behavior**

Run: `python -m pytest tests/test_web.py -v`  
Expected: PASS; include assertions that detail HTML contains status and event output.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/web.py tests/test_web.py
git commit -m "feat: add task and approval web ui"
```

## Task 10: Add CLI, secure configuration, and Docker distribution

**Files:**
- Create: `src/fr_harness/cli.py`
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `.env.example`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces commands `python -m fr_harness.cli init`, `serve`, and `test`.

- [ ] **Step 1: Write failing CLI configuration tests**

```python
def test_init_creates_database_without_printing_key(tmp_path, capsys) -> None:
    assert main(["init", "--database", str(tmp_path / "fr.sqlite3")]) == 0
    assert "OPENAI_API_KEY" not in capsys.readouterr().out
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_cli.py -v`  
Expected: FAIL with import error.

- [ ] **Step 3: Implement distribution files**

`init` initializes SQLite; `serve` reads `FR_DATABASE_PATH`, `FR_LLM_BASE_URL`, `FR_LLM_MODEL`, and `OPENAI_API_KEY` from environment without logging values; `test` runs pytest through `subprocess.run`. Docker must use `python:3.12-slim`, install the package, expose 8000, and execute `uvicorn fr_harness.web:app --host 0.0.0.0 --port 8000`. `.dockerignore` must exclude `.git`, `.env`, `.venv`, `__pycache__`, and `*.sqlite3`.

- [ ] **Step 4: Verify behavior**

Run: `python -m pytest tests/test_cli.py -v`  
Expected: PASS; then run `docker build -t fr-harness:local .`.

- [ ] **Step 5: Commit**

```bash
git add src/fr_harness/cli.py Dockerfile .dockerignore .env.example tests/test_cli.py
git commit -m "feat: add cli and docker distribution"
```

## Task 11: Create required mock mechanism demonstration

**Files:**
- Create: `demo/mock_repair_demo.py`
- Create: `tests/test_demo.py`

**Interfaces:**
- Produces: `python demo/mock_repair_demo.py`, exit code 0 only when all three required scenarios complete.

- [ ] **Step 1: Write failing demo test**

```python
import subprocess
import sys

def test_demo_reports_all_required_mechanisms() -> None:
    result = subprocess.run([sys.executable, "demo/mock_repair_demo.py"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "guardrail approval: PASS" in result.stdout
    assert "feedback repair: PASS" in result.stdout
    assert "approval one-time use: PASS" in result.stdout
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_demo.py -v`  
Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement deterministic demo**

Use `TemporaryDirectory`, a minimal temporary pytest project, and MockLLM action queues. The script must print exactly one PASS line for each required scenario: guardrail approval, feedback repair, approval one-time use. It must never instantiate an external HTTP client or read a real API key.

- [ ] **Step 4: Verify demo**

Run: `python demo/mock_repair_demo.py && python -m pytest tests/test_demo.py -v`  
Expected: three PASS lines followed by a passing test.

- [ ] **Step 5: Commit**

```bash
git add demo/mock_repair_demo.py tests/test_demo.py
git commit -m "test: add deterministic mechanism demo"
```

## Task 12: Add CI, complete README, and run cold-start verification

**Files:**
- Create: `.gitlab-ci.yml`
- Modify: `README.md`
- Create: `tests/test_readme_security.py`

**Interfaces:**
- Produces GitLab `unit-test` job and a standalone runbook for a new user.

- [ ] **Step 1: Write failing documentation test**

```python
from pathlib import Path

def test_readme_documents_safe_key_configuration() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in text
    assert ".env" in text
    assert "明文" in text
    assert "docker build" in text
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/test_readme_security.py -v`  
Expected: FAIL because the initial README does not contain complete operational guidance.

- [ ] **Step 3: Implement CI and documentation**

Create `.gitlab-ci.yml` with a `unit-test` job that installs `.[dev]` and runs `python -m pytest -v`; add a second Docker build job if GitLab runner supports Docker. Rewrite README in UTF-8 with sections: project overview, architecture, local install, one-command tests, WebUI, MockLLM demo, Docker build/run, API-key security, `.env` plaintext warning, workspace safety boundary, limitations, and directory structure. Include exact Docker commands and state that mounted workspaces contain user code.

- [ ] **Step 4: Verify repository release criteria**

Run: `python -m pytest -v`  
Expected: PASS.

Run: `python demo/mock_repair_demo.py`  
Expected: three PASS lines.

Run: `git status --short`  
Expected: only intentional documentation/CI changes before commit.

- [ ] **Step 5: Commit**

```bash
git add .gitlab-ci.yml README.md tests/test_readme_security.py
git commit -m "docs: add release and security guide"
```

## Dependency and Parallelism Map

| Task | Depends on | Can run in a separate worktree after dependency merges |
| --- | --- | --- |
| 1 | none | no |
| 2 | 1 | no |
| 3 | 1 | yes |
| 4 | 1 | yes |
| 5 | 1, 4 | no |
| 6 | 1, 2 | yes |
| 7 | 2, 3, 4, 5, 6 | no |
| 8 | 2, 4, 5, 7 | no |
| 9 | 2, 3, 7, 8 | no |
| 10 | 2, 3, 9 | no |
| 11 | 7, 8 | yes |
| 12 | 10, 11 | no |

## Plan Self-Review

### Spec coverage

- Self-built loop: Task 7.
- Mock and real LLM abstraction: Task 3.
- Constrained tools and pytest feedback: Task 5.
- Governance, safety boundaries, HITL, and audit: Tasks 2, 4, and 8.
- Memory: Task 6.
- WebUI and CLI: Tasks 9 and 10.
- Docker, CI, README, and cold-start readiness: Tasks 10 and 12.
- Required deterministic mechanism demonstration: Task 11.

### Placeholder scan

No implementation step contains TBD, TODO, or an unspecified future task. Each test/implementation task gives a file path, exact command, expected result, and a concrete interface.

### Type consistency

All LLMs return `Action`; all tools return `ToolResult`; pytest produces `Feedback`; agent task control uses `TaskStatus`; approvals use `ApprovalDecision`. The only later dependencies are listed explicitly in the dependency map.

