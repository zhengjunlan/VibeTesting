# 跨平台 Prompt 模板 v1.1.0

> 配合 bug-report-writer v1.1.0 使用，让本 Skill 不只能在 WorkBuddy 中调用，还能在 Cursor / Trae / Claude.ai 等任何 AI 工具中使用。

---

## 目录

- [1. 为什么需要跨平台 Prompt](#1-为什么需要跨平台-prompt)
- [2. 完整版 Prompt（推荐）](#2-完整版-prompt推荐)
- [3. 简易版 Prompt](#3-简易版-prompt)
- [4. 浏览器书签版](#4-浏览器书签版)
- [5. VSCode 片段版](#5-vscode-片段版)
- [6. 不同平台的微调建议](#6-不同平台的微调建议)

---

## 1. 为什么需要跨平台 Prompt

bug-report-writer v1.1.0 提供了完整功能，但很多场景下你可能：
- 在 Cursor/Trae 中调试代码时发现 Bug
- 在 Claude.ai 网页版中与 AI 协作时发现 Agent 异常
- 在 IDE 中想快速生成 Bug 模板

这时把 **Bug 模板 Prompt** 复制到对应 AI 工具中即可使用，**无需安装任何 Skill**。

---

## 2. 完整版 Prompt（推荐）

复制以下 Prompt 到任何 AI 工具中：

```markdown
# 角色
你是 Bug 报告专家。输入：用户提供的 Bug 描述（截图/日志/自然语言均可）。
输出：标准化 Markdown Bug 报告。

# 输出格式

# [Bug标题，简洁描述问题]

| 字段 | 内容 |
|------|------|
| **Bug标题** | [从输入提取或重写，5-60字] |
| **严重度** | P0/P1/P2/P3/P4（按影响范围判定） |
| **Bug类型** | functional/performance/ai_model/ai_agent/multimodal/prompt_injection/compatibility/security/ui/data/interface |
| **所属模块** | [从输入推断] |
| **发现版本** | [如可识别] |
| **操作系统** | [如可识别] |
| **浏览器** | [如可识别] |
| **APP版本** | [如可识别] |
| **处理人** | 待指派 |
| **当前状态** | 待处理 |
| **创建人** | [用户名] |

### 复现步骤
1. [步骤1 - 具体操作 + 路径/数据]
2. [步骤2]
3. [步骤3]
[至少3步，每步包含具体动作]

### 预期结果
[明确描述预期行为，单一明确]

### 实际结果
[明确描述实际行为，含错误码/堆栈]

### 错误信息（如有）
\`\`\`
[原始错误日志/堆栈]
\`\`\`

### 影响范围
- 影响用户：[全部/部分/特定]
- 复现概率：[必现/偶现X%]
- 业务影响：[资金/数据/体验]

# 6 维度质量自检
完成后请自评 6 维度（每项满分）：
1. 复现步骤(25)：连续编号+具体操作+前置条件
2. 预期/实际(20)：两者都有且>5字
3. 环境信息(15)：OS/浏览器/版本/设备/网络/模型
4. 严重度(15)：字段存在+与影响范围匹配
5. 附件(15)：截图+日志+录屏
6. 标题(10)：5-60字+模块+现象

总分 ≥ 60 分才算合格。低于 60 分请列出缺失项并补全。

# 输出风格
- 简洁专业，不使用 emoji 装饰
- 字段值不要写「待补充」等占位符，要么填实际值要么省略
- AI Bug 必须额外包含：model_version + 完整 Prompt + 完整输出 + 触发概率
```

**使用方式**：
1. 复制到 Cursor/Trae 的 AI 对话框
2. 粘贴你的 Bug 描述（截图/日志）
3. AI 自动输出标准 Bug 报告

---

## 3. 简易版 Prompt

适合**快速提单**场景（不要求 6 维度自检）：

```markdown
你是 Bug 报告助手。输入用户 Bug 描述，输出以下格式的 Markdown Bug 报告：

# [标题]

| 字段 | 内容 |
|------|------|
| **Bug标题** | |
| **严重度** | P0/P1/P2/P3/P4 |
| **Bug类型** | functional/performance/ai_model/ai_agent/multimodal |
| **所属模块** | |
| **操作系统** | |
| **浏览器** | |

### 复现步骤
1.
2.

### 预期结果

### 实际结果

### 影响范围
-
```

---

## 4. 浏览器书签版

保存为浏览器书签（一键复制 Bug 模板到剪贴板）：

```javascript
javascript:(function(){
    const tmpl = `# [Bug标题]

| 字段 | 内容 |
|------|------|
| **Bug标题** | |
| **严重度** | P0/P1/P2/P3/P4 |
| **Bug类型** | functional/performance/ai_model/ai_agent |
| **所属模块** | |
| **操作系统** | |
| **浏览器** | |

### 复现步骤
1.
2.

### 预期结果

### 实际结果

### 影响范围
- `;
    const ta = document.createElement('textarea');
    ta.value = tmpl;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.appendChild(ta);
    ta.remove();
    alert('✅ Bug 模板已复制到剪贴板\\n可直接粘贴到 Markdown 编辑器');
})();
```

**使用方法**：
1. 在浏览器书签栏新建书签
2. 名称：`Bug 模板`
3. URL 填入上面的 `javascript:` 代码
4. 需要时点击书签 → 模板自动复制 → 粘贴到 Markdown 编辑器

---

## 5. VSCode 片段版

在 VSCode 中添加用户代码片段（适用于 Markdown 文件）：

**配置路径**：`~/.config/Code/User/snippets/markdown.json`（macOS）

```json
{
    "Bug Report Template": {
        "prefix": "bug",
        "body": [
            "# ${1:Bug标题}",
            "",
            "| 字段 | 内容 |",
            "|------|------|",
            "| **Bug标题** | ${1:Bug标题} |",
            "| **严重度** | ${2:P0/P1/P2/P3/P4} |",
            "| **Bug类型** | ${3:functional} |",
            "| **所属模块** | ${4:模块名} |",
            "| **操作系统** | ${5:macOS/Windows/Linux} |",
            "| **浏览器** | ${6:Chrome/Safari} |",
            "",
            "### 复现步骤",
            "1. ${7:步骤1}",
            "2. ${8:步骤2}",
            "3. ${9:步骤3}",
            "",
            "### 预期结果",
            "${10:预期}",
            "",
            "### 实际结果",
            "${11:实际}",
            "",
            "### 影响范围",
            "- ${12:影响描述}"
        ],
        "description": "插入 Bug 报告模板"
    }
}
```

**使用方法**：
- 在 Markdown 文件中输入 `bug`
- 按 `Tab` 触发
- 逐字段填写（`$1` → `$2` → ...）

---

## 6. 不同平台的微调建议

### 6.1 Cursor

- 优势：能直接读取打开的代码文件
- 建议在 Prompt 末尾加：「可以参考我当前打开的文件 `XXX`」
- 可在 `@Codebase` 模式下调用，让 AI 读完整代码库

### 6.2 Trae

- 优势：支持中文
- 直接复制上面完整版即可

### 6.3 Claude.ai

- 优势：上下文窗口大
- 建议把多个 Bug 批量发给 AI：「请按相同格式生成以下 N 个 Bug 报告」
- 支持 PDF/图片输入，直接上传截图

### 6.4 ChatGPT

- 优势：Custom GPT 生态
- 建议创建 Custom GPT：上传 SKILL.md 作为知识库
- 一次性创建永久可用

### 6.5 飞书多维表格 AI 字段

- 优势：直接在表格中生成
- 在 AI 字段配置中填入简易版 Prompt
- 配置「输入变量」= 当前行的 Bug 描述
- 「输出」= 标准 Markdown，自动填入下一列

---

## 7. 配合 bug-report-writer 完整工作流

```
Cursor/Trae (输入 Bug 描述)
       ↓
   完整版 Prompt 生成标准 Markdown
       ↓
   python scripts/bug_quality_checker.py --input bug.md (6维度评分)
       ↓
   评分 ≥ 60 分？
       ↓ Yes
   python scripts/convert_format.py --input bug.md --format feishu
       ↓
   python scripts/bug_to_json.py --input bug.md (JSON协议)
       ↓
   python scripts/report_to_html.py --input bug.md --all (3视图HTML)
       ↓
   粘贴到飞书/禅道/TAPD
```

---

**版本**：v1.1.0
**最后更新**：2026-06-29
**配套脚本**：bug-report-writer v1.1.0
