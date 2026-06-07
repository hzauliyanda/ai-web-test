---
name: p2-test-case-generator
description: Generate comprehensive test cases for Shopline plugins and integrations. Use this skill whenever the user requests test case generation, mentions testing requirements, provides requirement/technical documentation links, or needs help creating test scenarios. This skill handles both new features and regression testing by analyzing requirement documents, technical specs, Figma designs, and code implementation details to produce structured test cases with priority classification. Also use this skill when the user wants to supplement, extend, or update existing test cases — for example, adding C-end (consumer-facing) test cases to a file that already has B-end (admin-facing) ones, or adding a new module's test cases to an existing file.
---

# 测试用例生成器

此技能帮助您为 Shopline 插件项目生成全面的测试用例，通过分析需求文档、技术文档、Figma 设计和代码实现。

## 使用时机

当出现以下情况时使用此技能：
- 用户提供需求文档链接并要求生成测试用例
- 用户想要为新功能或回归测试生成测试用例
- 用户需要帮助理解如何基于实现测试功能
- 用户在功能开发上下文中提到测试、测试用例或质量保证
- 用户要求在已有测试用例文件基础上补充、增改测试用例（如已有B端用例，需要补充C端用例）
- 用户指定了项目中已有的测试用例文件路径，要求在该文件基础上增改

## 工作流程

### 步骤 1：收集输入信息

询问用户：
1. **需求文档链接** (Yuque)：功能需求和用户故事（可提供多个）
2. **技术文档链接** (Yuque)：实现细节和技术规范（可提供多个，必须全部读取）
3. **Figma 设计链接**：UI/UX 设计规范
4. **项目类型**：这是新项目还是迭代项目？
   - 如果是新项目：确认是否已运行 `/init`，如果没有，建议先运行
   - 如果是迭代项目：说明将分析当前分支与 master 的代码差异
5. **已有测试用例文件路径**（可选）：如果用户提到已有测试用例文件，需要在该文件基础上增改
   - 用户提供文件路径后，读取该文件，分析已覆盖的模块和用例
   - 识别同名 TC-ID 前缀，避免编号冲突
   - 新生成的测试用例只补充已有文件中不存在的模块/场景
   - 最终写入已有文件（增改），而非创建新文件
   - 增改完成后重新生成 XLSX 文件

示例提示：
```
我将为您生成测试用例。请提供：
1. 需求文档链接 (Yuque)（可提供多个）
2. 技术文档链接 (Yuque)（可提供多个，我会全部读取）
3. Figma 设计链接
4. 这是新项目还是迭代项目？
5. 是否已有测试用例文件需要在上面增改？（如提供路径，我会在已有文件基础上补充）
```

### 步骤 1.5：确定生成模式（全新 vs 增量增改）

在开始生成测试用例之前，必须确定本次是**全新生成**还是**增量增改**：

**增量增改模式的触发条件**（满足任一即进入）：
- 用户明确说"在已有文件上补充"、"增改"、"添加C端用例"等
- 用户提供了已有测试用例文件的路径（如 `<测试用例输出目录>/xxx.md`）
- 用户说"已有一份B端测试用例，需要补充C端"

**增量增改模式的流程**：

1. **读取已有文件**：用 Read 工具读取用户提供的 Markdown 测试用例文件
2. **分析已有内容**：
   - 提取所有模块名（`## XXX模块` 标题）
   - 提取所有 TC-ID 及其编号（如 `TC-FORBID-001` 到 `TC-FORBID-010`）
   - 提取所有已有用例的标题和关键测试场景
   - 识别 TC-ID 前缀（如 `FORBID`、`CMT`、`MSG` 等），了解编号体系
3. **确定新增用例的模块和 TC-ID**：
   - 新增模块使用新的 `## XXX模块` 标题
   - 新增 TC-ID 前缀应与已有前缀体系一致但不冲突（如已有 `FORBID`、`CMT`、`MSG`，新增可用 `C-END` 或其他合适前缀）
   - 新增 TC-ID 编号从已有文件中同前缀最大编号继续递增，或使用新前缀从 001 开始
4. **直接编辑已有文件**：
   - 使用 Edit 工具在已有 Markdown 文件末尾追加新模块和测试用例
   - **不要创建新文件**，而是直接修改已有文件
   - 如果需要修改已有用例（如修正描述），也使用 Edit 工具精准修改
