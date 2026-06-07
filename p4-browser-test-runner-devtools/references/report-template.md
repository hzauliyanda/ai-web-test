# HTML 报告模板参考

## 报告结构

```
报告头部（标题、日期、环境、执行人）
├── 概览统计卡片（总数、通过、失败、跳过、N/A）
├── P0 用例汇总表
├── 按模块分组的 TC-ID 覆盖表
│   ├── 模块1（折叠面板）
│   │   └── 表格：TC-ID | 优先级 | 类型 | 描述 | 结果 | 详情
│   ├── 模块2
│   │   └── ...
│   └── 模块N
├── UI 可自动化覆盖统计
└── 失败详情（展开错误信息）
```

## HTML 生成要点

### 数据来源

1. **执行结果**：来自 Chrome DevTools MCP 执行的步骤记录
2. **TC-ID 映射**：从 YAML 文件注释中提取（如 `# S1-01: 进入新增处罚页面 [TC-SUBMIT-001]`）
3. **功能用例文件**：用户提供的功能测试用例 Markdown 文件，包含完整的 TC-ID 列表、模块归属、优先级、测试类型
4. **场景-YAML**：suite.yaml 中每个 case 的 tc_ids 字段

### TC-ID 与场景映射逻辑

1. 读取每个场景 YAML，从注释中提取步骤到 TC-ID 的映射
2. 读取 suite.yaml，获取场景级别的 tc_ids
3. 场景结果映射到 TC-ID：
   - 场景全部通过 → 关联 TC-ID 标记为通过
   - 场景部分失败 → 根据失败步骤的 TC-ID 注释区分
   - 场景跳过 → 关联 TC-ID 标记为跳过
4. 功能用例文件中有但 YAML 未覆盖的 TC-ID → 标记为 N/A（不适用UI自动化）

### 结果判定规则

| 条件 | TC-ID 结果 |
|------|-----------|
| 关联步骤全部通过 | ✅ 通过 |
| 关联步骤中有失败 | ❌ 失败 |
| 场景被跳过（依赖失败） | ⏭️ 跳过 |
| 功能用例中存在但无 UI 场景覆盖 | N/A |
| 功能用例标记为 API/集成/性能测试类型 | N/A |

### CSS 样式关键定义

```css
:root {
  --pass: #52c41a; --fail: #ff4d4f; --skip: #faad14; --warn: #fa8c16;
  --na: #bfbfbf; --primary: #1890ff;
}
/* 卡片统计 */
.summary { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:14px; }
/* 折叠面板 */
.st { cursor:pointer; } .st::before { content:"▶"; } .st.open::before { transform:rotate(90deg); }
.sb { max-height:0; overflow:hidden; transition:all .3s; } .sb.show { max-height:20000px; }
/* 状态徽章 */
.b-pass { background:#f6ffed; color:#52c41a; } .b-fail { background:#fff2f0; color:#ff4d4f; }
.b-skip { background:#fffbe6; color:#fa8c16; } .b-na { background:#f5f5f5; color:#999; }
/* 失败行高亮 */
.fail-row { background:#fff2f0 !important; }
```

### 报告文件命名

`{项目名}-UI自动化测试报告-{YYYYMMDD}.html`

输出路径与 YAML 测试文件同目录的上级目录。

### 生成后操作

1. 使用 Write 工具写入 HTML 文件
2. 使用 Bash `open` 命令在浏览器中打开
3. 向用户展示报告路径和概要统计
