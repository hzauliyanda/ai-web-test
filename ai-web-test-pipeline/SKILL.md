---
name: ai-web-test-pipeline
description: >
  一键编排 AI 辅助 Web 测试完整流水线。串联 4 个子 skill：
  p1-web-explorer（探索网站生成功能地图）→ p2-test-case-generator（生成功能测试用例）
  → p3-ui-test-case-generator（生成 UI 自动化用例 + YAML）→ p4-browser-test-runner-devtools（执行测试 + 生成 HTML 报告）。
  支持断点恢复：如果某步骤的产物已存在，自动跳过继续。
  Use when: 用户要求"跑一遍完整测试"、"从探索到报告全流程"、"一键测试"；
  用户说"帮我测试这个系统"、"全自动测试"、"端到端测试流程"。
  不要用于：用户只想执行单个步骤（如只要探索或只要生成用例），此时直接调用对应子 skill。
---

# AI Web 测试流水线

一键编排从网站探索到测试报告的完整流程，串联 4 个子 skill。

## 流水线总览

```
[1] p1-web-explorer            → {项目名}功能地图.md
[2] p2-test-case-generator     → {项目名}-功能测试用例-{date}.md/.xlsx
[3] p3-ui-test-case-generator  → {项目名}-UI测试用例.md + tests/*.yaml + traceability.json
[4] p4-browser-test-runner-devtools → {项目名}-UI自动化测试报告-{date}.html
```

## 步骤 1：收集输入

用 AskUserQuestion 收集核心参数：

```json
{
  "questions": [
    {
      "question": "请输入要测试的业务系统 URL",
      "header": "系统URL",
      "options": [
        {"label": "直接输入 URL", "description": "输入完整的系统地址，如 https://example.com"}
      ],
      "multiSelect": false
    },
    {
      "question": "请输入项目名称（用于文件命名）",
      "header": "项目名",
      "options": [
        {"label": "直接输入", "description": "输入项目名称，如"处罚系统""订单管理""}
      ],
      "multiSelect": false
    },
    {
      "question": "请选择测试产物输出目录",
      "header": "输出目录",
      "options": [
        {"label": "直接输入路径", "description": "输入项目输出目录的完整路径"},
        {"label": "当前目录下新建", "description": "在当前工作目录下创建 {项目名}/ 子目录"}
      ],
      "multiSelect": false
    },
    {
      "question": "请提供参考文档（可选，帮助生成更精准的测试用例，可多选）",
      "header": "参考文档",
      "options": [
        {"label": "需求文档", "description": "产品需求文档路径或 URL（Yuque/本地文件）"},
        {"label": "技术文档", "description": "技术方案/接口文档路径或 URL"},
        {"label": "不提供", "description": "仅基于网站探索结果生成用例"}
      ],
      "multiSelect": true
    }
  ]
}
```

收集完成后，确认登录信息：

```
请确认以下信息：
1. 系统是否需要登录？（是/否）
2. 如需登录，请提供：登录页面 URL、账号、密码、登录类型（普通/SSO）
```

如果用户选择了参考文档，追问具体路径：
- **需求文档**：请提供需求文档路径或 URL
- **技术文档**：请提供技术方案/接口文档路径或 URL

## 步骤 2：创建项目目录 + 初始化状态

```bash
mkdir -p "{输出目录}"
chmod 777 "{输出目录}"
```

创建 `pipeline-state.json` 到输出目录：

```json
{
  "project": "{项目名}",
  "url": "{系统URL}",
  "output_dir": "{输出目录}",
  "login_required": true/false,
  "steps": {
    "explore": { "status": "pending" },
    "generate-cases": { "status": "pending" },
    "generate-ui-cases": { "status": "pending" },
    "execute": { "status": "pending" }
  }
}
```

用 TaskCreate 创建 4 个任务跟踪进度。

## 步骤 3：检查已有产物，确定起点

读取 `pipeline-state.json`，检查每个步骤的产物是否已存在：

| 步骤 | 检查文件 | 如已存在 |
|------|---------|---------|
| explore | `{输出目录}/{项目名}功能地图.md` | 标记 completed，询问用户"功能地图已存在，使用现有文件还是重新探索？" |
| generate-cases | `{输出目录}/{项目名}-功能测试用例-*.md` | 标记 completed，询问是否重新生成 |
| generate-ui-cases | `{输出目录}/{项目名}-UI测试用例.md` + `tests/suite.yaml` | 标记 completed，询问是否重新生成 |
| execute | `{输出目录}/{项目名}-UI自动化测试报告-*.html` | 不跳过，总是重新执行 |