5. **重新生成 XLSX**：
   - 修改完 Markdown 文件后，运行 `generate_xlsx.py` 重新生成 XLSX 文件
   - XLSX 文件与 Markdown 文件同名同目录（如 `xxx.md` → `xxx.xlsx`）

**增量增改的关键原则**：
- 不重复已有用例，只补充缺失的模块和场景
- 保留已有文件的结构和编号体系
- 新模块追加到文件末尾，保持 `---` 分隔
- 修改完成后必须重新生成 XLSX

**全新生成模式的流程**（默认）：
- 与当前流程一致，生成完整的 Markdown 和 XLSX 文件

### 步骤 2：浏览文档

**重要**：必须完整读取所有文档内容，不能只读第一页或可见部分。

#### 2.1 读取需求文档

使用 Task 代理完整读取长文档：

```
使用 Task 代理的 "explore" 模式，让它使用 Grep 和 Read 工具配合 offset/limit 参数
完整读取文档的所有部分，而不是只读取第一页。
```

**必须读取的内容**：
- 功能需求
- 用户场景和流程
- 验收标准
- 提到的边缘情况
- 系统交互逻辑
- 字段映射关系
- 任务状态定义

使用以下策略之一：
1. 如果文档有清晰的章节结构，分段读取每一节
2. 使用 Grep 工具搜索关键章节标题，然后逐节读取
3. 使用 Read 工具的 offset/limit 参数分段读取完整文档

#### 2.2 读取技术文档

**重要**：用户可能提供多个技术文档链接，必须逐一完整读取所有文档，不能遗漏任何一个。

必须读取：
- API 端点和参数
- 数据模型和结构
- 集成点
- 错误处理机制
- 配置要求
- 接口列表
- 表结构设计

同样使用分段读取或 Grep 搜索完整读取所有内容。

当用户提供多个技术文档链接时，使用 Task 代理并行读取每个文档，确保所有文档都被完整读取并整合到测试用例生成中。

#### 2.3 读取 Figma 设计

**重要**：推荐使用 chrome-devtools MCP 工具通过浏览器截图和快照获取设计稿信息。相比 Figma API（限流严重、不稳定），浏览器方式更可靠且能直接观察设计意图。Figma API 脚本仅作为备选方案。

##### 方式一：浏览器截图+快照识别（推荐）

使用 chrome-devtools MCP 工具直接在浏览器中打开 Figma 设计稿，通过截图和 a11y 快照提取交互信息。

**Step 1：导航到设计稿**

```
chrome-devtools_navigate_page --type "url" --url "https://www.figma.com/design/XXXXX/FileName?node-id=186-5610"
```

Figma 页面加载较慢，建议设置 60 秒超时：
```
chrome-devtools_navigate_page --type "url" --url "<figma_url>" --timeout 60000
```

**Step 2：等待页面加载完成**

Figma 编辑器加载后需要等待画布渲染完成。使用 wait_for 等待关键元素出现：
```
chrome-devtools_wait_for --text ["Canvas"] --timeout 30000
```

或者截取快照确认内容已加载：
```
chrome-devtools_take_snapshot
```

**Step 3：截取设计稿截图**

对当前可见的设计稿页面截取全页截图，用于后续识别和归档：
```
chrome-devtools_take_screenshot --fullPage true --filePath "<缓存目录>/figma-screenshots/page-1.png"
```

如果设计稿很长，可以分段滚动截取：
```
chrome-devtools_take_screenshot --filePath "<缓存目录>/figma-screenshots/page-1-top.png"
```

**Step 4：获取 a11y 快照提取元素信息**

a11y 快照能提取出页面中可见的文本、按钮、表单字段等结构化信息：
```
chrome-devtools_take_snapshot
```

从快照中重点关注：
- **按钮文字**：如"保存"、"取消"、"删除"、"同步"等
- **表单字段**：输入框、下拉选择、开关等
- **导航元素**：Tab 标签、侧边栏菜单项
- **弹窗/对话框**：确认弹窗、提示信息
- **状态文字**：如"已同步"、"同步中"、"同步失败"

**Step 5：探索原型交互连接**

Figma 的原型模式（Prototype）可以设置页面间跳转和交互。识别交互的方法：

