# FR-Harness 对话问题、解决步骤与设计记录

记录日期：2026-08-04  
范围：本记录整理了围绕 FR-Harness 项目从理解需求、运行调试、模型接入、CLI 简化、审批体验、CI/PR、Release 交付到空工作区任务修复的主要讨论、问题、解决步骤和设计决策。  
隐私说明：本文档刻意使用 `<FR-Harness>`、`<目标项目>`、`<临时项目>` 等占位符，不记录本机绝对路径、用户名、API Key、Token、邮箱等敏感信息。

## 1. 项目目标理解

### 1.1 项目要做什么

FR-Harness 是一个面向编程修复任务的 Agent Harness。它的核心目标是：

- 接收一个工作区路径和一个自然语言修复目标。
- 让 LLM Agent 通过受控工具读取文件、写入文件、运行 pytest。
- 在修改已有文件或执行测试前提供审批机制。
- 记录任务执行过程、工具调用、审批与测试结果。
- 最终使目标项目的测试通过，并形成可审计的修复流程。

项目当前主要面向 Python 项目，核心判断标准是运行 pytest 是否通过。

### 1.2 是否只支持 Python 符合作业要求

讨论结论：

- 如果作业 A 的要求是实现 Agent Harness，而不是要求覆盖所有语言，那么先支持 Python + pytest 是可以接受的。
- 需要在 README、SPEC、PLAN 等文档中明确说明当前范围：本版本聚焦 Python 项目和 pytest 工作流。
- 后续可以把多语言支持作为扩展方向，例如 Node.js + npm test、Java + Maven/Gradle、通用 shell 测试命令等。

设计取舍：

- 当前以 Python 为主，能降低实现复杂度，便于展示工具调用、审批、测试闭环。
- 不把多语言支持写成已经完成，避免文档与实际功能不一致。

## 2. 本地运行与临时项目验证

### 2.1 初始本地运行方式

最初的运行方式是进入 `<FR-Harness>` 后，通过虚拟环境 Python 执行：

```powershell
.\.venv\Scripts\python.exe -m fr_harness.cli serve
```

或运行 CLI 演示：

```powershell
.\.venv\Scripts\python.exe -m fr_harness.cli demo
```

后续为了更易用，增加了命令入口和 Windows 快捷启动脚本。

### 2.2 创建第一个临时小项目

为了测试 Harness 能否修复目标项目，创建了一个简单 Python 临时项目。

目标：

- 构造一个能被 pytest 捕获的失败用例。
- 让 Agent 读取项目、修改代码、运行 pytest。
- 验证审批、工具调用和任务状态记录是否正常。

结果：

- 初步验证了任务创建、运行和失败日志展示流程。
- 也暴露了 API 配置和兼容模型调用的问题。

### 2.3 创建更复杂、错误更隐蔽的临时项目

后续又创建了一个更复杂的购物车折扣计算项目。

项目特征：

- 包含 README，描述业务规则。
- 包含边界条件和隐藏式业务错误。
- 让 Agent 需要根据 README 理解规则，而不是只靠测试错误机械修改。

业务规则大意：

- 每个商品包含 `name`、`unit_price`、`quantity`。
- 总价满一定金额时有满减折扣。
- 使用优惠券时继续扣减优惠券金额。
- 最终应付金额不能低于 0。
- 金额统一四舍五入到 2 位小数。

结果：

- 项目用于验证 Agent 是否能结合 README、源码和 pytest 输出完成修复。
- 同时暴露出 WebUI 审批信息不够直白的问题。

## 3. API Key、模型服务与 DeepSeek 接入

### 3.1 API credential 不能为空

遇到的问题：

```text
API credential:
credential cannot be empty
```

原因：

- 启动服务时需要 LLM API 凭据。
- 用户直接回车或未配置凭据，导致 credential 为空。

解决方向：

- 在 CLI 交互中提示用户输入 API Key。
- 支持通过 `.env` 或凭据命令保存配置。
- 增加 `credential status`、`credential set`、`credential update`、`credential clear` 等命令。

### 3.2 API Key 是否只能使用 OpenAI

讨论结论：

- 不一定只能使用 OpenAI。
- 只要模型服务兼容 OpenAI-style Chat Completions API，理论上可以接入。
- 关键是要配置正确的 Base URL、模型名和 API Key。

