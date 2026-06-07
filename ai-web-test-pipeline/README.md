# AI Web 测试流水线

基于 AI 的 Web 端自动化测试完整解决方案。输入一个 URL，自动完成从网站探索到测试报告的全流程。

## 它能做什么

```
业务系统 URL
    ↓
[1] 智能探索网站，生成功能地图
    ↓
[2] 结合需求文档，生成功能测试用例（含 TC-ID）
    ↓
[3] 按场景编排 UI 自动化用例（YAML），每个 UI 场景映射到功能用例
    ↓
[4] 自动执行测试，输出 HTML 覆盖报告
```

**一句话**：给个 URL，拿到测试报告。

## 前置要求

- [Claude Code](https://claude.com/claude-code) CLI 或桌面端
- Chrome 浏览器（已安装）
- Chrome DevTools MCP 插件（已配置）
- 本套 skills 已安装到 `~/.claude/skills/` 目录

## 快速开始

在 Claude Code 中输入：

```
/ai-web-test-pipeline
```

然后按提示提供：
1. 业务系统 URL（必填）
2. 项目名称（必填）
3. 输出目录（必填）
4. 参考文档：需求文档、技术文档（可选）
5. 登录信息：账号密码（如需登录）

之后就自动跑完整个流程。

## 输出产物

所有产物在同一目录下：

```
{项目名}/
├── {项目名}功能地图.md                  # 网站页面结构、导航、表单、按钮
├── {项目名}-功能测试用例-{date}.md      # 功能测试用例（含 TC-ID、优先级）
├── {项目名}-功能测试用例-{date}.xlsx    # 可导入测试管理平台
├── {项目名}-UI测试用例.md               # UI 场景化用例 + TC-ID 追溯矩阵
├── tests/
│   ├── suite.yaml                      # 测试套件（登录配置 + 执行顺序）
│   ├── traceability.json               # UI 场景 ↔ 功能用例映射
│   ├── s1-xxx.yaml                     # 场景 1 测试步骤
│   ├── s2-xxx.yaml                     # 场景 2 测试步骤
│   └── ...
└── {项目名}-UI自动化测试报告-{date}.html  # HTML 覆盖报告（自动打开）
```

## 报告包含什么

- 概览统计：通过/失败/跳过数量
- TC-ID 覆盖矩阵：按模块分组，每个功能用例的执行状态
- P0 用例汇总：高优先级用例单独列出
- 失败详情：失败步骤、错误信息、截图、修复建议

## 也可以单步使用

不需要跑全流程时，单独调用任意一个 skill：

| 命令 | 用途 |
|------|------|
| `/p1-web-explorer` | 只探索网站，生成功能地图 |
| `/p2-test-case-generator` | 只生成功能测试用例 |
| `/p3-ui-test-case-generator` | 只生成 UI 自动化用例（需先有功能地图 + 功能用例） |
| `/p4-browser-test-runner-devtools` | 只执行测试（需先有 YAML 用例） |

## 断点恢复

流程中断后重新运行 `/ai-web-test-pipeline`，会自动检测已有产物，跳过已完成的步骤，从断点继续。

比如功能地图和功能用例已经生成了，第三次运行会直接从生成 UI 用例开始。

## 登录说明

- **已登录自动跳过**：如果浏览器已登录目标系统，自动检测并跳过登录
- **普通登录**：首次输入账号密码后自动保存，后续自动登录
- **SSO 登录**：自动打开登录页，提示手动完成 SSO，完成后继续
- 登录配置保存在 `~/.claude/test-login-configs.json`，按域名存储

## Skill 清单

| Skill | 路径 | 功能 |
|-------|------|------|
| ai-web-test-pipeline | `skills/ai-web-test-pipeline/` | 编排器，串联全流程 |
| p1-web-explorer | `skills/p1-web-explorer/` | 探索网站，生成功能地图 |
| p2-test-case-generator | `skills/p2-test-case-generator/` | 生成功能测试用例 |
| p3-ui-test-case-generator | `skills/p3-ui-test-case-generator/` | 生成 UI 自动化用例 |
| p4-browser-test-runner-devtools | `skills/p4-browser-test-runner-devtools/` | 执行测试，生成报告 |

## 安装方式

将所有 skill 目录复制到 `~/.claude/skills/` 下：

```
~/.claude/skills/
├── ai-web-test-pipeline/
├── p1-web-explorer/
├── p2-test-case-generator/
├── p3-ui-test-case-generator/
└── p4-browser-test-runner-devtools/
```

确保 Chrome DevTools MCP 插件已在 Claude Code 中启用。

## 典型使用场景

**场景 1：新项目首次测试**
```
/ai-web-test-pipeline
→ 提供系统 URL + 需求文档 + 登录信息
→ 自动完成全流程，拿到 HTML 报告
```

**场景 2：回归测试**
```
/ai-web-test-pipeline
→ 使用已有功能地图和用例，只重新执行测试
→ 拿到最新报告
```

**场景 3：只探索不了解系统**
```
/p1-web-explorer
→ 提供 URL
→ 生成功能地图，了解系统全貌
```

**场景 4：已有功能用例，只要 UI 自动化**
```
/p3-ui-test-case-generator
→ 提供功能地图 + 功能用例 + URL
→ 生成 YAML，然后用 /p4-browser-test-runner-devtools 执行
```

## 内部工作流程

1. **收集输入**：通过交互式问答收集 URL、项目名、输出目录、参考文档、登录信息
2. **创建项目目录**：初始化 `pipeline-state.json` 跟踪各步骤状态
3. **检查已有产物**：检测输出目录中是否已有功能地图、测试用例等文件，有则询问是否复用
4. **按序执行子 skill**：
   - 调用 `p1-web-explorer` 探索网站 → 生成功能地图
   - 调用 `p2-test-case-generator` 生成功能测试用例 → Markdown + XLSX
   - 调用 `p3-ui-test-case-generator` 生成 UI 自动化用例 → YAML + 追溯矩阵
   - 调用 `p4-browser-test-runner-devtools` 执行测试 → HTML 报告
5. **输出总结**：展示所有产物路径和报告概要

每个子 skill 执行完成后更新 `pipeline-state.json`，支持断点恢复。
