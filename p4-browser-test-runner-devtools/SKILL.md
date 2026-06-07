---
name: p4-browser-test-runner-devtools
description: >
  使用 Chrome DevTools MCP 执行 p3-ui-test-case-generator 生成的 YAML 测试用例。
  通过 take_snapshot 定位元素，click/fill/navigate_page 执行操作，Claude 自身判断 assert 结果。
  支持自动登录（普通登录/SSO 登录），登录配置持久化到本地文件，后续执行自动复用。
  执行完成后自动生成功能测试维度覆盖报告（HTML 格式）。
  Use when: 用户要求用 Chrome DevTools 执行测试、运行 YAML 测试用例；
  用户说"执行UI测试"、"跑一下测试用例"、"运行YAML测试"。
---

# Browser Test Runner (Chrome DevTools)

使用 Chrome DevTools MCP 执行 YAML 测试用例，支持自动登录和配置持久化。

## 前置条件

- Chrome 已打开并启用远程调试（`--remote-debugging-port=9222`）
- Chrome DevTools MCP 插件已连接
- 已有 YAML 测试文件（由 `p3-ui-test-case-generator` 生成）
- 登录状态：如果浏览器已登录目标系统，自动跳过登录；如果未登录，自动执行登录

## 登录配置持久化

登录信息保存在 `~/.claude/test-login-configs.json`，避免每次执行都重新输入。