1. 在 Figma 中点击有原型连接的元素，观察是否出现蓝色箭头或连接指示
2. 使用快照查看是否有"Navigate to"、"Open overlay"等交互提示
3. 切换到 Figma 的 Prototype 面板（右侧面板）查看连接信息

**Step 6：查看多个页面/Frame**

如果设计稿包含多个页面（Page 1, Page 2 等）或多个 Frame：
1. 在 Figma 左侧面板的页面列表中点击切换
2. 每个页面/Frame 都重复截图和快照步骤
3. 确保覆盖所有相关的设计页面

**重要提示**：
- Figma 在浏览器中运行时，左侧面板显示页面列表，中间是画布，右侧是属性面板
- 如果 node-id 参数指定了特定节点，Figma 会自动定位到该节点
- 可以通过滚轮缩放查看设计稿全貌
- 如果遇到 Figma 加载失败（白屏或报错），可以刷新页面重试

##### 方式二：Figma API 脚本（备选）

当浏览器方式无法获取足够的交互连接信息时，可使用 `fetch_figma.py` 脚本作为补充。但注意 Figma API 存在限流和不稳定性，仅建议在以下场景使用：
- 需要获取原型跳转连接的详细目标节点信息
- 需要批量提取大量 Frame 的文字内容
- 浏览器方式遇到加载问题

```bash
export FIGMA_ACCESS_TOKEN="<YOUR_FIGMA_ACCESS_TOKEN>"

# 获取完整文件分析
python <skill目录>/scripts/fetch_figma.py "https://www.figma.com/design/XXXXX/FileName"

# 获取特定页面节点
python <skill目录>/scripts/fetch_figma.py "https://www.figma.com/design/XXXXX/FileName?node-id=186-5610"

# 保存到文件
python <skill目录>/scripts/fetch_figma.py "https://www.figma.com/design/XXXXX/FileName" -o figma-analysis.md
```

API 脚本可能遇到的错误：
- **429 限流**：脚本会自动重试（最多3次），但等待时间较长
- **403 认证失败**：检查 token 是否正确或过期
- **404 文件未找到**：检查 URL 中的 file key

##### 生成页面交互测试用例

根据 Figma 分析结果（截图+快照 或 API），在步骤 4 中应当增加以下类型的测试用例：

**必须生成的交互测试类型**：

1. **页面导航测试** — 验证各页面间跳转是否与 Figma 原型一致
   - 示例：点击"同步设置"Tab → 跳转到同步配置页面
   - 示例：点击"库存同步"开关 → 页面展示对应状态

2. **按钮交互测试** — 验证每个按钮的点击行为
   - 从截图和快照中识别的按钮列表，逐一验证点击后的响应
   - 包括主操作按钮（保存、同步、删除）和辅助按钮（取消、返回）

3. **表单输入测试** — 验证表单字段的交互行为
   - 必填项校验
   - 格式校验（邮箱、数字范围等）
   - 提交/重置逻辑

4. **弹窗/覆盖层测试** — 验证弹窗的打开、关闭和交互
   - 确认弹窗（删除确认、操作确认）
   - 错误提示弹窗
   - 成功/失败反馈

5. **开关/状态切换测试** — 验证状态变化的 UI 响应
   - 同步开关的开启/关闭状态变化
   - 状态切换时的过渡效果（loading、禁用状态等）

6. **空状态/错误状态测试** — 验证异常场景的 UI 展示
   - 无数据时的空状态展示
   - 网络错误时的错误页面
   - 加载中的过渡状态

### 步骤 3：分析项目代码

根据项目类型：

**对于新项目**：
1. 检查项目是否已初始化：
   ```bash
   ls -la
   ```
2. 如果没有找到 `/init`，建议先运行初始化
3. 读取项目结构：
   - `main.go` 或入口点
   - `internal/domain/` 业务逻辑
   - `internal/repository/` 数据访问
   - 客户端实现用于外部集成
4. 从 AGENTS.md 或类似文档理解代码库架构

**对于迭代项目**：
1. 检查当前分支：
   ```bash
   git branch
   ```
2. 获取当前分支与 master 的差异：
   ```bash
   git diff master...HEAD
   ```
3. 识别修改的文件和函数
4. 关注：
   - 新增功能
   - bug 修复实现
   - API 变更
   - 数据库模式变更

### 步骤 4：生成测试用例