国产或第三方模型服务方向：

- DeepSeek
- 通义千问兼容接口
- 智谱 GLM 兼容接口
- Moonshot/Kimi 兼容接口
- 本地 OpenAI-compatible proxy

注意：

- 不同平台虽然声称兼容 OpenAI 格式，但 endpoint、模型名、鉴权头、tool calling 支持细节可能不同。
- Agent Harness 对 tool calls 依赖较强，因此模型必须能稳定输出工具调用或至少能被适配成工具调用格式。

### 3.3 DeepSeek UnsupportedProtocol 错误

错误表现：

```json
{
  "error_type": "UnsupportedProtocol",
  "reason": "llm error"
}
```

判断原因：

- Base URL 很可能缺少协议头。
- 例如写成 `api.deepseek.com`，而不是 `https://api.deepseek.com`。

解决步骤：

1. 检查 `.env` 或配置文件中的 Base URL。
2. 确认它以 `https://` 开头。
3. DeepSeek 常见 OpenAI-compatible Base URL 应形如：

```env
OPENAI_BASE_URL=https://api.deepseek.com
```

4. 重新启动 CLI 或 WebUI，使环境变量生效。

### 3.4 DeepSeek HTTPStatusError 错误

错误表现：

```json
{
  "error_type": "HTTPStatusError",
  "reason": "llm error"
}
```

判断方向：

- URL 协议问题修好后，请求到达服务端，但服务端返回了非 2xx 状态码。
- 常见原因包括 API Key 错误、模型名错误、余额不足、权限不足、请求格式不符合服务商要求。

解决步骤：

1. 核对 API Key 是否完整。
2. 核对 Base URL 是否是兼容 Chat Completions 的入口。
3. 核对模型名，例如 DeepSeek 可能需要 `deepseek-chat` 或服务商文档指定名称。
4. 用最小请求验证服务是否可用。
5. 在 Harness 中统一读取 `.env` 中的 Base URL、模型名和凭据。

### 3.5 模型名是否放在 `.env`

讨论结论：

- 是，模型名适合放在 `.env`。
- 这样用户不需要每次运行都输入。

配置设计：

```env
OPENAI_API_KEY=你的_api_key
OPENAI_BASE_URL=https://api.example.com
OPENAI_MODEL=模型名
```

原则：

- `.env` 不提交到仓库。
- `.env.example` 提交，用作示例。
- README 中说明配置项用途，但不写真实密钥。

## 4. 配置和使用简化设计

### 4.1 初始问题

用户反馈：

- 每次运行都要打开终端、输入命令、配置环境，太麻烦。
- 新用户克隆项目后不知道先安装依赖、创建虚拟环境、再运行命令。
- README 中写了 `fr-harness demo` 等命令，但在未安装包或未激活环境时不能直接运行，容易误解。

目标：

- 让 Windows 用户尽量双击脚本即可开始。
- 让后续 CLI 命令能在新打开的终端里直接使用。
- 避免永久污染系统 PATH。
- 缺少 `.venv` 时自动创建和安装。

### 4.2 讨论过的模式

#### 模式 A：快捷启动 CMD

特点：

- 提供 `启动 FR-Harness.cmd`。
- 用户双击即可启动。
- 自动检查 Python。
- 自动创建 `.venv`。
- 自动安装项目依赖。
- 打开新的终端窗口。
- 在新终端里临时加入 `.venv\Scripts` 到 PATH。
- 自动运行 `fr-harness run`。
- 菜单退出后终端不关闭，用户还能继续执行 `fr-harness demo`、`fr-harness doctor` 等命令。

优点：

- 最适合 Windows 新手。
- 使用门槛低。
- 不需要手动激活虚拟环境。
- 不永久修改系统环境变量。

缺点：

- 主要服务 Windows。
- 脚本需要处理 PowerShell 与 CMD 的路径差异。

最终选择：

- 用户选择了模式 A。
- 已实现并合入 PR。

#### 模式 B：安装后全局命令

特点：

- 用户执行安装命令后，系统可以直接识别 `fr-harness`。
- 类似普通 Python CLI 工具。

优点：

- 更符合成熟 CLI 发布方式。
- 适合 Release 包和 pip 安装。

缺点：

- 对新手不如双击脚本友好。
- 涉及 PATH、pipx、虚拟环境等概念。

