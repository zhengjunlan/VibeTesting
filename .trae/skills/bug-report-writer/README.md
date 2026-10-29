# bug-report-writer

AI Bug提单助手 — 从问题发现到标准化Bug报告，一键完成。

## 功能特性

- 🖼️ **多模态输入**：支持截图、错误日志、堆栈信息、自然语言描述
- 🔍 **智能分析**：自动识别问题类型、提取关键错误信息、推断根因
- 📋 **标准化输出**：生成结构清晰、信息完整的Bug报告
- ⚡ **严重度定级**：基于影响范围自动建议严重度和优先级
- 📤 **多平台适配**：支持Jira、飞书、禅道、GitHub Issues等格式导出

## 快速开始

### 1. 在WorkBuddy中使用

直接对AI说：

```
帮我提个Bug，这个页面有问题
[上传截图]

根据这个日志提Bug
[粘贴错误日志]

购物车修改数量后金额没更新，帮我提Bug
```

### 2. 指定输出格式

```
帮我提个Bug，用Jira格式
帮我提个Bug，导出飞书格式
```

### 3. 使用导出脚本

```bash
# 转换为飞书格式
python scripts/export_to_feishu_md.py --input bug_report.md --output feishu_bug.md

# 转换为Jira格式
python scripts/export_to_jira_md.py --input bug_report.md --output jira_bug.md

# 通用格式转换
python scripts/convert_format.py --input bug_report.md --format feishu
python scripts/convert_format.py --input bug_report.md --format jira
```

## 目录结构

```
bug-report-writer/
├── SKILL.md                          # 技能主文件
├── README.md                         # 本文件
├── references/                       # 参考文档
│   ├── bug-report-standard.md        # Bug报告编写标准
│   ├── bug-severity-guide.md         # 严重度定级详细指南
│   ├── bug-title-guide.md            # Bug标题命名规范
│   └── reproduce-steps-guide.md      # 复现步骤编写指南
├── scripts/                          # 导出脚本
│   ├── convert_format.py             # 通用格式转换
│   ├── export_to_feishu_md.py        # 飞书格式导出
│   └── export_to_jira_md.py          # Jira格式导出
└── assets/                           # 资源文件
    └── templates/                    # Bug报告模板
        ├── template-config.json      # 默认模板配置
        └── jira-template.json        # Jira模板配置
```

## Bug报告格式

### 支持的输出格式

| 格式 | 说明 | 导入方式 |
|------|------|----------|
| 标准Markdown | 默认格式，信息完整 | 直接使用 |
| 飞书格式 | 纯列表结构，适配飞书思维笔记 | 复制粘贴到飞书 |
| Jira格式 | Wiki Markup，适配Jira | 粘贴到Jira Description |
| 禅道格式 | Markdown表格 | 粘贴到禅道Bug描述 |

### 严重度定级

| 严重度 | 定义 | 修复时限 |
|--------|------|----------|
| S1-致命 | 系统崩溃、数据丢失、核心功能完全不可用 | 2小时 |
| S2-严重 | 核心功能受损、重要数据错误 | 24小时 |
| S3-一般 | 非核心功能异常、有替代方案 | 本迭代 |
| S4-轻微 | UI瑕疵、文案错误、体验不佳 | 下迭代 |

## 版本

- v1.0.0 (2026-04-23) - 初始版本