创建按功能模块组织的全面测试用例：

**重要**：所有测试用例内容必须用中文生成，包括：
- 模块名称
- 测试用例标题
- 描述
- 前置条件
- 测试步骤
- 预期结果
- 实现参考

#### 优先级分类

- **P0（核心功能）**：
  - 必须具备的功能，会阻塞发布
  - 主要用户流程
  - 关键业务逻辑
  - 数据完整性场景
  - 核心页面交互流程（导航、主操作按钮）
  
- **P1（非核心但重要）**：
  - 用户可能触发的次要功能
  - 替代流程
  - 分页场景
  - 常见错误场景
  - 表单验证、弹窗交互
  
- **P2（锦上添花）**：
  - UX 改进
  - 优化功能
  - 低概率边缘情况
  - 加载状态、空状态展示

#### 测试用例格式

使用此结构编写每个测试用例：

```markdown
## [模块名称]模块

### P0 测试用例

#### TC-[MODULE]-001: [测试用例标题]
**优先级**：P0
**测试类型**：功能测试 / 集成测试 / API测试
**描述**：[简要描述正在测试的内容]

**前置条件**：
- [所需设置或数据]
- [用户权限或角色需要]

**测试步骤**：
1. [步骤 1]
2. [步骤 2]
3. [步骤 3]

**预期结果**：
- [预期结果]

**实现参考**：
[描述实现逻辑并引用代码]
示例：此功能监听 SHOPLINE 订单 webhook，按客户 ID 过滤，通过 API 查询 Klaviyo 用户资料，然后报告事件。

---
```

#### 业务逻辑实现细节

对于业务逻辑测试用例，必须包括：

1. **代码流程**：功能在代码层面如何工作
2. **数据流**：数据如何在系统中流动
3. **集成点**：涉及的外部服务 or 插件
4. **数据库操作**：创建/更新/删除了什么数据

示例：
```
实现参考：
1. Webhook Handler (internal/domain/webhook/api.go:45) 接收 SHOPLINE order.shipped 事件
2. OrderService.ExtractCustomerID (internal/domain/order/service.go:120) 从订单提取客户 ID
3. KlaviyoClient.GetCustomerProfile (internal/client/klaviyo/client.go:89) 查询客户资料
4. 如果客户在 Klaviyo 中存在，KlaviyoClient.ReportEvent (internal/client/klaviyo/client.go:145) 发送发货事件
5. 结果记录到 (internal/domain/webhook/service.go:78)
```

#### 页面交互测试用例格式

当 Figma 设计稿包含交互连接时，必须生成页面交互测试用例。使用以下格式：

```markdown
#### TC-UI-[MODULE]-001: [交互测试标题]
**优先级**：P0/P1
**测试类型**：交互测试
**设计来源**：Figma [页面名] → [Frame名]
**交互类型**：页面导航 / 按钮点击 / 弹窗交互 / 开关切换 / 表单提交

**初始页面状态**：
- [描述用户当前所在的页面和状态]

**操作步骤**：
1. [用户操作，如"点击XX按钮"]
2. [预期页面响应，如"页面跳转到XX"]
3. [验证目标页面的元素]

**预期 UI 行为**：
- [页面跳转/弹窗/状态变化的描述]
- [交互后的 UI 元素状态]
- [动画或过渡效果如果需要验证]

**Figma 原型参考**：
- 源 Frame：[Frame名] (ID: [node-id])
- 目标 Frame：[Frame名] (ID: [node-id])
- 交互类型：[ON_CLICK → NAVIGATE / OPEN_OVERLAY / 等]

---
```

### 步骤 5：保存输出

默认生成 Markdown 和 XLSX 两种格式的测试用例。XMind 格式仅在用户明确要求时才生成（如用户说"需要 xmind"、"生成思维导图"等）。

#### 增量增改模式的输出

如果本次是增量增改模式（在已有文件上增改），则：

1. **直接编辑已有 Markdown 文件**：
   - 使用 Edit 工具在已有 Markdown 文件末尾追加新模块和测试用例
   - 新模块追加到文件末尾，保持 `---` 分隔
   - 如果需要修改已有用例，使用 Edit 工具精准修改旧内容