#### 模式 C：交互式 setup

特点：

- 提供 `fr-harness setup`。
- 引导填写 API Key、Base URL、模型名。
- 可选择配置完成后自动启动。

优点：

- 配置集中，体验清晰。
- 可以和 `doctor` 配合做诊断。

缺点：

- 用户仍需要先能运行 `fr-harness` 命令。
- 因此适合与模式 A 或 B 配合，而不是单独承担全部首次启动体验。

### 4.3 最终配置简化方案

最终方案组合：

- 使用 `启动 FR-Harness.cmd` 做 Windows 一键入口。
- 保留 `fr-harness setup` 做交互式配置。
- 保留 `.env` 做可编辑配置。
- 保留 `fr-harness doctor` 做诊断。
- README 同时说明源码运行方式和 Release 使用方式。

## 5. Windows 启动脚本问题与修复

### 5.1 CMD 运行后闪退

问题：

- 用户双击 CMD 后窗口闪退。
- 网站没有打开。
- 看不到错误原因。

修复方向：

- 脚本末尾保持新终端窗口打开。
- 出错时打印错误并暂停。
- 自动启动 CLI 菜单而不是直接退出。

### 5.2 PowerShell 中 `cd /d` 报错

错误表现：

```text
Set-Location : 找不到接受实际参数“<路径>”的位置形式参数。
cd /d <路径> ; ...
```

原因：

- `cd /d` 是 CMD 语法。
- 在 PowerShell 中 `cd /d` 会被解释为 `Set-Location`，`/d` 被当成多余参数，从而报错。

修复设计：

- 不在 PowerShell 中使用 `cd /d`。
- PowerShell 使用：

```powershell
Set-Location -LiteralPath "<项目根目录>"
```

- CMD 中才使用：

```cmd
cd /d "%PROJECT_ROOT%"
```

隐私要求：

- 修复时同时扫描项目，避免代码和文档中暴露用户本机绝对路径。
- 文档使用相对路径或占位符。

### 5.3 缺少 `.venv` 时报错

错误表现：

```text
.\.venv\Scripts\python.exe : 无法将“.\.venv\Scripts\python.exe”项识别为 cmdlet、函数、脚本文件或可运行程序的名称。
```

原因：

- 新克隆的项目没有 `.venv`。
- README 中的命令假设用户已经完成了虚拟环境创建和依赖安装。

修复设计：

- 快捷启动脚本检测 `.venv\Scripts\python.exe` 是否存在。
- 不存在时自动：
  - 查找 Python 3.12+。
  - 创建 `.venv`。
  - 升级 pip。
  - 安装项目依赖。
  - 将 `.venv\Scripts` 临时加入 PATH。

### 5.4 能否在项目文件夹下直接运行 `fr-harness demo`

讨论结论：

- 如果直接打开普通终端，未安装项目或未激活虚拟环境时，`fr-harness demo` 不一定能运行。
- 如果通过 `启动 FR-Harness.cmd` 打开的终端，则脚本会临时配置 PATH，因此在该终端内可以直接运行：

```powershell
fr-harness demo
fr-harness doctor
fr-harness run
fr-harness --version
```

README 需要明确区分：

- 源码克隆后首次使用：推荐双击启动脚本。
- 已安装 Release 或已安装到环境中：可以直接运行 `fr-harness` 命令。

## 6. CLI 使用方式整理

### 6.1 推荐 Windows 源码使用方式

1. 克隆或解压项目源码。
2. 双击：

```text
启动 FR-Harness.cmd
```

3. 脚本自动准备环境并进入菜单。
4. 菜单退出后，当前新终端仍可继续运行：

```powershell
fr-harness run
fr-harness demo
fr-harness doctor
fr-harness setup
```

### 6.2 常用 CLI 命令

```text
fr-harness                     启动交互式菜单
fr-harness run                 启动交互式菜单
fr-harness demo                运行离线机制演示
fr-harness --version           显示版本
fr-harness setup [--no-start]  交互配置
fr-harness doctor              配置与模型自检
fr-harness serve               启动本地 WebUI
fr-harness init                初始化数据库
fr-harness test                运行源码测试套件
fr-harness credential set      保存凭据
fr-harness credential status   查看凭据状态
fr-harness credential update   更新凭据
fr-harness credential clear    清除凭据
```

