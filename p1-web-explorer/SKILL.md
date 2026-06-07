---
name: p1-web-explorer
description: >
  Web 端功能探索器，自动探索网站页面结构、导航体系、筛选条件、数据列表和操作按钮，生成结构化的功能地图 Markdown 文件。
  Use when: 用户要求探索网页、分析网站结构、生成功能地图、探索 Web 项目功能；
  用户说"探索这个页面"、"分析这个网站"、"生成功能地图"、"帮我看看这个 Web 项目"。
  依赖 chrome-devtools-mcp 插件提供浏览器控制能力。
---

# Web Explorer — 网站功能探索器

通过 Chrome DevTools MCP 控制浏览器，系统性探索 Web 项目并生成功能地图。

## 执行流程

### 第一步：收集信息

用 AskUserQuestion 一次性询问以下内容：

1. **目标 URL** — 要探索的网页地址
2. **是否需要登录** — 是/否
3. **探索深度** — 完整探索（推荐，含子页面、下拉选项、详情页）/ 仅当前页面 / 自定义
4. **输出路径** — 项目测试输出目录（如用户未指定，提示用户选择或创建一个目录），功能地图保存为 `{项目名}功能地图.md`

### 第二步：准备浏览器

1. 调用 `list_pages` 检查 Chrome DevTools MCP 连接
2. 如果连接失败，依次执行：
   - `killall -9 "Google Chrome"` 杀掉所有 Chrome 进程
   - 以调试模式重启：
     ```bash
     /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
       --remote-debugging-port=9222 \
       --user-data-dir=/tmp/chrome-debug \
       "{目标URL}" &
     ```
   - 等待 5 秒后创建 DevToolsActivePort 文件：
     ```bash
     printf "9222\n/devtools/browser/\n" > \
       "$HOME/Library/Application Support/Google/Chrome/DevToolsActivePort"
     ```
   - 再次 `list_pages` 确认连接成功

### 第三步：处理登录

- **需要登录**：`navigate_page` 打开目标 URL → `take_screenshot` 截图展示给用户 → 告知"请在浏览器中手动登录，完成后回复'登录成功'" → 等待用户回复
- **不需要登录**：直接打开目标 URL 继续探索

**绝不替用户输入密码**，因为实际项目可能有 SSO、验证码、2FA。

### 第四步：探索页面

用 TaskCreate 追踪每个页面的探索进度。对每个页面执行：

1. **`take_snapshot`** — 获取页面结构（优先，信息更结构化）
2. **`take_screenshot`** — 辅助截图验证
3. **展开所有下拉框** — `click` combobox → 记录 listbox 内所有选项 → `click` 任意选项关闭
4. **进入子页面** — 点击"查看"/"新增"/"编辑"等按钮，探索详情页和表单页
5. **切换 Tab 页签** — 点击所有 tab 获取不同内容
6. **`navigate_page`** — 访问左侧/顶部导航中的其他页面
7. **`wait_for`** — 等待页面加载完成再获取内容

需要记录的信息：

| 维度 | 内容 |
|------|------|
| 页面清单 | 每个页面的名称、URL 路径、页面类型 |
| 导航体系 | 全局导航、子导航、面包屑 |
| 筛选条件 | 字段名、类型、所有下拉选项值 |
| 数据列表 | 列名、操作按钮、按钮状态规则 |
| 分页信息 | 总条数、每页条数 |
| 表单字段 | 字段名、类型、是否必填、默认值 |
| 页面跳转 | 页面之间的链接和跳转关系 |
| 枚举值 | 所有可能的选项值和状态值 |
| 状态流转 | 数据状态的流转路径 |

### 第五步：生成功能地图

按 [references/output-template.md](references/output-template.md) 中的模板结构生成 Markdown 文件。

写入后执行 `chmod 777 {文件路径}`。

## 关键原则

- 先 snapshot 后 screenshot — snapshot 信息更结构化
- 下拉选项必须展开获取完整列表
- 操作按钮状态规则要记录（哪些状态下禁用）
- 每步用 TaskCreate 追踪，不丢进度
