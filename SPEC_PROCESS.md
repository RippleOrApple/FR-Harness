# FR-Harness 规格形成过程

## 0. 证据与记录原则

本文区分两类证据：

- **直接记录**：当前可见会话、OpenCode 输出、仓库文件或 Git commit 可以直接证明。
- **回顾性整理**：早期会话的完整问答已经无法逐字恢复，只依据仍可见的用户指令、批准结果和 Git 历史概括。

回顾性整理不等同于逐字稿。本文不伪造不存在的提问、subagent、评审或用户原话；无法证明的措辞会明确说明证据局限。

## 迭代 1：从 A 路线到轻量单进程 Harness

**证据类型：回顾性整理。**

- **AI 建议：** 比较轻量单进程、事件队列和多 Agent 三类架构，把治理、反馈和记忆做成可离线测试的代码，而不是把课程重点放在模型能力或提示词。
- **用户判断：** 选择 A 类 Coding Agent Harness，并批准轻量单进程方向及治理作为主要贡献。早期连续的数字选择和“可以/符合”可以证明发生过取舍和批准，但当前记录不能可靠恢复每个数字对应的完整选项文本。
- **修订：** SPEC 将首版范围收敛为 Python、pytest、FastAPI、SQLite、MockLLM、OpenAI 兼容适配器和 Docker；明确不做多 Agent、队列和语义检索。
- **证据：** `SPEC.md` 的范围、已比较方案；Git 中 `5d08b51`、`295430a` 等早期脚手架提交。

这一轮让“做一个 Agent”变成“实现决策、工具、治理、反馈、记忆与配置六个 Harness 维度”，避免项目退化为 API 包装器。

## 迭代 2：纠正仓库、路径与正式文档结构

**证据类型：回顾性整理，但用户纠正语句仍在会话中可见。**

- **AI 建议：** 早期脚手架使用过通用目录和独立 worktree/docs 组织。
- **用户判断：** 用户纠正项目名为 `FR-Harness`，要求项目结构遵循 A 任务完成指南；随后明确提出直接使用新分支并把内容放到 `FR-Harness`，`SPEC.md` 和 `PLAN.md` 必须是实质内容，`docs/` 可以删除；用户还确认采用 `src/fr_harness/`。
- **修订：** 正式 SPEC/PLAN 移到仓库根目录，包路径固定为 `src/fr_harness/`，实现留在 `setup-scaffold` 功能分支；过程文件按后续要求放入 `temp/`。
- **证据：** Git 提交 `6946fa6 docs: move specification and plan to repository root`、`0961ee1 docs: translate implementation plan to Chinese`，以及当前根目录结构。

这一轮体现人的最终判断：工具提出的通用 Superpowers 目录习惯不能覆盖课程交付结构和用户明确偏好。

## 迭代 3：陌生 Agent 冷启动暴露隐藏接口

**证据类型：直接记录。**

- **AI 建议：** 用户指出 PLAN 没有明确列出“阶段 2：陌生 Agent 冷启动验证”后，主 Agent 把它加入实施前关卡，并使用与 Codex 不同的 OpenCode CLI。
- **用户判断：** 用户允许在命令行使用 OpenCode 补做，要求继续；冷启动只给 SPEC/PLAN，遇到不确定处必须暂停。
- **修订：** 第一次验证暴露 Action/Approval/Memory/Chat 接口不清，SPEC §5.1 和 PLAN 对 Task 4/6 的契约被补齐；第二个全新会话复验后才继续 Task 4。
- **证据：** Git 提交 `e930464`、`57fc02f`、`b901129`；下方两次 OpenCode 记录。

### 冷启动验证（第一次）— 2026-07-16

- 主开发 Agent：Codex App。
- 测试 Agent：OpenCode CLI 1.17.18，模型 `nju/deepseek-v4-flash`。
- 隔离：全新 `--pure` 会话；临时目录只复制 `SPEC.md` 和 `PLAN.md`。
- 指令：评估尚未实施的 Task 4 与 Task 6；不查看代码，不确定即停止。
- 结果：OpenCode 正确复述目标，但提出十个接口/schema 问题，判定不能安全开始。

关键修订前后差异：

| 暂停点 | 修订前 | 修订后 |
|---|---|---|
| `ActionKind` | 文档未列精确枚举 | 固定五个值 |
| Guard/Approval 位置和字段 | 未定义 | 指定模型、枚举和字段 |
| 审批是否依赖 SQLite | 不清楚 | Task 4 纯内存，Task 8 持久化 |
| 路径和覆盖判定 | 只有高层描述 | 固定 `Path.resolve()`、子路径和 `exists()` |
| Memory schema/API | 未定义 | 固定表字段和 `MemoryStore(Database)` |
| Chat 格式 | 只有大致顺序 | 固定 role 与安全/记忆/反馈/目标顺序 |

