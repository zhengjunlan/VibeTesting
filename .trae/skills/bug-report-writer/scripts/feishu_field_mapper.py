#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_field_mapper.py - 飞书 Base 字段映射引擎 v1.1.1

核心职责:
  1. 加载默认映射配置 (config/feishu_field_mapping.default.json)
  2. 加载/合并用户自定义映射 (config/feishu_field_mapping.user.json)
  3. 调用 lark-cli +field-list 自动扫描目标 Base 表结构
  4. 智能匹配:完全匹配 → 模糊匹配(相似度≥阈值) → 留空
  5. 生成最终的 record 字段值,适配 select 选项值

CLI 用法:
  # 扫描目标 Base 自动生成映射
  python feishu_field_mapper.py scan \
    --base-url "https://xxx.feishu.cn/base/AbCd" \
    --table-id "tblXXX" \
    --output config/feishu_field_mapping.user.json

  # 验证映射完整性
  python feishu_field_mapper.py validate \
    --base-url "https://xxx.feishu.cn/base/AbCd" \
    --table-id "tblXXX" \
    --mapping config/feishu_field_mapping.user.json

  # 转换单条 bug 数据到目标 Base 格式
  python feishu_field_mapper.py convert \
    --bug bug.json \
    --mapping config/feishu_field_mapping.user.json \
    --output record.json
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_ROOT / "config"
DEFAULT_MAPPING_FILE = CONFIG_DIR / "feishu_field_mapping.default.json"
USER_MAPPING_FILE = CONFIG_DIR / "feishu_field_mapping.user.json"

LARK_CLI = "/Users/jasmine/.workbuddy/binaries/node/cli-connector-packages/bin/lark-cli"

# 标准 bug 字段集合
STANDARD_BUG_FIELDS = {
    "title", "description", "steps", "expected", "actual",
    "environment", "bug_type", "status", "priority",
    "assignee", "reporter", "created_at", "attachments",
    "ai_analysis",
}


