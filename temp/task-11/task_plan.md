# Task Plan: Task 11 MockLLM 机制演示

## Goal

交付严格三行输出、离线且确定性的核心机制演示。

## Current Phase

Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] 核对 Agent、审批、工具和 MockLLM 公共接口
- [x] 设计两个 TemporaryDirectory 内的独立场景
- **Status:** complete

### Phase 2: Tests First
- [x] 编写脚本子进程和源码安全测试
- [x] 观察有效红灯
- **Status:** complete

### Phase 3: Implementation
- [x] 实现审批与一次性场景
- [x] 实现反馈修复场景
- [x] 控制 stdout 为规定三行
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 直接运行脚本
- [x] 定向与完整测试通过
- [x] 重复运行检查确定性
- **Status:** complete

### Phase 5: Delivery
- [x] 更新计划、日志和过程文件
- [x] 审查并提交
- **Status:** complete

## Key Questions

1. 反馈场景如何处理默认 pytest 审批？答：使用注入的 allow_all 表示该隔离场景的危险动作已获外部授权；默认生产分类器不变。
2. 是否复用同一任务展示三项？答：审批与一次性复用一个任务，反馈修复用另一个，避免状态干扰。

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 失败时抛 AssertionError | 子进程自然返回非零且测试获得明确失败 |
| 先计算三个布尔结果，最后统一打印 | 避免半途失败留下误导性 PASS |
| 直接检查事件 passed 序列 | 证明反馈机制而非只检查最终状态 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| Windows TemporaryDirectory 无法删除 SQLite | 1 | 先修 Database 显式关闭；复验仍失败后定位 MemoryStore 直连并同样显式关闭 |

## Notes

- 过程 Markdown 全部位于 `temp/task-11/`。