2. **重新生成 XLSX 文件**：
   ```bash
   # 增改后必须重新生成 XLSX，用更新后的 Markdown 文件作为输入
   python <skill目录>/scripts/generate_xlsx.py <测试用例输出目录>/[已有的filename].md
   # XLSX 会自动覆盖同目录下的同名 xlsx 文件
   ```

3. **输出提示**：告知用户在已有文件基础上增改了哪些内容：
   - 列出新增的模块名
   - 列出新增的测试用例数量和编号范围
   - 说明 XLSX 已重新生成

**示例输出提示**：
```
已在已有文件基础上增改，新增内容：
- 新增模块：C端评价创建模块、C端留言创建模块、C端查询过滤模块
- 新增测试用例：37 条（P0: 26 条，P1: 11 条）
- 编号范围：TC-C-001 ~ TC-C-037
- XLSX 文件已重新生成
```

#### 全新生成模式的输出

#### 5.1 保存 Markdown 文件

```bash
# 测试用例输出目录（自动创建）
# 所有生成的文件保存到用户指定的项目输出目录下

# 保存为描述性文件名
# 格式：{项目名}-功能测试用例-{日期}.md
```

#### 5.2 生成 XLSX 导入文件（测试用例管理平台导入）

生成符合 `testcase-template.xlsx` 模板格式的 XLSX 文件，可直接导入测试用例管理平台：

```bash
python <skill目录>/scripts/generate_xlsx.py <测试用例输出目录>/[filename].md
# 输出：<测试用例输出目录>/[filename].xlsx（可导入 XLSX 格式）
# 可选参数：
#   --assignee NAME    指定负责人（默认：<YOUR_ASSIGNEE>）
#   自定义输出路径：python generate_xlsx.py input.md /path/to/output.xlsx
```

XLSX 格式列定义（14列）：
- **模块一~模块六**：从 Markdown H2 标题提取的模块层级
- **用例名称**：TC-ID + 标题
- **优先级**：统一为 3（整数）
- **负责人**：默认 <YOUR_ASSIGNEE>（可通过 --assignee 自定义）
- **前置条件**：合并为一个单元格，换行分隔
- **用例步骤**：编号格式，步骤1/继步骤2...
- **预期结果**：合并实现参考，以「【实现参考】」前缀附加在末尾
- **关联自动化用例**：留空
- **备注**：测试用例描述

注意：XLSX 文件中优先级统一写为 3，这是导入平台时的默认值。Markdown 和 XMind 中的优先级保持原始分类（P0/P1/P2）不变。

#### 5.3 生成 XMind 文件（仅在用户明确要求时）

当用户明确要求生成 XMind/思维导图时，提供两种 XMind 格式：

**XMind 8 格式**（兼容所有 XMind 版本）：

```bash
python <skill目录>/scripts/generate_xmind.py <测试用例输出目录>/[filename].md
# 输出：<测试用例输出目录>/[filename].xmind（XMind 8 XML 格式）
```

**XMind Zen 格式**（兼容 XMind 2020+/Zen/移动端）：

```bash
python <skill目录>/scripts/generate_xmind_zen.py <测试用例输出目录>/[filename].md
# 输出：<测试用例输出目录>/[filename].zen.xmind（XMind Zen JSON 格式）
```

两种 XMind 格式的区别：
- **XMind 8 (.xmind)**：XML 格式，兼容 XMind 8 及所有后续版本，使用 `xmind-sdk` 库生成
- **XMind Zen (.zen.xmind)**：JSON 格式，专为 XMind 2020+、XMind Zen、XMind iOS/Android 优化，纯 Python 标准库生成，无需额外依赖

**默认输出文件**：
- `<测试用例输出目录>/[项目]-[功能]-测试用例-[日期].md` - Markdown 格式
- `<测试用例输出目录>/[项目]-[功能]-测试用例-[日期].xlsx` - XLSX 可导入格式

**用户要求 XMind 时额外输出**：
- `<测试用例输出目录>/[项目]-[功能]-测试用例-[日期].xmind` - XMind 8 思维导图格式
- `<测试用例输出目录>/[项目]-[功能]-测试用例-[日期].zen.xmind` - XMind Zen 思维导图格式

**文件内容必须使用中文**，包括所有标题、描述、步骤和预期结果。

## 示例用法

### 示例 1：全新生成测试用例

