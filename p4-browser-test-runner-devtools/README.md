# p4-browser-test-runner-devtools — 浏览器测试执行器

使用 Chrome DevTools MCP 执行 p3-ui-test-case-generator 生成的 YAML 测试用例。自动处理浏览器连接、登录、元素定位、断言验证，执行完成后生成 HTML 覆盖报告。

## 它能做什么

- 自动连接 Chrome 浏览器（通过 DevTools MCP）
- 智能检测登录状态，已登录自动跳过，未登录自动执行登录
- 按依赖顺序执行 YAML 测试场景
- AI 驱动的元素定位（通过 a11y 树快照匹配）
- 自动判断断言结果（Claude 读取快照文本判断）
- 失败时自动截图保存现场
- 生成功能测试维度覆盖报告（HTML 格式）
- 登录配置持久化，首次输入后自动复用

## 前置要求

- Chrome 已打开并启用远程调试（`--remote-debugging-port=9222`）
- Chrome DevTools MCP 插件已连接
- 已有 YAML 测试文件（由 p3-ui-test-case-generator 生成）

## 使用方法

### 在流水线中使用

```
/ai-web-test-pipeline
→ 自动调用 p4-browser-test-runner-devtools 执行所有 YAML 测试
```

### 单独使用

```
/p4-browser-test-runner-devtools
```

然后提供 YAML 文件路径：
- **suite.yaml**：执行整个套件（按依赖顺序执行所有场景）
- **单个场景 YAML**：只执行一个场景
- **目录路径**：自动查找目录下 suite.yaml

可选提供功能测试用例文件路径，用于生成 TC-ID 覆盖报告。

## 输入参数

| 参数 | 说明 | 必填 |
|------|------|------|
| YAML 文件路径 | suite.yaml 或单个场景 YAML 的路径 | 是 |
| 功能测试用例 | 功能测试用例 Markdown 文件路径（用于 TC-ID 覆盖报告） | 否 |

## 登录配置持久化

登录信息保存在 `~/.claude/test-login-configs.json`，按域名存储。

```json
{
  "configs": {
    "test-risk.inshopline.com": {
      "login_url": "https://test-risk.inshopline.com/login",
      "username": "admin",
      "password": "xxx",
      "username_selector": "账号输入框",
      "password_selector": "密码输入框",
      "login_button_selector": "登录按钮",
      "login_success_indicator": "页面跳转到首页",
      "login_type": "normal",
      "updated": "2026-06-07"
    }
  }
}
```

**规则**：
- 首次执行时通过交互式问答收集登录信息并保存
- 后续执行自动读取，不再询问
- SSO 类型登录只打开登录页，由用户手动完成
- 用户可通过"更新登录配置"指令强制重新输入

## 内部工作流程

### 1. 解析输入
读取 YAML 文件，解析场景列表和步骤。同时检查同目录下是否有 `traceability.json`。

### 2. 验证浏览器连接 + 自动登录

#### 2.1 验证浏览器连接
调用 `list_pages` 确认 MCP 连接。失败时提示用户启动 Chrome 调试模式。

#### 2.2 检查登录状态
导航到 base_url，`take_snapshot` 检查页面内容：
- **已登录**：页面为业务内容，无登录表单 → 跳过登录
- **未登录**：页面包含账号/密码输入框 → 执行登录

#### 2.3 自动登录
读取持久化配置或首次收集登录信息，执行登录步骤并验证。

### 3. 执行测试场景

支持 7 种操作类型：

| 操作 | 执行方式 |
|------|----------|
| **navigate** | `navigate_page` 到 base_url + url |
| **click** | `take_snapshot` 定位元素 → `click` uid |
| **input** | `take_snapshot` 定位输入框 → `click` 聚焦 → `fill` 输入值 |
| **select** | `take_snapshot` 定位下拉框 → `click` 打开 → 再次 `take_snapshot` → `click` 选项 |
| **assert** | `take_snapshot` 获取快照 → Claude 判断描述是否为真 |
| **wait** | `evaluate_script` 等待指定秒数 / `wait_for` 等待文字出现 |
| **scroll** | `evaluate_script` 执行滚动脚本 |

