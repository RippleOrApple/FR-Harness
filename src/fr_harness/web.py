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
from fr_harness.models import ApprovalDecision, TaskStatus


def _page(title: str, body: str) -> HTMLResponse:
    safe_title = html.escape(title, quote=True)
    return HTMLResponse(
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:2rem auto;line-height:1.5}"
        "input,textarea{width:100%;box-sizing:border-box;margin:.3rem 0 1rem;padding:.5rem}"
        "button{margin-right:.5rem;padding:.4rem .8rem}pre{white-space:pre-wrap;background:#f5f5f5;padding:1rem}"
        "nav a{margin-right:1rem}</style></head><body>"
        "<nav><a href='/'>新建任务</a><a href='/approvals'>待审批</a></nav>"
        f"<h1>{safe_title}</h1>{body}</body></html>"
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
            "<label>工作区绝对路径<input name='workspace' required></label>"
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
            raise HTTPException(status_code=400, detail="workspace must be an existing directory")
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
        body = (
            f"<p><strong>目标：</strong>{html.escape(task.goal, quote=True)}</p>"
            f"<p><strong>工作区：</strong>{html.escape(str(task.workspace), quote=True)}</p>"
            f"<p><strong>状态：</strong>{html.escape(task.status.value, quote=True)}</p>"
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
            action_text = json.dumps(
                approval.action.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            )
            items.append(
                "<section>"
                f"<h2><a href='/tasks/{approval.task_id}'>任务 {approval.task_id}</a></h2>"
                f"<pre>{html.escape(action_text, quote=True)}</pre>"
                f"<form method='post' action='/approvals/{approval.id}/approve' style='display:inline'>"
                "<button type='submit'>批准</button></form>"
                f"<form method='post' action='/approvals/{approval.id}/reject' style='display:inline'>"
                "<button type='submit'>拒绝</button></form></section>"
            )
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