**用户**："我需要 Klaviyo 订单同步功能的测试用例。这是一个迭代项目。链接如下：https://shopline.yuque.com/ltxgkw/fkuadl/tp4qg4ki00camk5u（需求）https://shopline.yuque.com/ltxgkw/fkuadl/tech-doc-123（技术文档1）https://shopline.yuque.com/ltxgkw/fkuadl/tech-doc-456（技术文档2）https://www.figma.com/design/521jxVp1TfrEFlvc9dR26X/CIN7?node-id=186-5610（figma）"

**助手**：[加载技能并遵循工作流程]
1. 使用 Task 代理完整读取需求文档（不只是第一页）
2. 使用 Task 代理并行完整读取所有技术文档（文档1和文档2都必须完整读取，不能遗漏）
3. 使用 chrome-devtools 打开 Figma 设计（60秒超时处理缓慢加载），截图+快照获取交互信息
4. 运行 `git diff master...HEAD` 查看变更
5. 按以下方式生成全面测试用例：
   - 客户管理模块
   - 订单同步模块
   - 事件报告模块
6. 保存为 Markdown：`cin7-klaviyo-sync-测试用例.md`
7. 默认生成 Markdown + XLSX 两种格式（XMind 仅在用户明确要求时生成）

**输出文件**：
- `<测试用例输出目录>/cin7-klaviyo-sync-测试用例.md` - Markdown 格式
- `<测试用例输出目录>/cin7-klaviyo-sync-测试用例.xlsx` - XLSX 可导入格式

### 示例 2：在已有文件基础上增量增改

**用户**："这是PRD：https://shopline.yuque.com/ltxgkw/fkuadl/xxx，技术文档：https://shopline.yuque.com/ltxgkw/nvdpcp/xxx，已有测试用例在 <测试用例输出目录>/gsv-comment-196-内容过滤屏蔽词-测试用例-2026-05-22.md，需要你补充C端测试用例"

**助手**：[识别为增量增改模式，因为用户提供了已有文件路径且要求"补充"]
1. 读取已有 Markdown 文件，分析已覆盖的模块和 TC-ID：
   - 已有模块：屏蔽词设置模块、屏蔽词导入导出模块、进度管理模块、留言板筛选模块、评价筛选模块、评价导入模块、AI标签与负面评价模块、留言板设置模块、MongoDB表设计验证、C端评价创建接口改动、物理删除改成软删除、gRPC接口
   - 已有 TC-ID 前缀：FORBID、IMPORT、EXPORT、PM、MSG、CMT、AI、SET、DB、C-END、SOFT-DEL、GRPC
   - 已有 TC-ID 编号范围：TC-FORBID-001~008, TC-IMPORT-001~005, 等
2. 完整读取需求文档和技术文档
3. 分析 C 端代码实现，识别已有用例未覆盖的 C 端场景
4. 生成新的 TC-ID（如使用 `C-END` 前缀，从已有最大编号继续递增，或使用新前缀如 `C`）
5. 使用 Edit 工具在已有文件末尾追加新模块和测试用例
6. 重新生成 XLSX 文件：
   ```bash
   python <skill目录>/scripts/generate_xlsx.py <测试用例输出目录>/gsv-comment-196-内容过滤屏蔽词-测试用例-2026-05-22.md
   ```
7. 告知用户增改内容

**关键**：增量增改时不要创建新文件，直接编辑已有 Markdown 文件，然后重新生成 XLSX

## 输出示例结构

