# p2-test-case-generator — 测试用例生成器

为项目生成全面的功能测试用例。通过分析需求文档、技术文档、Figma 设计和代码实现，产出结构化的测试用例文件（Markdown + XLSX）。

## 它能做什么

- 从 Yuque 需求文档、技术文档中提取功能需求和验收标准
- 通过浏览器访问 Figma 设计稿，提取 UI 交互信息
- 分析项目代码（Git diff 或项目结构），理解实现逻辑
- 按功能模块组织测试用例，标注 P0/P1/P2 优先级
- 支持全新生成和增量增改两种模式
- 输出 Markdown 文件和可导入测试管理平台的 XLSX 文件

## 使用方法

### 在流水线中使用

```
/ai-web-test-pipeline
→ p1 探索完成后，自动调用 p2-test-case-generator 生成功能用例
```

### 单独使用

```
/p2-test-case-generator
```

然后按提示提供：
1. **需求文档链接**（Yuque，可多个）
2. **技术文档链接**（Yuque，可多个，必须全部读取）
3. **Figma 设计链接**（可选）
4. **项目类型**：新项目 / 迭代项目
5. **已有测试用例文件路径**（可选，增量增改时提供）

## 输入参数

| 参数 | 说明 | 必填 |
|------|------|------|
| 需求文档链接 | Yuque 文档 URL，可提供多个 | 是 |
| 技术文档链接 | Yuque 文档 URL，可提供多个 | 是 |
| Figma 设计链接 | UI/UX 设计稿 URL | 否 |
| 项目类型 | 新项目 或 迭代项目 | 是 |
| 已有用例文件路径 | 增量增改时提供已有 Markdown 文件路径 | 否 |
| 功能地图 | p1-web-explorer 生成的功能地图文件路径 | 否（流水线自动传入） |
| 输出目录 | 测试用例文件保存目录 | 是 |
| 项目名 | 用于文件命名 | 是 |

## 输出

### Markdown 文件

格式：`{项目名}-功能测试用例-{date}.md`

按模块和优先级组织，包含完整的标题、描述、前置条件、测试步骤、预期结果和实现参考。

```markdown
## 客户管理模块

### P0 测试用例

#### TC-CUST-001: 新客户同步到系统
**优先级**：P0
**测试类型**：集成测试
**描述**：验证新客户创建后成功同步

**前置条件**：
- 系统已配置
- 准备好测试数据

**测试步骤**：
1. 创建新客户
2. 等待同步触发
3. 验证目标系统数据一致

**预期结果**：
- 客户数据成功同步
- 字段完全匹配

**实现参考**：
1. Webhook Handler (internal/domain/api.go:45) ...
```

### XLSX 文件

格式：`{项目名}-功能测试用例-{date}.xlsx`

14 列格式，可直接导入测试用例管理平台：

| 列 | 说明 |
|----|------|
| 模块一~模块六 | 从 Markdown H2 标题提取的模块层级 |
| 用例名称 | TC-ID + 标题 |
| 优先级 | 统一为整数 3（导入平台默认值） |
| 负责人 | 默认值，可通过 `--assignee` 自定义 |
| 前置条件 | 合并为一个单元格 |
| 用例步骤 | 编号格式：步骤1/继步骤2... |
| 预期结果 | 含实现参考（【实现参考】前缀） |
| 关联自动化用例 | 留空 |
| 备注 | 测试用例描述 |

### XMind 文件（仅在用户明确要求时生成）

| 格式 | 后缀 | 兼容性 | 依赖 |
|------|------|--------|------|
| XMind 8 | `.xmind` | XMind 8 及所有后续版本 | `xmind-sdk` |
| XMind Zen | `.zen.xmind` | XMind 2020+、Zen、移动端 | 无（纯标准库） |

## 两种模式

### 全新生成（默认）

从零开始创建完整测试用例文件。读取所有文档和代码，按模块组织生成全部用例。

### 增量增改

当用户提供已有测试用例文件时自动进入：

1. 读取已有文件，分析已覆盖的模块和 TC-ID
2. 识别已有编号体系（前缀和编号范围）
3. 只补充已有文件中不存在的模块和场景
4. 新内容追加到文件末尾，不创建新文件
5. 修改完成后重新生成 XLSX

