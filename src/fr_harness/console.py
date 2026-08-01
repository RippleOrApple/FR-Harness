import difflib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fr_harness.db import ApprovalRecord
from fr_harness.guardrails import resolve_workspace_path
from fr_harness.models import Action, ActionKind, ApprovalDecision, Task, TaskStatus
from fr_harness.security import redact_secrets
from fr_harness.task_service import TaskService


STATUS_LABELS = {
    TaskStatus.CREATED: "已创建",
    TaskStatus.RUNNING: "运行中",
    TaskStatus.PENDING_APPROVAL: "等待审批",
    TaskStatus.PAUSED: "已暂停",
    TaskStatus.SUCCEEDED: "已成功",
    TaskStatus.FAILED: "已失败",
    TaskStatus.CANCELLED: "已取消",
}


@dataclass(frozen=True)
class DiffPreview:
    path: str
    added: int
    removed: int
    text: str
    truncated: bool


def render_action_diff(
    workspace: Path, action: Action, *, limit: int = 20_000
) -> DiffPreview:
    if action.kind is not ActionKind.WRITE_FILE or action.path is None:
        raise ValueError("write_file action with path required")
    target = resolve_workspace_path(workspace, action.path)
    previous = target.read_text(encoding="utf-8") if target.exists() else ""
    updated = action.content or ""
    lines = list(
        difflib.unified_diff(
            previous.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"{action.path}（修改前）",
            tofile=f"{action.path}（修改后）",
        )
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    safe_text = redact_secrets("".join(lines))
    truncated = len(safe_text) > limit
    return DiffPreview(
        path=action.path,
        added=added,
        removed=removed,
        text=safe_text[:limit],
        truncated=truncated,
    )


class InteractiveConsole:
    def __init__(
        self,
        service: TaskService,
        *,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
        cwd_provider: Callable[[], Path] = Path.cwd,
        configure: Callable[[], None] | None = None,
    ) -> None:
        self.service = service
        self.input = input_fn
        self.output = output_fn
        self.cwd_provider = cwd_provider
        self.configure = configure

    def run(self) -> int:
        while True:
            self.output("\nFR-Harness\n")
            self.output("1. 新建修复任务")
            self.output("2. 查看历史任务")
            self.output("3. 配置与自检")
            self.output("4. 退出")
            choice = self.input("请选择 [1-4]：").strip()
            if choice == "1":
                self._new_task()
            elif choice == "2":
                self._history()
            elif choice == "3":
                if self.configure is None:
                    self.output("当前运行方式未提供配置入口。")
                else:
                    self.configure()
            elif choice == "4":
                self.output("已退出 FR-Harness。")
                return 0
            else:
                self.output("请输入 1、2、3 或 4。")

    def approve_action(
        self, task: Task, approval: ApprovalRecord
    ) -> ApprovalDecision:
        action = approval.action
        if action.kind is ActionKind.WRITE_FILE:
            preview = render_action_diff(task.workspace, action)
            self.output("\n需要审批：修改已有文件")
            self.output(f"文件：{preview.path}")
            self.output(f"原因：{redact_secrets(action.reason or 'Agent 请求修改文件')}")
            self.output(f"变化：新增 {preview.added} 行，删除 {preview.removed} 行")
            while True:
                choice = self.input("[D] 查看完整差异  [A] 批准  [R] 拒绝：").strip().lower()
                if choice == "d":
                    self.output(preview.text or "文件内容没有变化。")
                    if preview.truncated:
                        self.output("差异内容过长，已截断。")
                elif choice == "a":
                    return ApprovalDecision.APPROVED
                elif choice == "r":
                    return ApprovalDecision.REJECTED
                else:
                    self.output("请输入 D、A 或 R。")
        self.output("\n需要审批：Agent 请求执行受控操作")
        self.output(f"原因：{redact_secrets(action.reason or action.kind.value)}")
        while True:
            choice = self.input("[A] 批准  [R] 拒绝：").strip().lower()
            if choice == "a":
                return ApprovalDecision.APPROVED
            if choice == "r":
                return ApprovalDecision.REJECTED
            self.output("请输入 A 或 R。")

    def _new_task(self) -> None:
        while True:
            current = self.cwd_provider().resolve()
            raw_workspace = self.input(f"工作区 [{current.name or current}]：").strip()
            workspace = Path(raw_workspace).expanduser().resolve() if raw_workspace else current
            if workspace.is_dir():
                break
            self.output("工作区不存在或不是目录，请重新输入。")

        while True:
            goal = self.input("请输入单行修复目标：").strip()
            if goal:
                break
            self.output("修复目标不能为空。")

        self.output("\n请确认任务：")
        self.output(f"工作区：{workspace.name or workspace}")
        self.output(f"修复目标：{redact_secrets(goal)}")
        while True:
            choice = self.input("[S] 开始  [E] 重新输入  [Q] 取消：").strip().lower()
            if choice == "q":
                self.output("已取消创建任务。")
                return
            if choice == "e":
                return self._new_task()
            if choice == "s":
                break
            self.output("请输入 S、E 或 Q。")

        self.output("\npytest 会执行工作区中的 Python 代码，请只对可信项目授权。")
        permission = self.input("[A] 允许本任务运行 pytest  [Q] 取消：").strip().lower()
        if permission != "a":
            self.output("未授权 pytest，任务未创建。")
            return

        task = self.service.create_task(goal, workspace, allow_pytest=True)
        try:
            result = self.service.run(
                task.id,
                approve=self.approve_action,
                on_events=self._show_events,
            )
        except KeyboardInterrupt:
            self.service.pause(task.id, "用户中断")
            self.output("任务状态已保存，可以从历史任务继续。")
            return
        self._show_result(result)

    def _history(self) -> None:
        tasks = self.service.list_tasks()
        if not tasks:
            self.output("当前没有历史任务。")
            return
        self.output("\n历史任务")
        for index, task in enumerate(tasks, start=1):
            self.output(
                f"{index}. [{STATUS_LABELS[task.status]}] {task.goal}\n"
                f"   工作区：{task.workspace.name or task.workspace}  轮次：{task.iteration}"
            )
        raw = self.input("输入序号查看，直接回车返回：").strip()
        if not raw:
            return
        try:
            task = tasks[int(raw) - 1]
        except (ValueError, IndexError):
            self.output("任务序号无效。")
            return
        self.output(f"目标：{task.goal}")
        self.output(f"状态：{STATUS_LABELS[task.status]}")
        if task.status not in {
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.PAUSED,
            TaskStatus.RUNNING,
        }:
            return
        if self.input("[R] 恢复任务  [Enter] 返回：").strip().lower() != "r":
            return
        result = self.service.resume(
            task.id,
            approve=self.approve_action,
            on_events=self._show_events,
        )
        self._show_result(result)

    def _show_events(self, task: Task, events: list[dict[str, object]]) -> None:
        for event in events:
            kind = event["kind"]
            payload = event["payload"]
            if not isinstance(payload, dict):
                continue
            if kind == "action":
                action_kind = payload.get("kind")
                path = payload.get("path")
                labels = {
                    ActionKind.READ_FILE.value: "读取文件",
                    ActionKind.WRITE_FILE.value: "准备修改",
                    ActionKind.RUN_PYTEST.value: "运行测试",
                    ActionKind.COMPLETE.value: "完成确认",
                }
                label = labels.get(str(action_kind), "执行操作")
                suffix = f" {path}" if path else ""
                self.output(f"[第 {task.iteration} 轮] [{label}]{suffix}")
            elif kind == "tool_result":
                ok = bool(payload.get("ok"))
                output = redact_secrets(str(payload.get("output", "")))
                self.output(f"[测试{'通过' if ok else '失败'}] {output}")
                details = payload.get("details")
                if not ok and details is not None:
                    choice = self.input("[L] 查看完整 pytest 输出  [Enter] 继续：").strip().lower()
                    if choice == "l":
                        self.output(redact_secrets(str(details)))

    def _show_result(self, task: Task) -> None:
        title = (
            "任务已成功完成"
            if task.status is TaskStatus.SUCCEEDED
            else f"任务{STATUS_LABELS[task.status]}"
        )
        self.output(f"\n{title}")
        self.output(f"目标：{task.goal}")
        self.output(f"执行轮次：{task.iteration}")