```markdown
# Cin7 插件 - 订单同步功能测试用例

生成时间：2024-01-15
项目：Cin7-Shopline 集成
类型：迭代开发

---

## 客户管理模块

### P0 测试用例

#### TC-CUST-001: 新客户同步到 Klaviyo
**优先级**：P0
**测试类型**：集成测试
**描述**：验证在 Shopline 创建的新客户成功同步到 Klaviyo

**前置条件**：
- Shopline 商店安装了 Cin7 插件
- 配置了 Klaviyo API 凭证
- 准备好测试客户数据

**测试步骤**：
1. 在 Shopline 管理员创建新客户
2. 等待 webhook 触发（最多 30 秒）
3. 查询 Klaviyo API 验证客户存在
4. 验证客户数据与 Shopline 数据匹配

**预期结果**：
- 客户在 30 秒内出现在 Klaviyo
- 所有客户字段（email、name、phone）匹配
- 客户 ID 映射正确存储

**实现参考**：
1. Customer Webhook Handler (internal/domain/customer/api.go:23) 接收 'customer.created' 事件
2. CustomerService.SyncToKlaviyo (internal/domain/customer/service.go:56) 验证客户数据
3. KlaviyoClient.CreateProfile (internal/client/klaviyo/client.go:123) 通过 Klaviyo API 创建资料
4. 映射通过 StoreAppConfigRepository 存储 (internal/repository/config.go:89)

---

### P1 测试用例

#### TC-CUST-002: 客户分页查询
**优先级**：P1
**测试类型**：功能测试
**描述**：验证客户列表查询正确处理分页

**前置条件**：
- 测试商店至少有 150 个客户
- Cin7 插件已配置

**测试步骤**：
1. 查询客户列表 page=1, limit=50
2. 验证响应包含 50 个客户
3. 查询 page=2，验证是不同的集合
4. 查询 page=4，验证为空结果集

**预期结果**：
- 分页正确工作
- 各页之间没有重复客户
- 最后一页正确返回空或部分结果

**实现参考**：
CustomerListService.QueryWithPagination (internal/domain/customer/service.go:201) 使用 dao.Q.Customer.WithContext(ctx).Limit(limit).Offset(offset) 进行分页...

---
```

## 有效测试用例的提示

1. **具体明确**：包含确切的字段名、API 端点和函数引用
2. **优先覆盖正常流程**：P0 用例应关注主要成功场景
3. **像用户一样思考**：从 Figma 考虑真实用户行为和流程
4. **包含数据设置**：每个测试用例应独立并有清晰的前置条件
5. **引用实现**：帮助开发人员理解"如何"而不仅仅是"什么"
6. **考虑集成**：对于插件，彻底测试集成点
7. **错误场景**：考虑网络失败、API 错误、验证错误

## 重要说明

1. 始终使用 chrome-devtools MCP 工具浏览文档 - 不要假设内容
2. 对于长文档，必须完整读取所有内容，使用分段读取或 Task 代理
3. 读取实际代码实现以理解逻辑流程
4. **Figma 设计稿优先使用浏览器截图+快照方式**，API 脚本作为补充（API 限流严重不稳定）
5. 对于迭代项目，关注变更的代码区域但也不要忽略与现有功能的集成
6. 如果无法访问文档链接，向用户请求澄清或替代访问方式
7. 默认生成 Markdown + XLSX 两种输出文件（XMind 仅在用户明确要求时生成）
8. **所有内容必须使用中文**：包括模块名称、测试用例标题、描述、步骤和预期结果
9. XMind 文件仅在用户明确要求时生成（默认不生成思维导图）
10. 使用 Task 代理的 "explore" 模式完整读取长文档，确保不会遗漏任何章节
11. **Figma 交互测试用例**：当设计稿包含原型交互时，必须生成页面导航、按钮点击、弹窗交互等 UI 测试用例
12. **增量增改模式**：当用户提供了已有测试用例文件路径或要求"补充"、"增改"、"在已有基础上添加"时，必须进入增量增改模式：
    - 使用 Edit 工具直接编辑已有 Markdown 文件，追加新模块和测试用例
    - **不要创建新文件**，修改已有文件后再重新生成 XLSX
    - 读取已有文件时必须提取 TC-ID 前缀和编号，避免编号冲突
    - 新模块追加到文件末尾，保持 `---` 分隔
    - 增改完成后必须重新运行 `generate_xlsx.py` 生成更新后的 XLSX

## 文档读取策略

### 对于 Yuque 长文档

**问题**：`chrome-devtools_take_snapshot` 只能读取可见部分，长文档会被截断。

**解决方案**：使用以下策略之一：

1. **使用 Grep 搜索章节标题**：
   ```
   使用 Grep 工具搜索文档中的章节标题（如 "### "、"#### "），找到所有章节，然后逐节读取
   ```

2. **分段读取**：
   ```
   使用 Read 工具的 offset/limit 参数：
   - 第一次读取：offset=1, limit=2000（前 2000 行）
   - 第二次读取：offset=2001, limit=2000（第 2001-4000 行）
   - 继续读取直到读到文档结尾
   ```

3. **使用 Task 代理**：
   ```
   使用 Task 工具启动 "explore" 模式的子代理，让它使用 Grep 和 Read 工具配合 offset/limit
   完整读取文档的所有部分，而不是只读取第一页。
   ```

