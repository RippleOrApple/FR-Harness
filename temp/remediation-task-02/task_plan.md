# Task Plan: 完整课程 SPEC

## Goal

形成覆盖通用十项结构与 A 类领域机制的可验收规格。

## Current Phase

Complete

## Phases

### Phase 1: Discovery

- [x] 阅读两份课程要求与现有 SPEC
- [x] 映射缺失章节
- **Status:** complete

### Phase 2: TDD RED

- [x] 写结构与内容断言
- [x] 确认旧 SPEC 三项红灯
- **Status:** complete

### Phase 3: Rewrite

- [x] 重组并补写 SPEC
- [x] 保留规范性接口
- **Status:** complete

### Phase 4: Verify & Deliver

- [x] 运行文档测试和全量测试
- [x] 更新证据并准备提交
- **Status:** complete

## Decisions Made

| Decision | Rationale |
|---|---|
| 十项通用结构 + 独立领域机制章 | 直接对应评分清单 |
| 用测试检查标题和关键机制 | 防止后续文档漂移 |

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 旧 SPEC 缺章节、故事和选型证据 | 1 | 按十项结构重写并保留机制接口 |
