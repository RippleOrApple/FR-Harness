# OpenCode 规格符合性评审

## 设置

- 日期：2026-07-17
- Reviewer：OpenCode CLI 1.17.18，`nju/deepseek-v4-flash`
- 会话：全新 `--pure`
- 权限：只读附件，不允许修改仓库
- 输入：两份课程要求、SPEC、PLAN、README、SPEC_PROCESS、AGENT_LOG、pyproject、GitHub workflow

## 执行记录

第一次命令把 positional prompt 放在 `--file` 数组之后，OpenCode 将 prompt 误当文件名，未进入评审。第二次允许遍历仓库的会话持续停留在文件读取，没有结论，主 Agent 在确认进程后终止。第三次改为附件限定且禁止工具调用，成功返回以下结论。

## OpenCode 原始结论摘要

OpenCode 报告：

- Critical C1：无线上部署 URL。
- Critical C2：无 PR 工作流/每功能 worktree。
- Critical C3：缺少逐 task subagent 与两阶段评审。
- Major M1：冷启动发生在 Task 1–3 之后，缺少真实修订 diff。
- Major M2：无认证 WebUI 与公开部署要求矛盾。
- Major M3：附件未含 `.gitlab-ci.yml`，无法验证。
- Major M4：附件未含 `REFLECTION.md`，无法验证 1500–2500 字。
- Minor：冷启动时序标记、回顾性日志和 commit message 缺 subagent 标注。

它同时确认自建主循环、MockLLM、代码护栏、反馈解析、离线机制测试、A 类机制章、机制演示、凭据设计和 Docker/CI 等核心要求已满足。原始 verdict 为“不可进入 PR”。

## 人工判断与处理

| 项目 | 判断 | 处理 |
|---|---|---|
| C1/M2 线上部署 | 有效课程缺口，但不在本轮前十项；当前无认证 WebUI 不能安全上公网 | 保留为未完成，不以不安全部署换形式合规 |
| C2 PR | 当前可修复；历史每功能 worktree 不可追补 | 本 Task 创建正式 PR；PLAN 明示历史偏差 |
| C3 subagent/双评审 | 当前双评审可补，历史逐 task 流程不可倒签 | 保存本次双评审；历史仍标偏差 |
| M1 冷启动 diff | 有效 | 新增测试红灯；从真实提交 `57fc02f` 提取关键 unified diff；测试转绿 |
| M3 GitLab CI | 附件范围导致的误报 | 仓库实际存在 `.gitlab-ci.yml`，`tests/test_readme_security.py` 自动验证 `unit-test` |
| M4 REFLECTION | 有效课程缺口，但课程禁止 AI 代写 | 留给学生本人完成，不由 Agent生成 |
| Minor commit 标注 | 历史事实不可通过改写 commit message 安全修复 | PR 描述明确 Codex/OpenCode/人工责任 |

## 修复证据

- `tests/test_course_documents.py::test_cold_start_process_contains_real_diff_and_irreversible_deviation` 先失败，补充真实 diff 后通过。
- `SPEC_PROCESS.md` 记录 `57fc02f` 的关键增加行。
- `PLAN.md` 明确“课程 §4.6 的历史偏差无法通过后补改写为合规历史”。

## 结论

可以创建 PR 以解决 PR/CI/合并链本身，但不能把项目宣称为课程最终完全合规。剩余课程缺口是安全线上部署、学生本人反思和不可逆的历史流程偏差。