如果所有步骤都已完成，询问用户是否要重新执行。

## 步骤 4：按序执行子 skill

### 4.1 执行 p1-web-explorer

如果 explore 步骤为 pending：

```
使用 Skill 工具调用 p1-web-explorer，传入以下参数：
- 目标 URL: {系统URL}
- 登录要求: {用户提供的登录信息}
- 探索深度: 完整探索
- 输出路径: {输出目录}/{项目名}功能地图.md
```

完成后更新 pipeline-state.json：
```json
"explore": { "status": "completed", "output": "{输出目录}/{项目名}功能地图.md" }
```

更新 TaskCreate 对应任务为 completed。

### 4.2 执行 p2-test-case-generator

如果 generate-cases 步骤为 pending：

```
使用 Skill 工具调用 p2-test-case-generator，传入以下参数：
- 需求文档: {用户提供的文档路径（如有）}
- 技术文档: {用户提供的技术文档路径（如有）}
- 功能地图: {输出目录}/{项目名}功能地图.md
- 输出目录: {输出目录}
- 项目名: {项目名}
```

完成后更新 pipeline-state.json：
```json
"generate-cases": { "status": "completed", "output": "{输出目录}/{项目名}-功能测试用例-{date}.md" }
```

### 4.3 执行 p3-ui-test-case-generator

如果 generate-ui-cases 步骤为 pending：

```
使用 Skill 工具调用 p3-ui-test-case-generator，传入以下参数：
- 功能地图: {输出目录}/{项目名}功能地图.md
- 功能测试用例: {输出目录}/{项目名}-功能测试用例-{date}.md
- 业务系统 URL: {系统URL}
- 登录信息: {步骤1收集的登录信息}
- 覆盖范围: 全部页面
```

完成后更新 pipeline-state.json：
```json
"generate-ui-cases": { "status": "completed", "output": "{输出目录}/{项目名}-UI测试用例.md" }
```

### 4.4 执行 p4-browser-test-runner-devtools

```
使用 Skill 工具调用 p4-browser-test-runner-devtools，传入以下参数：
- YAML 文件路径: {输出目录}/tests/suite.yaml
- 功能测试用例: {输出目录}/{项目名}-功能测试用例-{date}.md
```

p4-browser-test-runner-devtools 会自动处理：
- 浏览器连接验证
- 自动登录（读取持久化配置或首次收集）
- 执行所有场景
- 生成 HTML 覆盖报告

完成后更新 pipeline-state.json：
```json
"execute": { "status": "completed", "output": "{输出目录}/{项目名}-UI自动化测试报告-{date}.html" }
```

## 步骤 5：输出总结

所有步骤完成后，输出总结：

```
✅ 测试流水线执行完成！

📁 项目目录: {输出目录}/
├── {项目名}功能地图.md
├── {项目名}-功能测试用例-{date}.md
├── {项目名}-功能测试用例-{date}.xlsx
├── {项目名}-UI测试用例.md
├── tests/
│   ├── suite.yaml
│   ├── traceability.json
│   ├── s1-xxx.yaml ...
│   └── playwright/                     # Playwright 回归脚本
│       ├── package.json
│       ├── playwright.config.ts
│       ├── auth.setup.ts
│       └── s1-xxx.spec.ts ...
└── {项目名}-UI自动化测试报告-{date}.html

📊 报告已自动在浏览器中打开。

🔄 回归测试:
cd {输出目录}/tests/playwright
npm install && npx playwright install chromium
npx playwright test
```

## 错误处理

- **子 skill 执行失败**：更新 pipeline-state.json 为 `failed`，记录错误信息。告知用户在哪一步失败，建议下一步操作（如"功能地图已生成，可单独运行 /p3-ui-test-case-generator 继续"）
- **浏览器连接失败**：提示用户启动 Chrome 调试模式后重试
- **登录失败**：p4-browser-test-runner-devtools 内部处理，支持重试或切换手动登录

## 重要说明

1. **一次输入，全程自动**：步骤 1 收集所有参数，后续自动传递
2. **断点恢复**：中断后重新运行，自动检测已有产物，从断点继续
3. **子 skill 独立可用**：每个子 skill 可单独调用，不依赖本编排器
4. **所有产物同一目录**：功能地图、测试用例、YAML、报告统一在用户指定的输出目录
5. **无硬编码路径**：所有路径由用户指定，适用于任何环境
