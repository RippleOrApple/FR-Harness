# 目标

## 目标说明

把 FR-Harness 完善为可独立验收的中文交互式 CLI，并通过 GitHub Release 发布 Windows x64 单文件 EXE。

## 范围

- 无参数或 `run` 进入持续运行的中文主菜单。
- 配置缺失时自动进入 setup，成功后返回原流程。
- 新建任务默认使用当前目录，目标为单行输入。
- pytest 采用任务级一次授权，文件覆盖保持逐次审批。
- CLI 提供变更摘要、按需 diff、测试摘要和按需完整日志。
- 等待审批与暂停任务可恢复，终态任务只读。
- EXE 使用用户本地应用数据目录，API Key 继续使用 Windows Credential Manager。
- 保留 `serve` 作为本地 WebUI 可选能力。
- 发布 Windows x64 ZIP、SHA-256 和 GitHub Release。
- 清理当前版本中的本机路径和个人信息，并更新课程文档。

## 非目标

- 不部署公网 WebUI。
- 不实现 Windows ARM64、macOS 或 Linux 桌面发行包。
- 不增加任意 shell、多用户、后台队列或多进程任务执行。
- 不重写公开 Git 历史；只扫描、记录并清理当前版本，历史重写需要单独授权。
- 不代写学生个人反思正文。

## 验收标准

- 新增行为均有先失败后通过的确定性测试。
- 完整 pytest、MockLLM 演示、Windows EXE 冒烟测试和 Docker 验证通过。
- EXE 在隔离数据目录中运行 `--help`、`--version` 和 `demo`。
- GitHub Actions 能从 `v1.0.0` 标签创建公开 Release。
- README、SPEC、PLAN、AGENT_LOG 与最终行为一致。
- 当前跟踪版本没有本机绝对路径或凭据形状命中。
- 过期 PR #5 关闭，并说明由后续实现取代。

## 约束

- Python 3.12 或更高，界面文字使用中文。
- 不在代码和文档中写死用户名或本机绝对路径。
- pytest 始终使用固定参数、`shell=False` 和 `-p no:cacheprovider`。
- API Key 不得进入配置文件、数据库、日志、diff、终端输出或 Git。
- 保留现有 Agent 主循环，不在 CLI 复制决策逻辑。

