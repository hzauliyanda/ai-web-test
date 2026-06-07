# p3-ui-test-case-generator — UI 测试用例生成器

从功能地图 + 功能测试用例自动生成场景化 UI 自动化测试用例。每个 UI 场景映射到对应的功能用例 TC-ID，实现追溯。生成的 YAML 文件可直接用 p4-browser-test-runner-devtools 执行。

## 它能做什么

- 解析功能地图，提取页面结构、筛选条件、操作按钮、表单字段等元素信息
- 解析功能测试用例，提取 TC-ID、模块归属、优先级、测试类型
- 自动生成 6 类测试场景：列表页、新增/编辑表单、详情查看、端到端业务流、Tab 切换、数据导出
- 建立 UI 场景与功能用例 TC-ID 的追溯映射
- 按依赖关系编排执行顺序
- 输出 YAML 测试脚本，可被 p4-browser-test-runner-devtools 直接执行

## 前置要求

- 已有 `p1-web-explorer` 生成的功能地图 Markdown 文件
- 已有 `p2-test-case-generator` 生成的功能测试用例 Markdown 文件
- 业务系统 URL
- 登录账号密码（如需登录）

## 使用方法

### 在流水线中使用

```
/ai-web-test-pipeline
→ p1 探索 + p2 用例生成完成后，自动调用 p3 生成 UI 自动化用例
```

### 单独使用

```
/p3-ui-test-case-generator
```

然后按提示提供：
1. **功能地图文件路径**（p1-web-explorer 生成的 .md 文件）
2. **功能测试用例文件路径**（p2-test-case-generator 生成的 .md 文件）
3. **是否需要登录** + 登录信息
4. **覆盖范围**：全部页面 / 仅核心页面 / 指定页面

## 输入参数

| 参数 | 说明 | 必填 |
|------|------|------|
| 功能地图 | p1-web-explorer 生成的 .md 文件路径 | 是 |
| 功能测试用例 | p2-test-case-generator 生成的 .md 文件路径 | 是 |
| 业务系统 URL | 如 `https://example.com` | 是 |
| 登录配置 | 登录页 URL、账号、密码、元素描述、登录类型 | 视情况 |
| 覆盖范围 | 全部页面 / 仅核心页面 / 指定页面 | 是 |
| 输出目录 | 默认与功能地图同目录 | 否 |

## 输出

```
<输出目录>/
├── {项目名}-UI测试用例.md          # 场景化测试用例文档（含 TC-ID 追溯矩阵）
└── tests/
    ├── suite.yaml                  # 测试套件（登录配置 + 执行顺序 + 依赖）
    ├── traceability.json           # UI 场景 ↔ 功能用例 TC-ID 追溯映射
    ├── s1-xxx.yaml                 # 场景 1 测试步骤
    ├── s2-xxx.yaml                 # 场景 2 测试步骤
    └── ...
```

### 文件说明

| 文件 | 内容 |
|------|------|
| `{项目名}-UI测试用例.md` | 场景化文档，含 TC-ID 追溯矩阵、执行顺序表、每个场景的详细步骤 |
| `suite.yaml` | 测试套件配置：base_url、登录步骤、场景列表及依赖关系 |
| `traceability.json` | JSON 格式的 UI 场景 → TC-ID 映射，供报告生成器使用 |
| `s{n}-xxx.yaml` | 单个场景的测试步骤，使用 navigate/click/input/select/assert/wait/scroll 操作 |

## 内部工作流程

### 1. 收集输入信息
通过交互式问答获取功能地图路径、功能用例路径、登录配置、覆盖范围。

### 2. 解析输入文件

#### 2.1 解析功能地图
从功能地图中提取 11 个维度的结构化信息：

| 维度 | 来源 | 用途 |
|------|------|------|
| 页面清单 | 第一章 | 场景入口地址 |
| 导航菜单 | 第二章 | 导航步骤生成 |
| 筛选条件 | 第三章 | 查询场景生成 |
| 操作按钮 | 第三章 | 点击步骤生成 |
| 数据列表 | 第三章 | 列表验证步骤 |
| 表单字段 | 第三章 | 表单填写步骤 |
| Tab 页签 | 第三章 | Tab 切换步骤 |
| 页面跳转关系 | 第四章 | 场景依赖分析 |
| 业务流程 | 第五章 | 端到端场景生成 |
| 状态流转 | 第六章 | 状态验证步骤 |
| 枚举值汇总 | 第七章 | 测试数据准备 |

#### 2.2 解析功能测试用例
提取 TC-ID、功能模块、优先级、测试类型、用例描述、前置条件、测试步骤、预期结果。

#### 2.3 建立 TC-ID 与 UI 场景的映射
- 1 个 UI 场景可对应多个功能用例
- 同一模块/页面的 TC-ID 归入同一场景
- 功能地图中未找到对应页面的 TC-ID 标记为"需手工测试"