Git 提交 `57fc02f` 保存了当时的实际修订。以下是从该 commit 提取的关键 diff，而不是事后重写的示意文本：

```diff
+## 5.1 核心数据模型与接口约定
+
+- `ActionKind` 的值固定为：`read_file`、`write_file`、`run_pytest`、`request_approval`、`complete`。
+- `ApprovalStateMachine` 是纯内存类；Task 8 才负责将审批持久化到 SQLite。
+- `resolve_workspace_path(root, value)` 必须对 root 和候选路径调用 `Path.resolve()`。
+- `MemoryStore` 构造函数接收 `Database`；`relevant(task_id, limit)` 按最新优先返回。
+- `build_context(goal, memories, feedback)` 返回 OpenAI Chat 格式并固定消息顺序与 role。

+**实现约定：** `GuardDecision` 与 `Approval` 均定义在 `guardrails.py`；状态机为无数据库依赖的纯内存实现。
+**实现约定：** `MemoryStore(Database)` 接收数据库实例；上下文前三类消息 role 为 `system`，用户目标 role 为 `user`。
```

### 冷启动复验 — 2026-07-16

- 使用另一个全新 OpenCode `--pure` 会话，仍只给更新后的 SPEC/PLAN。
- OpenCode 判断“可以开始”，并准确提出 Task 4 的路径逃逸/未批准测试和 Task 6 的 role/limit 测试。
- 结论：文档消除了阻塞性歧义。

序列偏差：课程要求冷启动发生在任何实现前，但 Task 1–3 当时已经实现。该偏差无法补做成“历史上按时完成”；这里只能如实记录，之后在 Task 4 前完成关卡。

## 迭代 4：前十项补救与凭据架构

**证据类型：直接记录，日期 2026-07-17。**

- **AI 建议：** 对审计发现提出三种方案：最小补丁、评分项驱动补齐、整体重构；推荐每个评分项对应实现、测试、文档和远程证据。凭据比较 `keyring + 环境变量回退`、加密本地文件和 Windows-only Credential Manager。
- **用户判断：** 用户批准 `keyring + 环境变量回退`，随后批准评分项驱动设计，并确认落盘的 `temp/remediation-design.md`。
- **修订：** 形成十项补救：凭据生命周期、完整 SPEC、三轮过程、声明式配置、文档对齐、真实 hash/日志、GitHub Actions、OpenCode 双评审、绿色 CI/合并、公共 GHCR 镜像。
- **证据：** 当前会话的三次明确“可以/批准/确认”；提交 `a661164 docs: add remediation design and plan`；`temp/2026-07-17-remediation-implementation-plan.md`。

这一轮还确定了真实性边界：历史上没有逐 task subagent/two-stage review 的地方只能声明偏差；当前 OpenCode 评审是后补的独立评审，不能倒签为早期评审。

## 5. 建议采纳、修正与推翻

| 建议 | 人的处理 | 原因 |
|---|---|---|
| 轻量单进程架构 | 采纳 | 能把时间用于机制深度和确定性测试 |
| 通用 docs/worktree 布局 | 修正 | 用户要求正式文档在根目录并在当前功能分支工作 |
| 多 Agent 作为产品功能 | 推翻 | 首版会扩大范围且不增强主要治理贡献 |
| OpenCode 第一次“不能开始” | 采纳 | 问题都对应缺失的可执行接口 |
| 把历史流程补齐成形式上的完整 | 推翻 | 违反如实记录与 human-owned 原则 |
| keyring + 环境回退 | 采纳 | 本地安全存储与容器/CI 可移植性兼顾 |

## 6. 对 brainstorming 的反思

### brainstorming 做得好的地方

- 强迫先比较方案和边界，使架构选择可以解释，而不是直接堆功能。
- 分段批准让用户及时纠正项目名、目录、分支和凭据方案。
- 把“公共镜像”拆成发布与匿名拉取两层证据，避免只看到 workflow 就宣称完成。
- 当前补救轮先写设计、再写细粒度计划，为长任务提供了稳定上下文。

### brainstorming 让人不满的地方

- 流程关卡增加轮次；当用户已经要求直接修复时，仍需再次批准落盘设计，体验偏慢。
- 早期选项和批准若没有同步写入过程文件，后续很难恢复精确对话；技能本身不能自动替代证据管理。
- 模板容易诱导形式完整，但不能弥补事实上没有发生的 subagent 或评审。

### 人的最终判断

Brainstorming 能提高问题清晰度，却不能决定课程取舍或证明实现正确。用户负责选择范围和批准风险；开发 Agent 负责提出选项和证据；最终是否采纳 OpenCode 意见、是否把某项标为完成，必须由人依据测试、Git、CI 和公开拉取结果判断。