### 6.3 README 命令可运行性的解释

问题：

- README 中列出了 `fr-harness demo` 等命令。
- 用户在新克隆目录中直接运行时失败。

解释：

- 这些命令是 CLI 安装完成后的命令。
- 新克隆源码还没有自动安装到当前环境。
- 因此需要先运行启动脚本、安装依赖或激活虚拟环境。

文档修复方向：

- 在 README 中把“首次使用”和“已安装后使用”分开。
- 明确说明启动脚本会创建临时可用的命令环境。

## 7. WebUI 与审批页面体验

### 7.1 Pending approval 提示不明显

问题：

- WebUI 的待审批页面显示 JSON。
- 用户看到 `kind: run_pytest` 等字段，不直观。
- 页面上的任务链接只显示 UUID，不适合普通用户理解。

改进目标：

- 把机器字段转换成人类可读描述。
- 显示更明确的审批意图。
- 使用任务标题或目标摘要代替裸 UUID。

### 7.2 kind 描述改造

原始显示类似：

```json
{
  "kind": "run_pytest",
  "path": null,
  "content": null,
  "reason": null
}
```

目标显示：

- 操作类型：运行测试
- 影响范围：当前任务工作区
- 说明：Agent 想运行 pytest 检查项目是否通过
- 风险提示：pytest 会执行工作区中的 Python 代码，请只对可信项目授权

设计结果：

- `read_file` 显示为“读取文件”。
- `write_file` 显示为“修改文件”或“创建文件”。
- `run_pytest` 显示为“运行测试”。
- 审批按钮文案更直白，例如“批准并继续”“拒绝并取消任务”。

### 7.3 任务显示不应只显示 ID

问题：

- Pending approval 页面中的任务以 UUID 展示。
- 对用户来说没有识别意义。

讨论结论：

- 使用任务目标摘要作为主要显示。
- UUID 可以作为次要信息或详情信息。
- 例如：

```text
任务：修复购物车折扣计算项目
工作区：<目标项目>
操作：运行测试
```

实现方向：

- 任务列表和审批卡片优先显示目标摘要。
- 保留任务 ID 用于调试和唯一定位。

## 8. pytest 缓存与目标目录污染

### 8.1 `.pytest_cache` 是否每次都会创建

问题：

- 用户发现目标项目目录中会出现 `.pytest_cache`。
- 询问是否每次都会创建。

原因：

- pytest 默认会写入 `.pytest_cache`。
- Harness 在目标工作区运行 pytest，因此缓存会出现在目标项目里。

解决方案：

- 修改运行 pytest 的命令，加入禁用缓存参数。

```powershell
python -m pytest -q -p no:cacheprovider
```

效果：

- 避免在目标项目里创建 `.pytest_cache`。
- 减少对用户项目的非必要污染。

文档同步：

- README、SPEC 或相关文档中说明 Harness 会尽量避免写入测试缓存。

## 9. 复杂临时项目失败与修复

### 9.1 失败现象

在购物车折扣项目中，任务失败，WebUI 日志显示 Agent 有读取 README、运行 pytest、修改文件等动作，但最终未通过。

可能原因：

- LLM 输出不稳定。
- 任务轮次不足。
- 工具反馈不够明确。
- 审批或错误信息不够直观，用户难以判断下一步。

处理方式：

- 通过查看日志定位 Agent 的工具调用流程。
- 改进审批显示和工具结果提示。
- 调整 README 和测试项目，让错误隐蔽但规则清晰。

## 10. 空工作区创建任务失败

### 10.1 用户目标

用户希望在一个空工作区中创建斐波那契数列计算程序：

- 创建 `fibonacci.py`。
- 实现 `fibonacci(n)`。
- 创建 `test_fibonacci.py`。
- 使用 pytest 测试 `n=0`、`n=1`、`n=2`、`n=10` 和负数输入。
- 运行 pytest 直到通过。

### 10.2 第一次失败原因

用户输入简短目标：

```text
创建斐波拉数列计算
```

Agent 行为：

- 尝试读取 `README.md`。
- 读取失败。
- 尝试运行 pytest。
- pytest 显示 no tests ran。
- 尝试读取 `app.py`。
- 再次失败。

根因：

