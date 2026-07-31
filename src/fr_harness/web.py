import html
import json
from pathlib import Path
from urllib.parse import parse_qs
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fr_harness.agent import Agent
from fr_harness.config import HarnessConfig
from fr_harness.db import Database
from fr_harness.llm import LLMClient
from fr_harness.models import Action, ActionKind, ApprovalDecision, Task, TaskStatus


def _page(title: str, body: str) -> HTMLResponse:
    safe_title = html.escape(title, quote=True)
    return HTMLResponse(
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:2rem auto;line-height:1.5}"
        "input,textarea{width:100%;box-sizing:border-box;margin:.3rem 0 1rem;padding:.5rem}"
        "button{margin-right:.5rem;padding:.4rem .8rem}"
        "pre{white-space:pre-wrap;background:#f5f5f5;padding:1rem}"
        "nav a{margin-right:1rem}"
        ".notice{border:2px solid #a16207;background:#fff7ed;padding:1rem;margin:1rem 0}"
        ".notice strong{display:block;margin-bottom:.25rem}"
        ".meta{color:#555}"
        ".approval-grid{margin:.75rem 0}"
        ".approval-grid p{margin:.25rem 0}"
        ".approval-title{font-size:1.25rem;margin:0 0 .75rem}"
        "details{margin-top:1rem}</style></head><body>"
        "<nav><a href='/'>新建任务</a><a href='/approvals'>待审批</a></nav>"
        f"<h1>{safe_title}</h1>{body}</body></html>"
    )


def _status_label(status: TaskStatus) -> str:
    labels = {
        TaskStatus.CREATED: "已创建",
        TaskStatus.RUNNING: "运行中",
        TaskStatus.PENDING_APPROVAL: "等待审批",
        TaskStatus.SUCCEEDED: "已成功",
        TaskStatus.FAILED: "已失败",
        TaskStatus.CANCELLED: "已取消",
    }
    return labels[status]


def _action_title(action: Action) -> str:
    titles = {
        ActionKind.READ_FILE: "读取文件",
        ActionKind.WRITE_FILE: "写入/覆盖文件",
        ActionKind.RUN_PYTEST: "运行测试",
        ActionKind.REQUEST_APPROVAL: "请求人工确认",
        ActionKind.COMPLETE: "声明任务完成",
    }
    return titles[action.kind]


def _action_description(action: Action) -> list[tuple[str, str]]:
    if action.kind is ActionKind.RUN_PYTEST:
        return [
            ("说明", "Agent 想运行 pytest，检查当前代码是否已经修好。"),
            ("影响", "会执行目标项目的测试代码，不会修改文件。"),
            ("命令", "python -m pytest -q -p no:cacheprovider"),
        ]
    if action.kind is ActionKind.WRITE_FILE:
        preview = (action.content or "").splitlines()[0] if action.content else "空内容"
        if len(preview) > 120:
            preview = preview[:117] + "..."
        return [
            ("说明", "Agent 想写入目标文件。"),
            ("影响", "会修改目标项目中的文件内容。"),
            ("目标文件", action.path or "未指定"),
            ("内容预览", preview),
        ]
    if action.kind is ActionKind.READ_FILE:
        return [
            ("说明", "Agent 想读取目标项目中的文件内容。"),
            ("影响", "只读取文件，不会修改文件。"),
            ("目标文件", action.path or "未指定"),
        ]
    if action.kind is ActionKind.REQUEST_APPROVAL:
        return [
            ("说明", action.reason or "Agent 请求你确认下一步是否继续。"),
            ("影响", "批准后任务继续，拒绝后任务取消。"),
        ]
    return [
        ("说明", action.reason or "Agent 认为任务已经完成。"),
        ("影响", "批准后会记录该任务完成。"),
    ]


def _definition_list(rows: list[tuple[str, str]]) -> str:
    rendered = ["<div class='approval-grid'>"]
    for label, value in rows:
        rendered.append(
            "<p>"
            f"{html.escape(label, quote=True)}："
            f"{html.escape(value, quote=True)}</p>"
        )
    rendered.append("</div>")
    return "".join(rendered)


