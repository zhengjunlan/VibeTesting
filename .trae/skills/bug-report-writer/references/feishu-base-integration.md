# 飞书 Base 集成使用指南（v1.1.1）

> **目标**：把 bug-report-writer 生成的 Bug 一键写入飞书多维表格（Base），告别手动复制粘贴。

---

## 一、核心能力

| 能力 | v1.1.0 | v1.1.1 |
|------|--------|--------|
| 飞书支持 | 写死 9 字段 MD 导出 | **自定义字段映射 + 一键 Base 入库** |
| 字段匹配 | 手工对齐 | **自动扫描 + 模糊匹配 + 智能合并** |
| 导入方式 | 手动复制粘贴 | **lark-cli 一键批量写入** |
| 单条耗时 | 3-5 分钟 | **10-15 秒** ⚡ |

---

## 二、第一次使用（3 步走）

### Step 1：扫描你的飞书 Base 表

```bash
python scripts/feishu_field_mapper.py scan \
  --base-url "https://pvmhda3j1c.feishu.cn/base/D6Eub7nmBaIHIls6tVbcUTdSnfd" \
  --table-id "tblvocsgAtfKkqcA" \
  --output config/feishu_field_mapping.user.json
```

输出：`config/feishu_field_mapping.user.json`（你的 Base 字段映射配置）

### Step 2：确认 / 调整字段映射（可选）

打开生成的 JSON 文件，确认 `field_mapping` 符合预期：
```json
{
  "field_mapping": {
    "提出人": "reporter",
    "问题标题": "title",
    "详细描述": "description",
    ...
  },
  "select_options_mapping": {
    "类型": {"bug": "bug", "需求": "需求"},
    "状态": {"open": "待解决", "fixed": "待验收"}
  }
}
```

### Step 3：一键导入 Bug

```bash
# 批量
python scripts/feishu_base_importer.py \
  --bug-list bugs.json \
  --base-url "https://pvmhda3j1c.feishu.cn/base/D6Eub7nmBaIHIls6tVbcUTdSnfd" \
  --table-id "tblvocsgAtfKkqcA" \
  --mapping config/feishu_field_mapping.user.json

# 单条
python scripts/feishu_base_importer.py \
  --bug bug.json \
  --base-url "..." \
  --table-id "..." \
  --mapping config/feishu_field_mapping.user.json
```

---

## 三、CLI 参数详解

### feishu_field_mapper.py scan

| 参数 | 必填 | 说明 |
|------|------|------|
| `--base-url` | ✅ | 飞书 Base 完整 URL |
| `--base-token` | ❌ | Base token（默认从 URL 自动提取）|
| `--table-id` | ✅ | 目标表 ID |
| `--output` | ❌ | 映射配置输出路径（默认 `config/feishu_field_mapping.user.json`）|
| `--fuzzy-threshold` | ❌ | 模糊匹配阈值 0-1（默认 0.8）|

### feishu_base_importer.py

| 参数 | 必填 | 说明 |
|------|------|------|
| `--bug` | ✅* | 单条 bug JSON 文件（与 `--bug-list` 二选一）|
| `--bug-list` | ✅* | 批量 bug JSON 文件 |
| `--base-url` | ✅ | 飞书 Base URL |
| `--base-token` | ❌ | Base token（默认从 URL 提取）|
| `--table-id` | ✅ | 目标表 ID |
| `--mapping` | ❌ | 字段映射配置（默认 `config/feishu_field_mapping.user.json`）|
| `--batch-size` | ❌ | 每批处理条数（默认 50，飞书 API 限流友好）|
| `--dry-run` | ❌ | 干跑模式：不真实写入，只生成 record |
| `--output` | ❌ | 导入回执输出文件（JSON 格式）|

---

## 四、字段映射规则

### 4.1 默认映射

`config/feishu_field_mapping.default.json` 预置了 53 个**飞书表候选字段名** → **13 个标准 bug 字段**的映射：

```json
{
  "default_mapping": {
    "问题描述": "title",
    "标题": "title",
    "bug标题": "title",
    "开发备注": "description",
    "描述": "description",
    "类型": "bug_type",
    "缺陷类型": "bug_type",
    "状态": "status",
    "优先级": "priority",
    "严重程度": "priority",
    "负责人": "assignee",
    "处理人": "assignee",
    "复现步骤": "steps",
    "重现步骤": "steps",
    "期望结果": "expected",
    "实际结果": "actual",
    "环境": "environment",
    "提单人": "reporter",
    "提单时间": "created_at"
  }
}
```

### 4.2 模糊匹配

`scan` 命令会对每个用户表字段遍历默认映射：
- **完全匹配** → 直接映射
- **模糊相似度 ≥ 0.8** → 自动匹配 + 提示确认
- **匹配不到** → 留空 + 输出警告

### 4.3 智能合并未映射字段

当用户 Base 表没有"期望结果/实际结果/环境/AI分析"独立字段时，自动合并到"详细描述"字段：

```
【问题】xxx
【详细描述】xxx
【复现步骤】xxx

【期望结果】xxx
【实际结果】xxx
【环境信息】xxx
【AI 分析】xxx
【提单时间】xxx
```

合并触发顺序：
1. 找"详细描述"字段
2. 找"问题描述"字段
3. 找"描述"字段
4. 找"详情"字段
5. 都没有 → 丢弃 + 警告

---

## 五、select 字段选项映射

飞书 Base 的 select 字段必须使用**预置选项值**，所以需要做"标准值 → 飞书选项"映射：

```json
{
  "select_options_mapping": {
    "类型": {
      "bug": "bug",
      "AI模型": "bug",
      "性能": "bug",
      "需求": "需求"
    },
    "状态": {
      "open": "待解决",
      "fixed": "待验收",
      "verified": "验收通过",
      "rejected": "验证不通过"
    },
    "优先级": {
      "P0": "P0",
      "P1": "P1",
      "P2": "P2",
      "P3": "P3"
    }
  }
}
```