- Harness 默认假设目标工作区已有项目文件。
- Prompt 引导 Agent 读取 README 或常见入口文件。
- 空工作区没有文件，导致 Agent 不知道应该先创建文件。

### 10.3 第二次失败原因

用户明确说明这是空工作区，并要求先创建文件和测试。

Agent 行为：

- 创建了 `fibonacci.py`。
- 立即运行 pytest。
- 因为没有测试文件，pytest 输出 `no tests ran`。
- Agent 反复修改 `fibonacci.py`，没有创建 `test_fibonacci.py`。

根因：

- 工具反馈存在冲突：`write_file completed` 后提示下一步应 `run_pytest`。
- 即使用户要求创建测试，Harness 的上下文仍过度鼓励写完源文件后马上运行 pytest。
- Harness 没有工作区文件清单，无法明确告诉模型“当前还没有测试文件”。

### 10.4 空工作区修复设计

新增设计：

- 在每轮 Agent 上下文中加入工作区文件清单。
- 如果工作区为空，明确提示：
  - 这是空工作区。
  - 不要猜测读取 `README.md` 或 `app.py`。
  - 需要先用 `write_file` 创建源文件。
  - 还需要创建 pytest 测试文件。
- 如果写入源文件后还没有测试文件，下一步必须创建测试文件。
- 如果已有测试文件，下一步才运行 pytest。
- 如果 pytest 输出 `no tests ran` 或 `collected 0 items`，下一步必须创建测试文件。

### 10.5 代码改动方向

新增或调整：

- `workspace_inventory(root, limit=100)`：
  - 扫描工作区文件。
  - 忽略 `.git`、`.venv`、`__pycache__`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、coverage 等目录。
  - 返回相对路径。
  - 优先展示 pytest 测试文件。

- `has_pytest_files(paths)`：
  - 判断工作区是否已有 pytest 文件。
  - 支持 `test_*.py` 和 `*_test.py`。

- `build_context(..., workspace_files=None)`：
  - 空工作区时给出 greenfield 指令。
  - 非空工作区时列出文件清单。
  - 写入后根据是否已有测试文件决定下一步。
  - 遇到 no tests ran 时要求创建测试文件。

- `Agent.run_once`：
  - 将工作区文件清单传入上下文构建。

- `ToolDispatcher`：
  - 空工作区读取缺失文件时，提示使用 `write_file` 创建文件。
  - 非空工作区读取缺失文件时，保留原有修复提示。
  - `write_file` 的返回提示根据测试文件存在与否动态变化。

### 10.6 验证结果

验证内容：

- 新增确定性测试，覆盖空工作区 Fibonacci 流程。
- 本地测试通过。
- `fr-harness demo` 通过。
- CI 中 unit-test 和 docker-build 通过。

相关 PR：

- 创建了后续修复 PR，用于支持空工作区创建任务。
- 该 PR 处于 Draft 状态，用于合并前检查。

## 11. Git、PR 与 CI 处理记录

### 11.1 PR 失败处理

用户多次反馈 PR 检查失败：

- unit-test 失败。
- docker-build 成功。
- publish-image skipped。

处理流程：

1. 查看 GitHub PR 检查状态。
2. 获取 CI 日志。
3. 在本地复现测试失败。
4. 修改代码或测试。
5. 重新运行本地测试。
6. 提交 commit。
7. 推送分支。
8. 等待 CI 重新运行。

结果：

- 对应 PR 的 unit-test 修复后通过。
- docker-build 通过。
- publish-image 跳过属于预期情况。

### 11.2 PR #9

主要内容：

- 一键启动 CMD。
- CLI 命令入口。
- README 源码使用说明。
- Windows 首次使用体验优化。

状态：

- 已合入 main。

### 11.3 PR #10

主要内容：

- 支持空工作区创建任务。
- 修复 Agent 在无测试文件时反复改源文件的问题。
- 增加工作区 inventory。
- 更新 README 的空工作区说明。

状态：

- 已创建 Draft PR。
- CI 检查通过。

## 12. Release 交付方案讨论

### 12.1 助教说明

作业 A 允许两种提交方式：

- 方案一：只提供 CLI，不继续开发 WebUI，提供托管平台 Release 链接。
- 方案二：提供 WebUI 和 CLI，WebUI 链接供检查访问。

### 12.2 最终选择

用户选择：

