# Task Plan: Task 10 CLI、安全配置与 Docker

## Goal

交付安全、不泄密、可容器化的本地管理入口。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 CLI、环境变量和 Docker 验收要求
- [x] 检查当前空配置文件和依赖
- **Status:** complete

### Phase 2: Tests First
- [x] 编写 init/serve/test 与分发文件测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Implementation
- [x] 实现 argparse CLI
- [x] 实现安全环境读取与 Uvicorn 启动
- [x] 补齐 Docker/.dockerignore/.env.example
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 定向和完整测试通过
- [x] 扫描配置与输出不含测试 secret
- [x] 执行 docker build
- **Status:** complete

### Phase 5: Delivery
- [x] 更新计划、日志、过程文件
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. 缺少 LLM 配置如何处理？答：serve 返回非零并给出不含变量名/值的通用错误。
2. `.env` 是否自动加载？答：加载到进程环境，但所有读取统一经 `os.environ`，且绝不打印。
3. Docker 是否安装开发依赖？答：运行镜像只安装项目运行依赖；CI/本地测试另行安装 `.[dev]`。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| main(argv) 返回整数 | 易于离线单元测试和模块入口退出码 |
| uvicorn.run 接收 app 对象 | 复用 create_app 及依赖注入 |
| test 子命令固定参数数组 | 阻断 shell 注入 |
| `.dockerignore` 排除 `temp/` | 过程记录不是运行镜像所需内容 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| Docker 客户端无法连接 Desktop Linux Engine | 1 | 检查服务/安装，后台启动 Docker Desktop，确认 Engine 29.6.1 后重试成功 |

## Notes

- 过程 Markdown 全部位于 `temp/task-10/`。