**配置文件格式**：
```json
{
  "configs": {
    "{domain}": {
      "login_url": "https://example.com/login",
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
- 以域名（domain）为 key，同一系统只保存一份配置
- 首次执行时通过 AskUserQuestion 收集登录信息并保存
- 后续执行自动读取，不再询问
- 用户可通过"更新登录配置"指令强制重新输入
- SSO 类型登录会标记 `login_type: "sso"`，此时只打开登录页让用户手动完成 SSO

## 工作流程

### 步骤 1：解析输入

用户传入 YAML 路径，格式支持：
- **suite.yaml**：执行整个套件（按依赖顺序执行所有场景）
- **单个场景 YAML**：只执行一个场景
- **目录路径**：查找目录下 suite.yaml

先读取 YAML 文件，解析出场景列表和步骤。

同时检查同目录下是否有 `traceability.json`（TC-ID 追溯映射文件），如有则读取用于报告生成。

### 步骤 2：验证浏览器连接 + 自动登录

#### 2.1 验证浏览器连接

1. 调用 `mcp__plugin_chrome-devtools-mcp_chrome-devtools__list_pages` 确认 MCP 已连接
2. 如果连接失败，提示用户启动带远程调试的 Chrome：
   ```bash
   open -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```

#### 2.2 检查登录状态

从 suite.yaml 读取 `base_url`。

1. 导航到 base_url
2. `take_snapshot` 检查当前页面内容
3. **如果已登录**（页面内容为业务系统首页/功能页，不包含登录表单）：直接跳过登录，进入步骤 3
4. **如果未登录**（页面为登录页或包含账号/密码输入框）：进入步骤 2.3 执行登录

**判断已登录的标志**：快照中不包含 `login`、`登录`、`password`、`密码` 等登录表单特征元素，且包含系统菜单、导航栏等业务内容。

#### 2.3 自动登录（如需要）

**如果检测到未登录**：

1. 读取 `~/.claude/test-login-configs.json` 中该域名的配置
2. **有已保存配置**：
   - `login_type: "normal"`：自动执行登录步骤
     1. 导航到 `login_url`
     2. `take_snapshot` 获取页面
     3. 找到账号输入框 → `fill` 输入用户名
     4. 找到密码输入框 → `fill` 输入密码
     5. 找到登录按钮 → `click` 点击
     6. 等待 2 秒
     7. `take_snapshot` 验证登录成功（检查 `login_success_indicator`）
   - `login_type: "sso"`：导航到登录页，提示用户"请在浏览器中手动完成 SSO 登录，完成后回复继续"
3. **无已保存配置**：
   - 通过 AskUserQuestion 收集登录信息：
     ```
     请提供以下登录信息：
     1. 登录页面 URL
     2. 登录账号
     3. 登录密码
     4. 账号输入框描述（如"账号输入框"或"用户名输入框"）
     5. 密码输入框描述
     6. 登录按钮描述
     7. 登录成功后的验证描述（如"页面出现首页菜单"）
     8. 登录类型（普通登录 / SSO 登录）
     ```
   - 收集后保存到 `~/.claude/test-login-configs.json`
   - 然后执行登录步骤

**登录失败处理**：
- 如果自动登录后验证失败，提示用户选择：
  1. 重新输入登录信息（更新配置）
  2. 手动登录（在浏览器中操作，完成后回复继续）

### 步骤 3：执行测试场景

对每个场景，按顺序执行步骤。每个步骤的执行方式：

#### navigate — 页面导航

```
action: navigate
url: "/path"
description: "描述"
```

执行：拼接 base_url + url，调用 `navigate_page`：
- `mcp__plugin_chrome-devtools-mcp_chrome-devtools__navigate_page` type=url url=完整URL
- 等待页面加载（等待 2 秒或 `wait_for` 关键文字）

#### click — 点击元素

```
action: click
description: "点击新增处罚按钮"
```

执行：
1. `take_snapshot` 获取当前页面快照
2. 从快照中找到 description 描述匹配的元素 uid
3. `click` uid=找到的uid
4. 等待 1 秒

**元素匹配策略**：
- 优先精确匹配：按钮文字、链接文字完全包含描述中的关键词
- 模糊匹配：描述中的关键词出现在元素的 name/role/text 中
- 如果找不到，`take_screenshot` 截图辅助判断

#### input — 输入文本

```
action: input
description: "在任务名称输入框中输入'测试'"
value: "测试"
```

执行：
1. `take_snapshot` 获取快照
2. 找到描述匹配的输入框 uid
3. 先 `click` 该输入框聚焦
4. `fill` uid=输入框uid value=值（fill 会先清空再输入）
5. 等待 0.5 秒

**注意**：对于 textarea，同样用 `fill`。

#### select — 下拉选择

```
action: select
description: "执行主体下拉框选择'商品'"
```

执行：
1. `take_snapshot` 获取快照
2. 找到下拉框元素 uid
3. `click` 该下拉框打开选项列表
4. 等待 0.5 秒
5. 再次 `take_snapshot` 获取下拉选项列表
6. 找到目标选项的 uid
7. `click` 该选项

**如果 select 步骤有 value 字段**：value 就是要选的选项。
**如果没有 value**：从 description 中提取选项（如"选择'商品'"提取"商品"）。

#### assert — 断言验证

```
action: assert
description: "列表展示了任务数据"
```

执行：
1. `take_snapshot` 获取当前页面完整快照
2. Claude 根据快照内容判断 description 中的陈述是否为真
3. 如果无法从快照判断，`take_screenshot` 截图辅助判断

**断言原则**：
- 断言描述通常比较宽泛，只要页面状态大体符合即通过
- 不要求精确匹配文案，只要语义正确即可
- 如果断言失败，记录失败原因

#### wait — 等待

```
action: wait
description: "等待列表加载完成"
seconds: 3
```

执行：
- 有 `seconds`：使用 `evaluate_script` 执行 `await new Promise(r => setTimeout(r, seconds*1000))`
- 有 description：使用 `wait_for` text=[关键词]
- 都没有：默认等待 2 秒

#### scroll — 滚动页面

```
action: scroll
direction: "down"
```

执行：使用 `evaluate_script`：
```javascript
() => {
  const findScrollable = (el) => {
    const style = getComputedStyle(el);
    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 10) return el;
    for (const child of el.children) { const found = findScrollable(child); if (found) return found; }
    return null;
  };
  const container = findScrollable(document.documentElement) || document.documentElement;
  container.scrollBy({ top: direction === 'down' ? 500 : -500, behavior: 'smooth' });
}
```

或直接用 `press_key` key="PageDown"/"PageUp"。

### 步骤 4：记录结果

每个步骤执行后记录：

| 字段 | 说明 |
|------|------|
| 场景名 | 如 S1-处罚任务创建 |
| 步骤序号 | 从 1 开始 |
| action 类型 | navigate/click/input/select/assert/wait/scroll |
| 描述 | 步骤的 description |
| 状态 | pass / fail |
| 错误信息 | 失败原因（如有） |
| 截图路径 | 失败时自动截图，保存到 `{输出目录}/screenshots/` |

**失败截图规则**：
- 每个步骤执行失败时，立即调用 `take_screenshot` 截图
- 截图保存到 `{输出目录}/screenshots/S{n}-{步骤序号}-fail.png`
- 截图文件路径记录到结果中，用于报告展示和失败分析

### 步骤 5：生成功能测试维度覆盖报告

所有场景执行完成后，自动生成功能测试维度覆盖报告。

#### 5.1 收集报告数据

从执行结果中提取：
- 每个场景的通过/失败/跳过状态
- 每个步骤的详细结果
- 失败步骤的错误信息和快照
- 场景与 TC-ID 的映射关系（从 YAML 文件注释中提取）

如果用户提供了功能测试用例文件（Markdown），读取并解析所有 TC-ID、模块归属、优先级、测试类型等信息。

#### 5.2 确定报告输出路径

报告输出到 YAML 测试文件所在目录的上级目录（即项目输出目录），文件名格式：`{项目名}-UI自动化测试报告-{日期}.html`

所有产物在同一项目目录下：
```
{项目输出目录}/
├── {项目名}功能地图.md
├── {项目名}-功能测试用例.md
├── {项目名}-UI测试用例.md
├── tests/
│   ├── suite.yaml
│   ├── traceability.json
│   └── s1-xxx.yaml ...
└── {项目名}-UI自动化测试报告-{date}.html
```

#### 5.3 生成 HTML 报告

使用 Write 工具生成 HTML 格式的报告文件。报告包含以下章节：

**报告头部**：
- 项目名称
- 测试日期
- 测试环境（URL）
- 执行工具（Chrome DevTools MCP）
- 执行人

**概览统计卡片**：
- 功能用例总数
- 通过数
- 失败数
- 跳过数
- 不适用数（API/集成/性能类型）

**按模块分组的 TC-ID 覆盖表**：
- 模块名称（如 SUBMIT-处罚任务提交、LIST-任务列表查询）
- 该模块下所有 TC-ID
- 每个 TC-ID 的优先级（P0/P1/P2）
- 测试类型（功能/API/集成/性能）
- 用例描述
- 执行结果（✅通过/❌失败/⏭️跳过/N/A）
- 失败原因（如有）

**P0 用例汇总**：单独列出所有 P0 优先级用例的执行结果

**UI 可自动化用例汇总**：统计哪些用例适合 UI 自动化、哪些需要 API/集成测试

**失败详情**：展开显示每个失败用例的详细错误信息、失败截图（base64 嵌入）、根因分析

**CSS 样式要求**：
- 使用内联 CSS（单文件 HTML）
- 模块区域可折叠展开
- 使用 badge 样式区分通过/失败/跳过/N/A
- 响应式布局，最大宽度 1400px
- 失败行高亮背景色
- 表格行 hover 效果

报告 HTML 模板结构参考 `references/report-template.md`。

#### 5.4 打开报告

生成后使用 Bash 工具 `open` 命令在浏览器中打开报告。

### 步骤 6：失败分析（如有失败）

对每个失败步骤：
1. 读取步骤 4 保存的失败截图（`{输出目录}/screenshots/S{n}-{步骤序号}-fail.png`）
2. 分析失败原因（元素不在可视区域 / 元素名称变化 / 页面未加载完 / 断言不符等）
3. 给出修复建议（修改 YAML description / 添加 wait 步骤 / 调整断言描述）

## 执行策略

### 元素定位

`take_snapshot` 返回的 a11y 树中，每个元素有 `uid` 和文本内容。定位策略：

1. **从 description 提取关键词**：如"点击新增处罚按钮" → 关键词"新增处罚"
2. **在快照中搜索**：找 button/link/treeitem 等可点击元素中包含关键词的
3. **精确匹配优先**：元素文本完全包含关键词
4. **如果多个匹配**：选择 role 最相关的（如按钮 > 文本 > 容器）

### 下拉框处理

Ant Design 等框架的下拉框通常是：
1. 点击触发器（通常是带有 `combobox` role 或 `down` 图标的元素）
2. 等待下拉面板出现（新出现在快照底部的 `listbox` 元素）
3. 点击目标选项（`option` role 的元素）

### 错误恢复

- 如果步骤失败，**不立即终止**，记录失败并继续执行下一个步骤
- 如果是关键步骤失败（如 navigate 失败），后续步骤可能全部失败，标记为级联失败
- 每个步骤失败时自动截图保存现场

### 依赖处理

suite.yaml 中的 `depends_on`：
- 如果依赖的场景失败，当前场景标记为"跳过"
- 如果依赖的场景通过，正常执行

## 重要说明

1. **登录非必须**：如果浏览器已登录目标系统，自动检测并跳过登录步骤；未登录时才触发自动登录
2. **登录配置持久化**：首次输入后保存到 `~/.claude/test-login-configs.json`，后续自动复用
3. **快照优先于截图**：take_snapshot 比 take_screenshot 更高效，能精确获取元素 uid
4. **Claude 自身判断 assert**：不依赖 VLM，Claude 直接读取快照文本判断
5. **每个步骤间隔适当等待**：避免页面未加载完就开始操作
6. **所有内容使用中文**：步骤描述、报告、修复建议
7. **支持的操作**：navigate, click, input, select, assert, wait, scroll
8. **不启动新浏览器**：直接操作用户已有的 Chrome 窗口
9. **报告以功能用例为准**：报告维度围绕 TC-ID 组织，不是 UI 场景
10. **traceability.json 自动读取**：如 YAML 同目录存在 traceability.json，自动用于 TC-ID 覆盖映射
