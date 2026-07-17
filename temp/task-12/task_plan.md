# Task Plan: Task 12 CI、README 与发布验证

## Goal

交付有安全说明、自动 CI 和真实冷启动证据的可发布版本。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 Task 12、当前 README/CI/Docker/反思边界
- [x] 明确最终发布验证命令和证据
- **Status:** complete

### Phase 2: Tests First
- [x] 编写 README/CI 安全与完整性测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Documentation & CI
- [x] 编写完整 UTF-8 README
- [x] 实现 GitLab unit-test 与 docker-build jobs
- **Status:** complete

### Phase 4: Release Verification
- [x] 完整 pytest -v
- [x] 直接运行 Mock 演示
- [x] 重建镜像并真实冷启动/HTTP/日志验证
- [x] 检查工作树和凭据模式
- **Status:** complete

### Phase 5: Delivery
- [x] 更新 PLAN/AGENT_LOG/过程文件
- [x] 使用 verification-before-completion 复核证据
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. CI 平台用什么？答：按课程清单实现 `.gitlab-ci.yml`；仓库在 GitHub 不改变当前任务的明确文件要求。
2. Docker 冷启动如何避免真实网络？答：传入无效本地兼容端点和测试占位 key；启动阶段不发模型请求，只验证 Web 首页。
3. Reflection 如何处理？答：保留占位说明，由学生基于真实过程自行完成。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| README 中文、命令保持原样 | 与课程/用户语言一致且便于复制 |
| CI 分 test/build 两阶段 | 测试先通过再构建镜像 |
| 冷启动检查 HTTP 200 与日志 key 缺失 | 同时验证可用性与最小安全条件 |
| 不修改 Reflection 正文 | 个人反思必须由学生本人完成 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| 暂无 | 1 | — |

## Notes

- 过程 Markdown 全部位于 `temp/task-12/`。