def _approval_card(task: Task, approval_id: UUID, action: Action) -> str:
    action_json = json.dumps(
        action.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    task_rows = [
        ("任务", task.goal),
        ("工作区", task.workspace.name or "."),
        ("当前状态", _status_label(task.status)),
        ("已执行轮次", str(task.iteration)),
    ]
    detail_rows = [
        ("任务编号", str(task.id)),
        ("审批编号", str(approval_id)),
    ]
    return (
        "<section class='notice'>"
        f"<h2 class='approval-title'>需要审批：{html.escape(_action_title(action), quote=True)}</h2>"
        "<p>请确认是否允许 Agent 执行下面这个操作。批准后任务会继续运行；拒绝后任务会取消。</p>"
        "<h3>关联任务</h3>"
        f"{_definition_list(task_rows)}"
        "<h3>本次操作</h3>"
        f"{_definition_list(_action_description(action))}"
        f"<p><a href='/tasks/{task.id}'>查看任务详情</a></p>"
        f"<form method='post' action='/approvals/{approval_id}/approve' style='display:inline'>"
        "<button type='submit'>批准并继续</button></form>"
        f"<form method='post' action='/approvals/{approval_id}/reject' style='display:inline'>"
        "<button type='submit'>拒绝并取消任务</button></form>"
        "<details><summary>技术详情</summary>"
        f"{_definition_list(detail_rows)}"
        f"<h4>原始动作 JSON</h4><pre>{html.escape(action_json, quote=True)}</pre>"
        "</details></section>"
    )


async def _urlencoded_form(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/x-www-form-urlencoded"):
        raise HTTPException(status_code=415, detail="URL-encoded form required")
    try:
        body = (await request.body()).decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="form must be UTF-8") from error
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items() if values}


def create_app(
    database_path: Path,
    llm: LLMClient,
    *,
    config: HarnessConfig | None = None,
) -> FastAPI:
    app = FastAPI()
    database = Database(database_path)
    database.initialize()
    agent = Agent(database, llm, config=config)
    app.state.database = database
    app.state.agent = agent

    @app.get("/", response_class=HTMLResponse)
    def task_form() -> HTMLResponse:
        return _page(
            "创建修复任务",
            "<form method='post' action='/tasks'>"
            "<label>目标<textarea name='goal' required></textarea></label>"
            "<label>工作区路径<input name='workspace' required></label>"
            "<button type='submit'>创建并运行</button></form>",
        )

    @app.post("/tasks")
    async def create_task(request: Request):
        form = await _urlencoded_form(request)
        goal = form.get("goal", "").strip()
        workspace_value = form.get("workspace", "").strip()
        if not goal:
            raise HTTPException(status_code=400, detail="goal is required")
        workspace = Path(workspace_value).expanduser()
        if not workspace.exists() or not workspace.is_dir():
            raise HTTPException(
                status_code=400, detail="workspace must be an existing directory"
            )
        task = database.create_task(goal, workspace)
        agent.run_until_stopped(task.id)
        return RedirectResponse(f"/tasks/{task.id}", status_code=303)

    @app.get("/tasks/{task_id}", response_class=HTMLResponse)
    def task_detail(task_id: UUID) -> HTMLResponse:
        try:
            task = database.get_task(task_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="task not found") from error
        audit = json.dumps(
            database.list_events(task.id),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        approval_notice = ""
        if task.status is TaskStatus.PENDING_APPROVAL:
            approval_notice = (
                "<div class='notice'><strong>需要你审批</strong>"
                "Agent 已暂停，正在等待你确认是否允许执行一个可能修改文件或运行测试的操作。"
                "请进入 <a href='/approvals'>待审批页面</a> 查看并选择批准或拒绝。</div>"
            )
        workspace_label = task.workspace.name or "."
        body = (
            f"{approval_notice}"
            f"<p><strong>目标：</strong>{html.escape(task.goal, quote=True)}</p>"
            f"<p><strong>工作区：</strong>{html.escape(workspace_label, quote=True)}</p>"
            f"<p><strong>状态：</strong>{html.escape(_status_label(task.status), quote=True)}</p>"
            f"<p><strong>轮次：</strong>{task.iteration}</p>"
            f"<h2>审计日志</h2><pre>{html.escape(audit, quote=True)}</pre>"
        )
        return _page("任务详情", body)

    @app.get("/approvals", response_class=HTMLResponse)
    def approvals_page() -> HTMLResponse:
        approvals = database.list_pending_approvals()
        if not approvals:
            return _page("待审批操作", "<p>当前没有待审批操作。</p>")
        items: list[str] = []
        for approval in approvals:
            task = database.get_task(approval.task_id)
            items.append(_approval_card(task, approval.id, approval.action))
        return _page("待审批操作", "".join(items))

    def _decide(approval_id: UUID, decision: ApprovalDecision) -> RedirectResponse:
        try:
            approval = database.decide_approval(approval_id, decision)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="approval not found") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        task = agent.resume_after_approval(approval.task_id)
        if task.status is TaskStatus.RUNNING:
            agent.run_until_stopped(task.id)
        return RedirectResponse(f"/tasks/{approval.task_id}", status_code=303)

    @app.post("/approvals/{approval_id}/approve")
    def approve(approval_id: UUID) -> RedirectResponse:
        return _decide(approval_id, ApprovalDecision.APPROVED)

    @app.post("/approvals/{approval_id}/reject")
    def reject(approval_id: UUID) -> RedirectResponse:
        return _decide(approval_id, ApprovalDecision.REJECTED)

    return app