- 采用方案一。
- 重点完善 CLI。
- 创建 GitHub Release 链接作为交付入口。

### 12.3 Release 前需要完成的事项

应完成：

- README 完整更新。
- CLI 使用方式明确。
- Release 包可下载。
- `fr-harness demo` 可运行。
- `fr-harness doctor` 可诊断配置。
- `.env.example` 不含真实密钥。
- 文档不含本机绝对路径。
- 敏感信息扫描。
- CI 通过。

## 13. 文档与隐私清理

### 13.1 绝对路径问题

用户明确指出：

- 项目中不能存在暴露个人信息的绝对路径。
- 文档也不能暴露本机路径。

处理原则：

- 代码中使用相对路径、项目根路径自动推导或用户输入路径。
- 文档中使用：
  - `<FR-Harness>`
  - `<目标项目>`
  - `<工作区>`
  - `<Release 页面>`
- 不记录真实用户名、磁盘目录、API Key、Token、邮箱。

### 13.2 `.gitignore` 更新

已加入或确认忽略：

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
*.sqlite3
*.egg-info/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/
build/
dist/
logs/
temp/
release/*.zip
release/*.sha256
```

其中 `temp/` 是后续根据用户要求追加的临时目录忽略规则。

## 14. README 更新方向

README 需要覆盖：

- 项目简介。
- 功能范围。
- 安装方式。
- Windows 一键启动。
- CLI 命令。
- `.env` 配置。
- DeepSeek 等 OpenAI-compatible 服务配置。
- `doctor` 自检。
- `demo` 离线演示。
- `serve` WebUI 可选说明。
- 空工作区创建任务说明。
- pytest 缓存处理。
- Docker 使用。
- 安全与隐私说明。
- Release 交付说明。

重点改进：

- 区分“源码克隆后首次运行”和“安装后命令运行”。
- 不再让用户误以为新克隆后一定可以直接运行裸 `fr-harness`。
- 对 Windows 用户优先推荐 `启动 FR-Harness.cmd`。

## 15. CLI 目标体验

理想首次体验：

1. 用户下载或克隆项目。
2. 双击 `启动 FR-Harness.cmd`。
3. 自动准备环境。
4. 自动进入交互菜单。
5. 用户输入目标工作区。
6. 用户输入修复目标。
7. CLI 显示任务确认。
8. CLI 在运行 pytest 前请求授权。
9. CLI 在修改已有文件前显示审批。
10. CLI 逐轮显示：
    - 读取文件
    - 创建文件
    - 修改文件
    - 运行测试
    - 测试通过或失败
11. 成功时清晰显示任务完成。

## 16. 后续待办建议

### 16.1 可以继续优化的功能

- 让 CLI 自动识别空工作区并询问是否创建新项目。
- 增加任务模板，例如：
  - 创建函数库
  - 修复 pytest
  - 添加测试
  - 根据 README 实现功能
- 支持用户选择测试命令，而不是固定 pytest。
- 增加 dry-run 模式。
- 增加更详细的失败原因显示。
- 增加任务日志导出。
- Release 自动打包脚本。

### 16.2 作业提交前建议检查

- main 分支 CI 全绿。
- 最新 Release 已创建。
- Release 页面包含压缩包和简要使用说明。
- README 中的命令实际可运行。
- `.env.example` 无真实密钥。
- 文档无本机绝对路径。
- 演示视频或截图不暴露敏感信息。
- `fr-harness demo` 输出正常。
- `fr-harness doctor` 对配置错误有清晰提示。

## 17. 总结

本轮围绕 FR-Harness 完成了从“能跑”到“更容易给助教检查和给普通用户使用”的多轮改造。核心变化包括：

- 明确项目范围：Python + pytest Agent Harness。
- 支持 OpenAI-compatible 模型服务，重点调通 DeepSeek 配置路径。
- 引入 `.env`、setup、doctor 等配置体验。
- 增加 Windows 一键启动脚本。
- 修复 PowerShell 路径命令兼容问题。
- 改进 CLI 命令可用性说明。
- 改进审批页面和操作描述。
- 避免 pytest 缓存污染目标目录。
- 支持空工作区创建新 Python 项目。
- 推进 PR、CI 和 Release 交付方案。

后续重点应放在最终 Release、README 最终检查、敏感信息扫描和作业提交材料整理上。