# ---------------------------------------------------------------------------
# 1. 加载映射配置
# ---------------------------------------------------------------------------
def load_default_mapping() -> dict:
    """加载默认映射配置(default_mapping 是字段名候选扩展,供 auto_generate 用)"""
    if not DEFAULT_MAPPING_FILE.exists():
        return {"default_mapping": {}, "select_options_mapping": {}}
    with open(DEFAULT_MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_user_mapping() -> dict:
    """加载用户自定义映射(可选)"""
    if not USER_MAPPING_FILE.exists():
        return {}
    with open(USER_MAPPING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_mappings(default: dict, user: dict) -> dict:
    """合并默认映射 + 用户映射,用户优先

    关键设计:
    - 默认配置的 default_mapping: 飞书表候选字段名 → 标准字段名(用于 auto_generate 匹配)
    - 用户配置(从 scan 来)的 field_mapping: 实际选中的飞书表字段名 → 标准字段名
    - 转换时(field_mapping)只用用户的实际映射,默认的"候选扩展"不参与
    """
    merged: dict = {
        "field_mapping": {},
        "select_options_mapping": {},
        "select_options_meta": {},
        "match_strategy": default.get("match_strategy", "fuzzy"),
        "fuzzy_threshold": default.get("fuzzy_threshold", 0.8),
    }

    # 1. select_options_meta(目标表字段元数据)直接覆盖
    if "select_options_meta" in user:
        merged["select_options_meta"] = user["select_options_meta"]

    # 2. select_options_mapping 合并(过滤自映射和 _comment)
    default_select = default.get("select_options_mapping", {})
    for field_name, options in default_select.items():
        if field_name.startswith("_") or not isinstance(options, dict):
            continue
        merged["select_options_mapping"].setdefault(field_name, {}).update(options)
    if "select_options_mapping" in user and isinstance(user["select_options_mapping"], dict):
        for field_name, options in user["select_options_mapping"].items():
            if field_name.startswith("_") or not isinstance(options, dict):
                continue
            merged["select_options_mapping"].setdefault(field_name, {}).update(options)

    # 3. field_mapping 优先用用户的(scan 出来的),不叠加默认的
    if "field_mapping" in user and isinstance(user["field_mapping"], dict):
        # 过滤:用户配置里 value 是字符串,且 value 不是 key(即排除自映射和 value=key 的无效项)
        clean = {
            k: v for k, v in user["field_mapping"].items()
            if isinstance(v, str) and k != v
        }
        merged["field_mapping"] = clean
    elif "default_mapping" in user and isinstance(user["default_mapping"], dict):
        clean = {
            k: v for k, v in user["default_mapping"].items()
            if isinstance(v, str) and k != v
        }
        merged["field_mapping"] = clean

    # 4. base_meta
    if "base_meta" in user:
        merged["base_meta"] = user["base_meta"]

    return merged


# ---------------------------------------------------------------------------
# 2. 扫描飞书 Base 表结构
# ---------------------------------------------------------------------------
def scan_base_fields(base_token: str, table_id: str) -> List[dict]:
    """调用 lark-cli 拉取目标表的所有字段定义"""
    cmd = [
        LARK_CLI, "base", "+field-list",
        "--base-token", base_token,
        "--table-id", table_id,
        "--format", "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"lark-cli 调用失败: {result.stderr}")

    data = json.loads(result.stdout)
    if not data.get("ok"):
        raise RuntimeError(f"lark-cli 返回错误: {data.get('error')}")

    return data["data"]["fields"]


# ---------------------------------------------------------------------------
# 3. 相似度计算 (简化版 Levenshtein 距离)
# ---------------------------------------------------------------------------
def calc_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的相似度,返回 0-1 之间的浮点数"""
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    if s1 in s2 or s2 in s1:
        return 0.9

    # Levenshtein 距离
    len1, len2 = len(s1), len(s2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)

    distance = dp[len1][len2]
    return 1 - distance / max(len1, len2)


# ---------------------------------------------------------------------------
# 4. 自动生成字段映射
# ---------------------------------------------------------------------------
def auto_generate_mapping(fields: List[dict], threshold: float = 0.8) -> Tuple[dict, List[str]]:
    """
    根据目标表字段自动生成映射
    返回: (mapping_dict, warnings)
    """
    default = load_default_mapping()
    default_map = default.get("default_mapping", {})
    warnings = []

    # 反向索引:标准字段 → 候选用户字段
    std_to_user: Dict[str, str] = {}
    unmatched_std: List[str] = []

    for std_field in STANDARD_BUG_FIELDS:
        matched = None

        # 第一轮:精确匹配(遍历所有用户字段)
        for user_field in fields:
            if user_field["name"] in default_map:
                if default_map[user_field["name"]] == std_field:
                    matched = user_field["name"]
                    break

        # 第二轮:模糊匹配
        if not matched:
            best_score = 0.0
            best_field = None
            for user_field in fields:
                if user_field["name"] in std_to_user.values():
                    continue  # 已被占用
                score = calc_similarity(user_field["name"], std_field)
                if score > best_score:
                    best_score = score
                    best_field = user_field["name"]
            if best_score >= threshold:
                matched = best_field
                warnings.append(
                    f"模糊匹配: '{std_field}' ↔ '{best_field}' (相似度 {best_score:.2f})"
                )

        if matched:
            std_to_user[std_field] = matched
        else:
            unmatched_std.append(std_field)
            warnings.append(f"未匹配: 标准字段 '{std_field}' 在目标表无对应字段")

    if unmatched_std:
        warnings.append(
            f"⚠️  {len(unmatched_std)} 个标准字段未映射,导入时将丢弃: {', '.join(unmatched_std)}"
        )

    # 组装 mapping(用户字段名 → 标准字段名)
    user_to_std = {v: k for k, v in std_to_user.items()}

    # select 选项映射
    select_map = {}
    for field in fields:
        if field["type"] == "select" and field.get("options"):
            field_options = {opt["name"] for opt in field["options"]}
            select_map[field["name"]] = {
                "available_options": sorted(field_options),
                "field_id": field["id"],
            }

    return {
        "field_mapping": user_to_std,
        "select_options_meta": select_map,
        "warnings": warnings,
    }, warnings


# ---------------------------------------------------------------------------
# 5. 转换单条 bug → 飞书 record
# ---------------------------------------------------------------------------
def convert_bug_to_record(
    bug: dict,
    mapping: dict,
    select_options_meta: Optional[dict] = None,
) -> Tuple[dict, List[str]]:
    """
    把标准 bug dict 转换为飞书 record fields

    返回: (record_dict, warnings)
      record_dict = { "field_name": value, ... } (用户表字段名)

    智能合并规则:
      - 标准字段在用户表中有精确映射 → 直接写入
      - 用户表的"详细描述"类字段没有精确匹配 description →
        自动把 description/expected/actual/environment/ai_analysis 拼成结构化文本
    """
    field_mapping = mapping.get("field_mapping", {})
    select_map = mapping.get("select_options_mapping", {})
    warnings = []

    # 反向:标准字段名 → 用户表字段名
    std_to_user = {v: k for k, v in field_mapping.items()}

    # 1) 先收集所有标准字段的实际值
    std_values: Dict[str, str] = {}
    for std_field in STANDARD_BUG_FIELDS:
        if std_field == "steps":
            steps = bug.get("steps", bug.get("reproduce_steps", []))
            std_values[std_field] = "\n".join(f"- {s}" if not s.startswith("-") else s for s in steps) if isinstance(steps, list) else str(steps)
        elif std_field == "created_at":
            std_values[std_field] = bug.get("created_at") or bug.get("created_time") or ""
        elif std_field == "attachments":
            atts = bug.get("attachments", bug.get("screenshots", []))
            if isinstance(atts, list):
                std_values[std_field] = "\n".join(atts) if atts else ""
            else:
                std_values[std_field] = str(atts) if atts else ""
        else:
            std_values[std_field] = str(bug.get(std_field, "") or "")

    # 2) 直接写入有精确映射的字段
    record = {}
    mapped_std = set()
    for user_field, std_field in field_mapping.items():
        if std_field not in std_values:
            continue
        mapped_std.add(std_field)
        value = std_values[std_field]

        # select 字段选项值映射
        if select_options_meta and user_field in select_options_meta:
            available = set(select_options_meta[user_field].get("available_options", []))
            user_field_select_map = select_map.get(user_field, {})
            mapped_value = user_field_select_map.get(value, value)
            if mapped_value not in available:
                warnings.append(
                    f"⚠️  字段 '{user_field}' 值 '{value}' 在目标表选项中不存在 (可选: {sorted(available)})"
                )
            value = mapped_value
        elif user_field in select_map and value:
            user_field_select_map = select_map[user_field]
            value = user_field_select_map.get(value, value)

        if value or std_field in ("title", "description", "steps"):
            record[user_field] = value

    # 3) 智能合并:把未映射的标准字段塞到"详细描述"类字段里
    extra_sections = []
    for std_field in ["expected", "actual", "environment", "ai_analysis", "created_at"]:
        if std_field in mapped_std or not std_values.get(std_field):
            continue
        title_map = {
            "expected": "期望结果",
            "actual": "实际结果",
            "environment": "环境信息",
            "ai_analysis": "AI 分析",
            "created_at": "提单时间",
        }
        extra_sections.append(f"【{title_map[std_field]}】\n{std_values[std_field]}")

    if extra_sections:
        # 找"详细描述"字段(优先)或"问题描述"字段
        merge_target = None
        for candidate in ["详细描述", "问题描述", "描述", "详情", "description"]:
            if candidate in record:
                merge_target = candidate
                break
        if merge_target:
            record[merge_target] = record[merge_target] + "\n\n" + "\n\n".join(extra_sections)
        else:
            # 没有描述类字段,新建一个 fallback 字段
            warnings.append(
                f"⚠️  {len(extra_sections)} 个标准字段(期望/实际/环境/AI分析/提单时间)无对应字段,且表中无详细描述类字段可合并,已丢弃"
            )

    # 4) 汇总未映射的标准字段警告
    unmapped_std = [s for s in ["actual", "expected", "environment", "ai_analysis", "created_at"] if s not in mapped_std and s in std_values and std_values[s]]
    still_unmapped = [s for s in std_values if s not in mapped_std and s not in ("expected", "actual", "environment", "ai_analysis", "created_at") and std_values[s]]
    if still_unmapped:
        warnings.append(
            f"⚠️  {len(still_unmapped)} 个标准字段在目标表无对应字段,已丢弃: {', '.join(still_unmapped)}"
        )

    return record, warnings


# ---------------------------------------------------------------------------
# 6. 扫描命令 (CLI)
# ---------------------------------------------------------------------------
def cmd_scan(args):
    """扫描 Base 表自动生成映射"""
    print(f"🔍 扫描 Base: {args.base_url}")
    print(f"📋 目标表: {args.table_id}")
    print()

    # 提取 base_token
    base_token = args.base_token or args.base_url.rstrip("/").split("/")[-1].split("?")[0]

    fields = scan_base_fields(base_token, args.table_id)
    print(f"✅ 扫描到 {len(fields)} 个字段:")
    for f in fields:
        opts = f" (选项: {[o['name'] for o in f.get('options', [])]})" if f["type"] == "select" else ""
        print(f"   - {f['name']:>10s}  {f['type']:>8s}  {f['id']}{opts}")
    print()

    mapping, warnings = auto_generate_mapping(fields, threshold=0.8)

    print("📌 自动生成的标准字段映射:")
    for user_field, std_field in mapping["field_mapping"].items():
        print(f"   {user_field:>10s}  →  {std_field}")
    print()

    if warnings:
        print("⚠️  警告:")
        for w in warnings:
            print(f"   {w}")
        print()

    # 组装输出配置
    output_config = {
        "version": "1.1.1",
        "schema_version": "1.0",
        "base_meta": {
            "base_url": args.base_url,
            "base_token": base_token,
            "table_id": args.table_id,
            "scanned_at": "",
        },
        "field_mapping": mapping["field_mapping"],
        "select_options_meta": mapping["select_options_meta"],
        "select_options_mapping": load_default_mapping().get("select_options_mapping", {}),
        "match_strategy": "fuzzy",
        "fuzzy_threshold": 0.8,
    }

    output_path = Path(args.output) if args.output else USER_MAPPING_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_config, f, ensure_ascii=False, indent=2)

    print(f"💾 映射配置已保存到: {output_path}")
    print(f"   后续用此配置可直接导入: feishu_base_importer.py --mapping {output_path}")


# ---------------------------------------------------------------------------
# 7. 转换命令 (CLI)
# ---------------------------------------------------------------------------
def cmd_convert(args):
    """转换单条 bug 数据到飞书 record 格式"""
    with open(args.bug, "r", encoding="utf-8") as f:
        bug = json.load(f)

    with open(args.mapping, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    record, warnings = convert_bug_to_record(bug, mapping)

    output_path = Path(args.output) if args.output else "record.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"✅ Record 已生成: {output_path}")
    print()
    print("📋 字段值预览:")
    for k, v in record.items():
        preview = v[:80] + "..." if len(v) > 80 else v
        print(f"   {k:>10s}  =  {preview}")
    print()
    if warnings:
        print("⚠️  警告:")
        for w in warnings:
            print(f"   {w}")


# ---------------------------------------------------------------------------
# 8. 验证命令 (CLI)
# ---------------------------------------------------------------------------
def cmd_validate(args):
    """验证映射配置完整性"""
    with open(args.mapping, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    base_token = args.base_token or mapping.get("base_meta", {}).get("base_token")
    table_id = args.table_id or mapping.get("base_meta", {}).get("table_id")

    if not base_token or not table_id:
        print("❌ 缺少 base_token 或 table_id,可通过 --base-token --table-id 或 --mapping 中读取")
        return 1

    print(f"🔍 验证映射配置: {args.mapping}")
    print(f"📋 目标表: {table_id}")
    print()

    fields = scan_base_fields(base_token, table_id)
    user_field_names = {f["name"] for f in fields}
    mapped_user_fields = set(mapping.get("field_mapping", {}).keys())

    # 检查映射中的字段是否在目标表存在
    missing_in_table = mapped_user_fields - user_field_names
    if missing_in_table:
        print(f"❌ 映射中 {len(missing_in_table)} 个字段在目标表不存在:")
        for f in missing_in_table:
            print(f"   - {f}")
    else:
        print(f"✅ 映射中所有字段在目标表都存在")

    # 检查未映射的目标表字段
    unmapped = user_field_names - mapped_user_fields
    if unmapped:
        print(f"💡 目标表 {len(unmapped)} 个字段未在映射中(可选,不影响导入):")
        for f in unmapped:
            print(f"   - {f}")

    # 检查 select 选项
    select_meta = mapping.get("select_options_meta", {})
    for field_name, meta in select_meta.items():
        available = set(meta.get("available_options", []))
        select_map = mapping.get("select_options_mapping", {}).get(field_name, {})
        unmapped_values = []
        for std_val, mapped_val in select_map.items():
            if mapped_val not in available:
                unmapped_values.append(f"{std_val} → {mapped_val}")
        if unmapped_values:
            print(f"⚠️  字段 '{field_name}' 选项映射缺失:")
            for v in unmapped_values:
                print(f"   - {v}")

    print()
    print("✅ 验证完成")
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="飞书 Base 字段映射引擎 v1.1.1")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # scan
    p_scan = subparsers.add_parser("scan", help="扫描 Base 自动生成映射")
    p_scan.add_argument("--base-url", required=True, help="Base URL")
    p_scan.add_argument("--base-token", help="Base token(可从 URL 末尾自动提取)")
    p_scan.add_argument("--table-id", required=True, help="目标表 ID")
    p_scan.add_argument("--output", help="输出映射文件路径(默认: config/feishu_field_mapping.user.json)")
    p_scan.set_defaults(func=cmd_scan)

    # convert
    p_convert = subparsers.add_parser("convert", help="转换单条 bug 到飞书 record")
    p_convert.add_argument("--bug", required=True, help="标准 bug JSON 文件")
    p_convert.add_argument("--mapping", required=True, help="映射配置文件")
    p_convert.add_argument("--output", help="输出 record 文件")
    p_convert.set_defaults(func=cmd_convert)

    # validate
    p_validate = subparsers.add_parser("validate", help="验证映射完整性")
    p_validate.add_argument("--mapping", required=True, help="映射配置文件")
    p_validate.add_argument("--base-url", help="Base URL")
    p_validate.add_argument("--base-token", help="Base token")
    p_validate.add_argument("--table-id", help="目标表 ID")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