### 3. 生成测试场景

自动生成 6 类场景：

| 类型 | 触发条件 | 生成内容 |
|------|----------|----------|
| 列表页场景 | 功能地图中的列表页 | 打开页面、筛选查询、重置、下拉筛选、分页 |
| 新增/编辑表单 | 功能地图中的表单页 | 正常提交、必填校验、下拉选择、字符上限 |
| 详情查看 | 依赖列表页数据 | 进入详情、详情内列表、操作按钮 |
| 端到端业务流 | 第五章业务流程 | 跨页面的完整业务操作 |
| Tab 切换 | 含 Tab 页签的页面 | Tab 切换验证、Tab 内操作 |
| 数据导出 | 有导出按钮的页面 | 导出数据验证 |

**场景编号**：S 前缀 + 编号（S1、S2...），按依赖关系排列。

### 4. 编排执行顺序
分析场景间的依赖关系（数据依赖、状态依赖），按拓扑排序编排执行顺序。

### 5. 生成 YAML 测试步骤
为每个场景生成 browser-test-agent 格式的 YAML：
- **操作写具体**：使用功能地图中的实际元素名称（按钮名、字段名、选项名）
- **断言写宽泛**：只验证页面状态变化，不写死具体文案
- **步骤编号**：`S{场景号}-{序号}` 格式
- **中文描述**：AI 执行器使用自然语言效果更好

### 6. 输出文件
生成 Markdown 文档、suite.yaml、traceability.json 和各场景 YAML 文件。

## YAML 格式示例

### suite.yaml

```yaml
name: "处罚任务下发 - UI 测试套件"
base_url: "https://test-risk.inshopline.com"

login:
  enabled: true
  url: "https://test-risk.inshopline.com/login"
  steps:
    - action: input
      description: "账号输入框"
      value: "username"
    - action: input
      description: "密码输入框"
      value: "password"
    - action: click
      description: "登录按钮"
    - action: assert
      description: "登录成功，页面跳转"

cases:
  - file: s1-penalty-task-create.yaml
    name: "S1: 处罚任务创建"
    depends_on: []
    entry_url: "/penaltyTask/modify-event"

  - file: s2-task-list-query.yaml
    name: "S2: 任务列表查询"
    depends_on: ["S1"]
    entry_url: "/penaltyTask"
```

### 场景 YAML

```yaml
name: "S1-处罚任务创建"
base_url: "https://test-risk.inshopline.com"

steps:
  # S1-01: 导航到新增页面
  - action: navigate
    url: "/penaltyTask/modify-event"
    description: "S1-01: 导航到新增处罚任务页面"

  # S1-02: 填写表单
  - action: input
    description: "任务名称输入框"
    value: "自动化测试任务"

  # S1-03: 提交
  - action: click
    description: "点击提交按钮"

  # S1-04: 验证
  - action: assert
    description: "提交成功，页面跳转回列表页"
```

### traceability.json

```json
{
  "project": "处罚任务下发",
  "generated": "2026-06-07",
  "mappings": {
    "S1": {
      "name": "S1: 处罚任务创建",
      "tc_ids": ["TC-SUBMIT-001", "TC-SUBMIT-002", "TC-SUBMIT-003"],
      "priority": "P0",
      "depends_on": [],
      "entry_url": "/penaltyTask/modify-event"
    }
  },
  "uncovered_tc_ids": [
    {"tc_id": "TC-API-050", "reason": "API 类型用例，无法 UI 自动化", "priority": "P1"}
  ]
}
```

## 目录结构

```
p3-ui-test-case-generator/
├── SKILL.md              # Skill 定义文件
├── README.md             # 本文件
└── scripts/
    └── generate_xlsx.py  # 软链接到 p2-test-case-generator 的脚本
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
cp -r ai-web-test/p3-ui-test-case-generator ~/.claude/skills/
# Codex
cp -r ai-web-test/p3-ui-test-case-generator ~/.codex/skills/
# OpenCode
cp -r ai-web-test/p3-ui-test-case-generator ~/.config/opencode/skills/
```

## 重要说明

1. **双文件输入**：功能地图提供页面结构和元素信息，功能测试用例提供 TC-ID 和覆盖维度
2. **TC-ID 追溯**：每个 UI 场景必须映射到功能用例 TC-ID
3. **断言宽泛**：只验证页面状态变化，不写死文案和具体数量
4. **元素名称精确**：操作步骤中使用功能地图中的实际字段名、按钮名、选项名
5. **场景依赖编排**：按功能地图中的业务流程和页面跳转关系排列执行顺序
6. **不包含登录步骤**：登录由 suite.yaml 统一管理
7. **YAML 兼容 p4**：生成的 YAML 可直接用 p4-browser-test-runner-devtools 执行