> **注意**：select 字段值在 API 调用时必须是**单元素数组**形式：`["P0"]` 而不是 `"P0"`。脚本已自动处理。

---

## 六、输出示例

### 6.1 成功导入后的飞书 Base

| 问题标题 | 优先级 | 类型 | 状态 | 负责人 | 详细描述 |
|----------|--------|------|------|--------|----------|
| AI图片生成服务返回空白图 | P0 | bug | 待解决 | AI平台组-张三 | 调用gpt-image-1接口...【期望结果】...【实际结果】...【AI 分析】... |
| 登录页接口 P95 响应时间超 SLA | P1 | bug | 待解决 | 后端组-李四 | 登录接口 /api/v1/login 在 17:00-19:00 高峰期 P95 达到 1280ms... |
| Safari 浏览器下商品卡片图片错位 | P2 | bug | 待解决 | 前端组-王五 | 在 Safari 15+ 浏览器下,首页商品列表的卡片图片位置偏移约 20px... |

### 6.2 导入回执（`--output` 输出文件）

```json
{
  "timestamp": "2026-06-29T17:50:00+08:00",
  "base_url": "https://xxx.feishu.cn/base/AbCd",
  "table_id": "tblvocsgAtfKkqcA",
  "total": 5,
  "success": 5,
  "fail": 0,
  "dry_run": false,
  "results": [
    {"record_id": "recvnVqYLKmG9s", "status": "success"},
    {"record_id": "recvnVqYLKFOol", "status": "success"},
    ...
  ],
  "warnings": []
}
```

---

## 七、真实导入演示（端到端验证）

### 测试场景

把 5 条 mock bug 真实导入用户的飞书 Base（https://pvmhda3j1c.feishu.cn/base/D6Eub7nmBaIHIls6tVbcUTdSnfd）

### 流程

```bash
# 1. 扫描表结构
python scripts/feishu_field_mapper.py scan \
  --base-url "https://pvmhda3j1c.feishu.cn/base/D6Eub7nmBaIHIls6tVbcUTdSnfd" \
  --table-id "tblvocsgAtfKkqcA" \
  --output config/feishu_field_mapping.user.json

# 2. 真实导入
python scripts/feishu_base_importer.py \
  --bug-list examples/mock_bugs_for_feishu.json \
  --base-url "https://pvmhda3j1c.feishu.cn/base/D6Eub7nmBaIHIls6tVbcUTdSnfd" \
  --table-id "tblvocsgAtfKkqcA" \
  --mapping config/feishu_field_mapping.user.json \
  --output examples/import_receipt.json
```

### 结果

```
📦 加载 5 条 bug 数据
📋 映射配置加载完成 (字段数: 9)
🔄 转换 bug → 飞书 record ...
   ✅ 成功转换 5 / 5 条
🔐 检查 lark-cli 飞书授权...
   已授权 (user: 许卉)
📦 处理第 1 批 (5 条)...
   ✅ 成功 5 / 5 条 (record_ids: ['recvnVqYLKmG9s', ...])

📊 导入结果
   总条数:    5
   成功:      5 ✅
   失败:      0 ❌
🎉 导入成功!
```

---

## 八、常见问题

### Q1：导入时报 `not_found` 错误

**原因**：字段名拼写错误或表中确实无此字段。
**解决**：
1. 运行 `scan` 命令重新生成映射
2. 检查 `field_mapping` 中 key 是否与飞书表字段名完全一致（含空格/标点）
3. 用 `--dry-run` 先 dry-run 看下要写入的 record 字段

### Q2：select 字段写入失败

**原因**：option 名称不在飞书表预置选项中。
**解决**：
1. 打开飞书 Base 表，点击字段 → 添加选项
2. 或在 `select_options_mapping` 中添加标准值 → 选项名的映射

### Q3：未授权场景

如果 `lark-cli auth status` 返回未就绪：
- importer 自动降级生成 `feishu_base_import_guide_{时间戳}.md`
- 含可复制表格 + 原始 JSON 数据
- 用户可手动复制到飞书 Base

### Q4：批量导入超过 50 条

`--batch-size` 默认 50，飞书 API 限流友好。如需调整：
```bash
--batch-size 100  # 单批 100 条（可能触发限流）
```

### Q5：字段映射匹配度低

调整模糊匹配阈值：
```bash
python scripts/feishu_field_mapper.py scan \
  --fuzzy-threshold 0.6 \
  --base-url "..." --table-id "..."
```

---

## 九、文件清单（v1.1.1）

| 文件 | 行数 | 说明 |
|------|------|------|
| `scripts/feishu_field_mapper.py` | ~350 | 字段映射引擎（默认+模糊+智能合并）|
| `scripts/feishu_base_importer.py` | ~430 | 飞书 Base 一键导入主入口 |
| `config/feishu_field_mapping.default.json` | ~60 | 默认字段映射模板（53 个候选）|
| `config/feishu_field_mapping.user.template.json` | ~30 | 用户自定义映射模板 |
| `examples/mock_bugs_for_feishu.json` | ~120 | 演示数据（5 条覆盖各类型）|
| `SKILL.md` | +50 | 新增第 17 章"飞书 Base 深度集成"|
| `references/feishu-base-integration.md` | ~280 | 本文档 |

---

**v1.1.1 升级时间**：2026-06-29
**测试环境**：许卉的飞书 Base（base_token: D6Eub7nmBaIHIls6tVbcUTdSnfd, table_id: tblvocsgAtfKkqcA）
**端到端验证**：✅ 5/5 条 mock bug 真实导入成功
