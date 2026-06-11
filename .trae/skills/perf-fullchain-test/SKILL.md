---
name: perf-fullchain-test
description: "AI-assisted full-chain performance testing workflow with 7 standardized skills. Covers requirement clarification, test planning, data construction, readiness checking, JMX script generation, report analysis, and formal report generation. Trigger when user mentions: 性能压测, 全链路压测, 性能测试, performance test, performance testing, 压测方案, 压测报告, TPS, 并发压测, JMeter, 性能瓶颈, 容量评估, perf test, load test, stress test, SLA, P95, P99."
---

# 全链路性能测试工作流（7-Skill Pipeline）

## 概述

覆盖性能测试完整生命周期的 7 个标准化 Skill，将压测前置准备（需求/计划/数据/检查/脚本）和后置分析（报告分析/报告生成）全部标准化、AI 辅助产出，压测执行本身保留人工操控 JMeter。

**核心设计原则：**
- 前 5 项聚焦压测前置筹备（P01~P05），后 2 项负责压测后数据分析（P06~P07）
- 压测执行始终由人操控 JMeter，AI 不接管实操启停
- 所有输出均达到企业交付标准，支持跨平台模板（WorkBuddy / Cursor / Claude / ChatGPT / DeepSeek）

## 触发条件

用户提及以下任意关键词时触发本 Skill：
- 性能压测、全链路压测、压测方案、压测报告
- TPS、并发压测、性能瓶颈、容量评估
- perf test、load test、stress test、performance testing
- SLA、P95、P99、响应时间优化
- 压测需求澄清、压测计划、压测数据构造
- JMeter 脚本、JMX、性能测试报告

## 7-Skill 全景图

```
P01 ──→ P02 ──→ P03 ──→ P04 ──→ P05 ──── 压测执行(人工) ────→ P06 ──→ P07
需求     计划     数据     就绪     JMX脚本                            报告     报告
澄清              构造     检查     生成                              分析     生成
```

详细说明见 `references/` 目录下各子 Skill 文档。

## Pipeline 协作规则

| 环节 | Skill | 输入 | 输出 | 详细文档 |
|------|-------|------|------|---------|
| P01 需求澄清 | perf-requirement-clarifier | 接口文档/PRD/口头需求 | 需求澄清文档、待确认清单、确认函、需求摘要 | [P01](./references/p01-requirement-clarifier.md) |
| P02 测试计划 | perf-test-planner | P01 产出 | 场景参数、压测机估算、数据量预警、预热计划 | [P02](./references/p02-test-planner.md) |
| P03 数据构造 | perf-data-builder | 表结构/接口文档 | INSERT SQL / CSV 参数化文件 | [P03](./references/p03-data-builder.md) |
| P04 就绪检查 | perf-readiness-checker | 环境/脚本/监控/数据 | 4 维度 34 项检查清单 + 问题排查 | [P04](./references/p04-readiness-checker.md) |
| P05 JMX 脚本 | perf-jmx-generator | 接口/SLA/参数化需求 | 场景模板 + JMX 文件 | [P05](./references/p05-jmx-generator.md) |
| → 压测执行(人工) | — | JMeter 操控 | 原始结果(.jtl/.csv) | — |
| P06 报告分析 | perf-report-analyzer | .jtl/.csv + 监控数据 | 瓶颈定位决策树 + 根因分析 | [P06](./references/p06-report-analyzer.md) |
| P07 报告生成 | perf-report-writer | P02+P06+原始数据 | 10 模块标准报告 + HTML 可视化 | [P07](./references/p07-report-writer.md) |

## 版本管控规范

plan_id 命名规则：`{项目}-{模块}-{接口}-{压测类型}-{日期}-{版本}`

示例：`aio-testcase-query-baseline-20260605-v1`

| 变更类型 | 版本规则 |
|----------|----------|
| 首次澄清 | v1.0 |
| 需求变更（并发/SLA/范围调整） | v1.1 → v1.2 |
| 重大变更（压测目标类型改变） | v2.0 |

## 跨平台 Prompt 模板

每个子 Skill 文档均包含跨平台通用 Prompt 模板，可直接复制到以下平台使用：

- **WorkBuddy**: `@skill:perf-xxx` 直接调用
- **Cursor**: 复制 Prompt 到 Chat 或 `.cursorrules`
- **Trae**: 复制到侧边栏 AI 助手
- **Claude/ChatGPT/DeepSeek**: 新建对话粘贴 Prompt + 输入需求

## 目录结构

```
perf-fullchain-test/
├── SKILL.md                    # 本文件 - 总纲 & 协作规则
├── references/
│   ├── p01-requirement-clarifier.md   # 需求澄清
│   ├── p02-test-planner.md            # 测试计划
│   ├── p03-data-builder.md            # 数据构造
│   ├── p04-readiness-checker.md       # 就绪检查
│   ├── p05-jmx-generator.md           # JMX 脚本生成
│   ├── p06-report-analyzer.md         # 报告分析
│   └── p07-report-writer.md           # 报告生成
└── scripts/                           # 辅助脚本（可选）