**触发条件**：用户说"补充"、"增改"、"在已有基础上添加" 或 提供了已有文件路径。

## 内部工作流程

### 1. 收集输入信息
通过交互式问答获取文档链接、项目类型、输出目录等参数。

### 2. 浏览文档
- **需求文档**：使用 Task 代理分段读取，确保完整读取所有章节
- **技术文档**：逐个完整读取所有文档，不遗漏
- **Figma 设计**：优先通过 Chrome DevTools 浏览器截图 + a11y 快照获取设计信息（Figma API 仅作备选）

### 3. 分析项目代码
- **新项目**：读取项目结构、入口文件、业务逻辑代码
- **迭代项目**：通过 `git diff master...HEAD` 分析代码变更

### 4. 生成测试用例
按功能模块组织，每个模块包含 P0/P1/P2 优先级分类：
- **P0（核心功能）**：必须具备的功能、主要用户流程、关键业务逻辑
- **P1（重要但非核心）**：次要功能、替代流程、表单验证
- **P2（锦上添花）**：UX 改进、低概率边缘情况

### 5. 保存输出
- 写入 Markdown 文件
- 运行 `generate_xlsx.py` 生成 XLSX
- （如用户要求）运行 `generate_xmind.py` 生成 XMind

## 目录结构

```
p2-test-case-generator/
├── SKILL.md              # Skill 定义文件
├── README.md             # 本文件
└── scripts/
    ├── generate_xlsx.py        # Markdown → XLSX 转换
    ├── generate_xmind.py       # Markdown → XMind 8 格式
    ├── generate_xmind_zen.py   # Markdown → XMind Zen 格式
    ├── fetch_figma.py          # Figma API 数据获取（备选方案）
    └── XMIND_STYLES.md         # XMind 样式配置
```

## 脚本使用

### generate_xlsx.py

```bash
# 基本用法
python scripts/generate_xlsx.py <测试用例.md>

# 指定负责人
python scripts/generate_xlsx.py <测试用例.md> --assignee "张三"

# 自定义输出路径
python scripts/generate_xlsx.py <测试用例.md> /path/to/output.xlsx
```

**依赖**：`pip install openpyxl`

### generate_xmind.py / generate_xmind_zen.py

```bash
python scripts/generate_xmind.py <测试用例.md>       # XMind 8 格式
python scripts/generate_xmind_zen.py <测试用例.md>   # XMind Zen 格式
```

**依赖**：XMind 8 需要 `pip install xmind-sdk`，XMind Zen 无额外依赖。

### fetch_figma.py

```bash
export FIGMA_ACCESS_TOKEN="<YOUR_FIGMA_ACCESS_TOKEN>"
python scripts/fetch_figma.py "<Figma URL>"
python scripts/fetch_figma.py "<Figma URL>" -o figma-analysis.md
```

> **注意**：Figma API 存在限流和不稳定性，推荐优先使用浏览器方式。

## 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 默认负责人 | `TESTCASE_DEFAULT_ASSIGNEE` | `<YOUR_ASSIGNEE>` | XLSX 负责人列默认值 |
| Figma 令牌 | `FIGMA_ACCESS_TOKEN` | — | Figma API 访问令牌（备选方案使用） |

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
cp -r ai-web-test/p2-test-case-generator ~/.claude/skills/
# Codex
cp -r ai-web-test/p2-test-case-generator ~/.codex/skills/
# OpenCode
cp -r ai-web-test/p2-test-case-generator ~/.config/opencode/skills/
```

## 重要说明

1. **完整读取文档**：使用分段读取或 Task 代理确保不遗漏任何章节
2. **Figma 优先使用浏览器方式**：通过 Chrome DevTools 截图 + 快照获取，Figma API 仅作备选
3. **所有内容使用中文**：模块名称、标题、描述、步骤、预期结果
4. **增量增改不创建新文件**：直接编辑已有 Markdown 文件，修改后重新生成 XLSX
5. **技术文档必须全部读取**：用户可能提供多个链接，不能遗漏任何一个
6. **XMind 非默认输出**：仅在用户明确要求时才生成
