# Task 12 目标：CI、README 与发布验证

## 目标

交付可复现的测试/镜像 CI、完整 UTF-8 使用与安全文档，并用全量测试、确定性演示和真实 Docker 冷启动完成发布验收。

## 范围

- 补齐 `.gitlab-ci.yml` 的 `unit-test` 与镜像构建 job。
- 重写已有 `README.md`，覆盖项目、架构、安装、CLI、WebUI、演示、Docker、安全、边界、限制和目录结构。
- 新建 `tests/test_readme_security.py`。
- 运行发布验证并记录证据。
- 保留 `REFLECTION.md` 为学生本人撰写，不生成反思正文。

## 验收标准

1. README 可用 UTF-8 读取，包含 `OPENAI_API_KEY`、`.env`、`明文`、`docker build`。
2. README 明确 key 不进源码/Git/SQLite/日志，解释 `.env` 明文风险和工作区边界。
3. `.gitlab-ci.yml` 有精确名为 `unit-test` 的 job，安装 `.[dev]` 后运行 `python -m pytest -v`；另有 Docker build job。
4. 完整 `python -m pytest -v` 通过。
5. `python demo/mock_repair_demo.py` 输出三行 PASS。
6. 重建 `fr-harness:local`，容器启动后 Web 首页返回 200，容器日志不含测试 key，最后清理容器。
7. 更新计划/日志并提交 `docs: add release and security guide`。

## 非目标

- 不代写课程要求的个人反思，不推送远端或创建 PR。