#### 元素定位策略
1. 从 description 提取关键词
2. 在 a11y 树快照中搜索匹配元素
3. 精确匹配优先，模糊匹配兜底
4. 多个匹配时选择 role 最相关的

#### 下拉框处理
Ant Design 等框架的下拉框：
1. 点击触发器（combobox role）
2. 等待下拉面板出现（listbox 元素）
3. 点击目标选项（option role）

#### 错误恢复
- 步骤失败不立即终止，记录失败并继续
- 关键步骤失败（如 navigate）标记后续为级联失败
- 每个步骤失败时自动截图保存现场

#### 依赖处理
- 依赖的场景失败 → 当前场景标记为"跳过"
- 依赖的场景通过 → 正常执行

### 4. 记录结果
每个步骤执行后记录：场景名、步骤序号、action 类型、描述、状态（pass/fail）、错误信息、截图路径。

### 5. 生成 HTML 覆盖报告

#### 报告结构

```
报告头部（项目名、日期、环境）
├── 概览统计卡片（总数、通过、失败、跳过、N/A）
├── P0 用例汇总表
├── 按模块分组的 TC-ID 覆盖表
│   └── 表格：TC-ID | 优先级 | 类型 | 描述 | 结果 | 详情
├── UI 可自动化覆盖统计
└── 失败详情（错误信息、截图、根因分析）
```

#### TC-ID 结果判定

| 条件 | 结果 |
|------|------|
| 关联步骤全部通过 | ✅ 通过 |
| 关联步骤中有失败 | ❌ 失败 |
| 场景被跳过（依赖失败） | ⏭️ 跳过 |
| 功能用例中存在但无 UI 场景覆盖 | N/A |
| 测试类型为 API/集成/性能 | N/A |

#### 报告样式
- 单文件 HTML，内联 CSS
- 模块区域可折叠展开
- 状态徽章区分通过/失败/跳过/N/A
- 响应式布局，最大宽度 1400px
- 失败行高亮背景色
- 表格行 hover 效果

### 6. 失败分析
对每个失败步骤：读取截图 → 分析失败原因 → 给出修复建议（修改 description / 添加 wait / 调整断言）。

## 输出

```
{项目输出目录}/
├── tests/
│   └── screenshots/                    # 失败步骤截图
│       └── S{n}-{步骤序号}-fail.png
└── {项目名}-UI自动化测试报告-{date}.html   # HTML 覆盖报告
```

报告生成后自动在浏览器中打开。

## 目录结构

```
p4-browser-test-runner-devtools/
├── SKILL.md              # Skill 定义文件
├── README.md             # 本文件
├── references/
│   └── report-template.md  # HTML 报告模板参考
└── scripts/              # 预留脚本目录
```

## 安装

**仓库地址**：`https://github.com/hzauliyanda/ai-web-test.git`

### 方式一：让 AI 工具自己安装

```
帮我安装以下 GitHub 仓库中的 skills：https://github.com/hzauliyanda/ai-web-test.git
```

### 方式二：手动安装

```bash
git clone https://github.com/hzauliyanda/ai-web-test.git
# Claude Code
cp -r ai-web-test/p4-browser-test-runner-devtools ~/.claude/skills/
# Codex
cp -r ai-web-test/p4-browser-test-runner-devtools ~/.codex/skills/
# OpenCode
cp -r ai-web-test/p4-browser-test-runner-devtools ~/.config/opencode/skills/
```

## 重要说明

1. **登录非必须**：浏览器已登录时自动跳过，未登录时才触发
2. **快照优先于截图**：`take_snapshot` 比 `take_screenshot` 更高效，能精确获取元素 uid
3. **Claude 自身判断 assert**：不依赖 VLM，直接读取快照文本判断
4. **不启动新浏览器**：直接操作用户已有的 Chrome 窗口
5. **报告以功能用例为准**：报告维度围绕 TC-ID 组织，不是 UI 场景
6. **traceability.json 自动读取**：同目录存在时自动用于 TC-ID 覆盖映射
7. **所有内容使用中文**：步骤描述、报告、修复建议
8. **支持的操作**：navigate, click, input, select, assert, wait, scroll