**读取检查清单**：
- [ ] 所有模块章节
- [ ] 所有子章节
- [ ] 字段映射表
- [ ] 状态机定义
- [ ] API 接口列表
- [ ] 错误处理逻辑
- [ ] 边缘情况说明

### 对于代码文件

完整读取关键代码文件：
- Service 层代码
- Repository 层代码
- API 层代码
- Model 定义
- 配置文件

使用 Read 工具分段读取大文件，确保不会遗漏任何实现细节。

## XMind 生成说明（仅在用户明确要求时生成）

XMind 格式不是默认输出。只有当用户明确提出"需要 xmind"、"生成思维导图"、"导出 xmind"等要求时，才运行以下脚本。

提供两种 XMind 格式生成脚本：

### XMind 8 格式（generate_xmind.py）

使用 `xmind-sdk` 库输出 XMind 8 XML 格式（兼容所有 XMind 版本）：

**依赖**：`pip install xmind-sdk`

```bash
python <skill目录>/scripts/generate_xmind.py <测试用例输出目录>/test-cases.md
# 输出：<测试用例输出目录>/test-cases.xmind
```

### XMind Zen 格式（generate_xmind_zen.py）

使用纯 Python 标准库生成 JSON 格式（兼容 XMind 2020+、XMind Zen、移动端）：

**依赖**：无需额外依赖（使用 Python 内置 zipfile + json）

```bash
python <skill目录>/scripts/generate_xmind_zen.py <测试用例输出目录>/test-cases.md
# 输出：<测试用例输出目录>/test-cases.zen.xmind
```

### XLSX 导入格式（generate_xlsx.py）

生成符合 `testcase-template.xlsx` 模板的 14 列格式 XLSX 文件，可以直接导入测试用例管理平台：

**依赖**：`pip install openpyxl`

```bash
python <skill目录>/scripts/generate_xlsx.py <测试用例输出目录>/test-cases.md
# 输出：<测试用例输出目录>/test-cases.xlsx

# 自定义负责人
python <skill目录>/scripts/generate_xlsx.py <测试用例输出目录>/test-cases.md --assignee <YOUR_ASSIGNEE>

# 自定义输出路径
python <skill目录>/scripts/generate_xlsx.py <测试用例输出目录>/test-cases.md /path/to/output.xlsx
```

XLSX 格式说明：
- 模板 14 列格式：模块一~模块六、用例名称、优先级、负责人、前置条件、用例步骤、预期结果、关联自动化用例、备注
- 优先级映射：XLSX 中统一为 3（整数），Markdown/XMind 中保留原始 P0/P1/P2
- 实现参考合并到「预期结果」列末尾，以【实现参考】前缀标识
- 负责人默认 <YOUR_ASSIGNEE>

### 三种格式对比

| 特性 | XMind 8 (.xmind) | XMind Zen (.zen.xmind) | XLSX (.xlsx) |
|------|-----------------|----------------------|---------------|
| 内部格式 | XML | JSON | Excel |
| 兼容性 | XMind 8 及所有后续版本 | XMind 2020+、Zen、iOS/Android | 测试用例管理平台导入 |
| 额外依赖 | 需要 xmind-sdk | 无（纯标准库） | 需要 openpyxl |
| 优先级表示 | P0/P1/P2 marker | P0/P1/P2 marker | 统一为 3 |
| 推荐场景 | 需要兼容老版本 | 现代版本优先选择 | 平台导入 |
| 生成条件 | 用户明确要求时 | 用户明确要求时 | 默认生成 |

### 共同功能

所有脚本都支持：
1. 解析 Markdown 文件中的结构
2. 提取模块、优先级和测试用例
3. 添加优先级标识（P0/P1/P2 对应不同标记方式）
4. 完整保留层级结构（模块 → 优先级 → 测试用例 → 详细信息 → 子项）

确保 Markdown 文件遵循正确的格式：
- `## [模块名]模块` 作为顶级模块
- `### P0 测试用例` / `### P1 测试用例` / `### P2 测试用例` 作为优先级
- `#### TC-[MODULE]-###: [标题]` 作为测试用例标题

---

**重要**：生成测试用例时请确保使用中文内容，并完整读取所有文档章节。