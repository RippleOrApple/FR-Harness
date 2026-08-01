from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from fr_harness.console import InteractiveConsole, render_action_diff
from fr_harness.db import ApprovalRecord
from fr_harness.models import (
    Action,
    ActionKind,
    ApprovalDecision,
    Task,
    TaskStatus,
)


class RecordingService:
    def __init__(self, tasks: list[Task] | None = None) -> None:
        self.tasks = list(tasks or [])
        self.created: list[tuple[str, Path, bool]] = []
        self.resumed: list[object] = []
        self.paused: list[object] = []
        self.raise_interrupt = False

    def create_task(self, goal: str, workspace: Path, *, allow_pytest: bool) -> Task:
        self.created.append((goal, workspace, allow_pytest))
        task = Task(
            id=uuid4(),
            goal=goal,
            workspace=workspace,
            pytest_allowed=allow_pytest,
        )
        self.tasks.insert(0, task)
        return task

    def run(self, task_id, *, approve=None, on_events=None) -> Task:
        del approve, on_events
        if self.raise_interrupt:
            raise KeyboardInterrupt
        task = next(task for task in self.tasks if task.id == task_id)
        task.status = TaskStatus.SUCCEEDED
        return task

    def list_tasks(self) -> list[Task]:
        return self.tasks

    def resume(self, task_id, *, approve=None, on_events=None) -> Task:
        del approve, on_events
        self.resumed.append(task_id)
        task = next(task for task in self.tasks if task.id == task_id)
        task.status = TaskStatus.SUCCEEDED
        return task

    def pause(self, task_id, reason: str) -> Task:
        self.paused.append((task_id, reason))
        task = next(task for task in self.tasks if task.id == task_id)
        task.status = TaskStatus.PAUSED
        return task


def scripted_input(values: list[str]) -> Callable[[str], str]:
    answers = iter(values)
    return lambda prompt: next(answers)


def test_main_menu_has_four_chinese_actions_and_exits(tmp_path: Path) -> None:
    output: list[str] = []
    console = InteractiveConsole(
        RecordingService(),
        input_fn=scripted_input(["4"]),
        output_fn=output.append,
        cwd_provider=lambda: tmp_path,
    )

    assert console.run() == 0
    rendered = "\n".join(output)
    assert "1. 新建修复任务" in rendered
    assert "2. 查看历史任务" in rendered
    assert "3. 配置与自检" in rendered
    assert "4. 退出" in rendered


def test_new_task_uses_current_directory_and_single_line_goal(tmp_path: Path) -> None:
    output: list[str] = []
    service = RecordingService()
    console = InteractiveConsole(
        service,
        input_fn=scripted_input(["1", "", "修复金额计算", "s", "a", "4"]),
        output_fn=output.append,
        cwd_provider=lambda: tmp_path,
    )

    console.run()

    assert service.created == [("修复金额计算", tmp_path.resolve(), True)]
    rendered = "\n".join(output)
    assert "修复金额计算" in rendered
    assert "任务已成功完成" in rendered
    assert str(service.tasks[0].id) not in rendered


def test_new_task_retries_invalid_workspace_and_empty_goal(tmp_path: Path) -> None:
    output: list[str] = []
    service = RecordingService()
    console = InteractiveConsole(
        service,
        input_fn=scripted_input(
            ["1", str(tmp_path / "missing"), "", "   ", "repair", "s", "a", "4"]
        ),
        output_fn=output.append,
        cwd_provider=lambda: tmp_path,
    )

    console.run()

    rendered = "\n".join(output)
    assert "工作区不存在或不是目录" in rendered
    assert "修复目标不能为空" in rendered
    assert service.created[0][0] == "repair"


def test_render_action_diff_reports_changes_and_caps_output(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    action = Action(
        kind=ActionKind.WRITE_FILE,
        path="app.py",
        content="value = 2\nsecret = 'TOKEN=private-value'\n",
        reason="修复值",
    )

    preview = render_action_diff(tmp_path, action, limit=120)

    assert preview.path == "app.py"
    assert preview.added == 2
    assert preview.removed == 1
    assert "[REDACTED]" in preview.text
    assert len(preview.text) <= 120


def test_file_approval_can_show_diff_before_approval(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("value = 1\n", encoding="utf-8")
    task = Task(id=uuid4(), goal="repair", workspace=tmp_path)
    approval = ApprovalRecord(
        id=uuid4(),
        task_id=task.id,
        action=Action(
            kind=ActionKind.WRITE_FILE,
            path="app.py",
            content="value = 2\n",
            reason="修复值",
        ),
        decision=ApprovalDecision.PENDING,
        created_at="now",
    )
    output: list[str] = []
    console = InteractiveConsole(
        RecordingService(),
        input_fn=scripted_input(["d", "a"]),
        output_fn=output.append,
        cwd_provider=lambda: tmp_path,
    )

    decision = console.approve_action(task, approval)

    assert decision is ApprovalDecision.APPROVED
    rendered = "\n".join(output)
    assert "新增 1 行，删除 1 行" in rendered
    assert "-value = 1" in rendered
    assert "+value = 2" in rendered


def test_history_uses_goal_not_uuid_and_resumes_paused_task(tmp_path: Path) -> None:
    task = Task(
        id=uuid4(),
        goal="修复日期格式",
        workspace=tmp_path,
        status=TaskStatus.PAUSED,
        iteration=2,
    )
    output: list[str] = []
    service = RecordingService([task])
    console = InteractiveConsole(
        service,
        input_fn=scripted_input(["2", "1", "r", "4"]),
        output_fn=output.append,
        cwd_provider=lambda: tmp_path,
    )

    console.run()

    rendered = "\n".join(output)
    assert "修复日期格式" in rendered
    assert "已暂停" in rendered
    assert str(task.id) not in rendered
    assert service.resumed == [task.id]


def test_keyboard_interrupt_pauses_task_and_returns_to_menu(tmp_path: Path) -> None:
    service = RecordingService()
    service.raise_interrupt = True
    output: list[str] = []
    console = InteractiveConsole(
        service,
        input_fn=scripted_input(["1", "", "repair", "s", "a", "4"]),
        output_fn=output.append,
        cwd_provider=lambda: tmp_path,
    )

    console.run()

    assert len(service.paused) == 1
    assert "任务状态已保存" in "\n".join(output)
