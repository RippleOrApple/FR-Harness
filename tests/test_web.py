from pathlib import Path

from starlette.testclient import TestClient

from fr_harness.llm import MockLLM
from fr_harness.models import Action, ActionKind, TaskStatus
from fr_harness.web import create_app


def make_client(tmp_path: Path, actions: list[Action] | None = None) -> TestClient:
    app = create_app(tmp_path / "fr.sqlite3", MockLLM(actions or []))
    return TestClient(app)


def test_post_tasks_redirects_to_task_detail(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    client = make_client(
        tmp_path, [Action(kind=ActionKind.COMPLETE, reason="premature")]
    )

    response = client.post(
        "/tasks",
        data={"goal": "fix greeting", "workspace": str(workspace)},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/tasks/")


def test_post_tasks_rejects_workspace_that_is_not_a_directory(tmp_path: Path) -> None:
    not_a_directory = tmp_path / "app.py"
    not_a_directory.write_text("value = 1", encoding="utf-8")
    client = make_client(tmp_path)

    response = client.post(
        "/tasks",
        data={"goal": "fix app", "workspace": str(not_a_directory)},
    )

    assert response.status_code == 400
    assert "workspace" in response.text.lower()


def test_task_detail_escapes_audit_json(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    database = client.app.state.database
    task = database.create_task("inspect <b>goal</b>", tmp_path)
    database.append_event(task.id, "unsafe", {"value": "<script>alert(1)</script>"})

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "inspect &lt;b&gt;goal&lt;/b&gt;" in response.text


def test_task_detail_never_displays_api_key_from_goal(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    database = client.app.state.database
    secret = "sk-test-secret-value"
    task = database.create_task(f"fix OPENAI_API_KEY={secret}", tmp_path)

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    assert secret not in response.text
    assert "[REDACTED]" in response.text


def test_approvals_page_lists_pending_action(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    database = client.app.state.database
    task = database.create_task("overwrite app", tmp_path)
    database.create_approval(
        task.id, Action(kind=ActionKind.WRITE_FILE, path="app.py", content="new")
    )

    response = client.get("/approvals")

    assert response.status_code == 200
    assert "app.py" in response.text
    assert f"/tasks/{task.id}" in response.text


def test_reject_approval_returns_303_and_cancels_task(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    database = client.app.state.database
    task = database.create_task("overwrite app", tmp_path)
    task.status = TaskStatus.PENDING_APPROVAL
    database.update_task(task)
    approval = database.create_approval(
        task.id, Action(kind=ActionKind.WRITE_FILE, path="app.py", content="new")
    )

    response = client.post(
        f"/approvals/{approval.id}/reject", follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/tasks/{task.id}"
    assert database.get_task(task.id).status is TaskStatus.CANCELLED
