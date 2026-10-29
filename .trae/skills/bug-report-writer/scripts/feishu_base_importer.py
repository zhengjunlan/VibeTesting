#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_base_importer.py - 飞书 Base 一键导入器 v1.1.1

核心职责:
  1. 加载 bug JSON 数据(单条 / 批量)
  2. 调用 feishu_field_mapper.convert_bug_to_record 转换
  3. 调用 lark-cli +record-batch-create 批量写入飞书 Base
  4. 自动检测授权状态(无授权时降级生成 .md 提示)
  5. 输出导入回执(成功条数 / 失败条数 / 链接)

CLI 用法:
  # 单条 bug 导入
  python feishu_base_importer.py \
    --bug bug.json \
    --base-url "https://xxx.feishu.cn/base/AbCd" \
    --table-id "tblXXX" \
    --mapping config/feishu_field_mapping.user.json

  # 批量 bug 导入
  python feishu_base_importer.py \
    --bug-list bugs.json \
    --base-url "https://xxx.feishu.cn/base/AbCd" \
    --table-id "tblXXX" \
    --mapping config/feishu_field_mapping.user.json \
    --batch-size 50

  # 干跑(不真正写入,只生成 record)
  python feishu_base_importer.py \
    --bug bug.json \
    --base-url "..." \
    --table-id "..." \
    --mapping config/feishu_field_mapping.user.json \
    --dry-run
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# feishu_field_mapper 同目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feishu_field_mapper import (  # noqa: E402
    LARK_CLI,
    SKILL_ROOT,
    load_default_mapping,
    load_user_mapping,
    merge_mappings,
    convert_bug_to_record,
    scan_base_fields,
)


# ---------------------------------------------------------------------------
# 1. 检查 lark-cli 授权状态
# ---------------------------------------------------------------------------
def check_lark_auth() -> Tuple[bool, str]:
    """检查 lark-cli 飞书授权状态,返回 (是否就绪, 状态信息)"""
    try:
        result = subprocess.run(
            [LARK_CLI, "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return False, f"lark-cli 调用失败: {result.stderr}"

        data = json.loads(result.stdout)
        user_identity = data.get("identities", {}).get("user", {})
        if user_identity.get("status") == "ready":
            return True, f"已授权 (user: {user_identity.get('userName', 'unknown')})"
        return False, f"用户身份未就绪: {user_identity.get('message', 'unknown')}"
    except Exception as e:
        return False, f"检测失败: {e}"


# ---------------------------------------------------------------------------
# 2. 加载 bug 数据
# ---------------------------------------------------------------------------
def load_bugs(args) -> List[dict]:
    """根据 CLI 参数加载单条/批量 bug 数据"""
    if args.bug:
        with open(args.bug, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [data] if isinstance(data, dict) else data
    elif args.bug_list:
        with open(args.bug_list, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError("必须指定 --bug 或 --bug-list")


# ---------------------------------------------------------------------------
# 3. 加载映射配置
# ---------------------------------------------------------------------------
def load_mapping(args) -> dict:
    """加载用户映射(优先) + 默认映射(兜底),合并返回"""
    user_mapping = load_user_mapping()
    if args.mapping:
        with open(args.mapping, "r", encoding="utf-8") as f:
            user_mapping = json.load(f)

    default_mapping = load_default_mapping()
    return merge_mappings(default_mapping, user_mapping)


# ---------------------------------------------------------------------------
# 4. 调用 lark-cli 写入 record
# ---------------------------------------------------------------------------
def import_records(
    base_token: str,
    table_id: str,
    records: List[Dict[str, str]],
    mapping: dict,
    batch_size: int = 50,
    dry_run: bool = False,
) -> Tuple[int, int, List[dict]]:
    """
    批量导入 records 到飞书 Base
    返回: (成功条数, 失败条数, 详细结果列表)
    """
    if dry_run:
        print(f"🔍 [DRY RUN] 将要导入 {len(records)} 条 record,不会真实写入")
        return len(records), 0, [{"record": r, "status": "dry-run"} for r in records]

    success, fail = 0, 0
    results = []

    # 加载 select_options_meta 获取 field_id 映射
    select_meta = mapping.get("select_options_meta", {})

    # 构造 name → field_id 的映射(优先用 field_id,缺失时降级用 name)
    # select 字段在 select_options_meta 中有 field_id
    # text 字段没有 field_id,只能传 name
    name_to_id: Dict[str, str] = {}
    for fname, fmeta in select_meta.items():
        if isinstance(fmeta, dict) and "field_id" in fmeta:
            name_to_id[fname] = fmeta["field_id"]

    # 收集所有 record 的 field name,转成 (id_or_name, type) 列表
    all_field_names = set()
    for r in records:
        all_field_names.update(r.keys())
    all_field_names_sorted = sorted(all_field_names)

    # 转换:select 字段用 field_id,text 字段用 name
    api_fields = []
    name_to_api_field = {}  # 用于填 rows 时查找
    for fname in all_field_names_sorted:
        if fname in name_to_id:
            api_field = name_to_id[fname]
        else:
            api_field = fname
        api_fields.append(api_field)
        name_to_api_field[fname] = api_field

    # select 字段名集合(这些字段的值需要包成数组)
    select_field_names = set(name_to_id.keys())

    # 分批处理(每批 50 条)
    for batch_start in range(0, len(records), batch_size):
        batch = records[batch_start:batch_start + batch_size]
        print(f"📦 处理第 {batch_start // batch_size + 1} 批 ({len(batch)} 条)...")

        # 构造 lark-cli +record-batch-create 请求体
        # fields 是 field_id 或 field_name 的列表,rows 是对应的值
        # select 字段的值必须是数组形式(单选也用单元素数组)
        rows = []
        for record in batch:
            row = []
            for fname in all_field_names_sorted:
                val = record.get(fname, "")
                if fname in select_field_names and val and not isinstance(val, list):
                    val = [val]
                row.append(val)
            rows.append(row)

        cmd = [
            LARK_CLI, "base", "+record-batch-create",
            "--base-token", base_token,
            "--table-id", table_id,
            "--json", json.dumps({"fields": api_fields, "rows": rows}, ensure_ascii=False),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                print(f"   ❌ 批次失败: {result.stderr[:200]}")
                fail += len(batch)
                results.append({
                    "batch_start": batch_start,
                    "status": "fail",
                    "error": result.stderr[:500],
                })
                continue

            data = json.loads(result.stdout)
            if not data.get("ok"):
                print(f"   ❌ API 错误: {data.get('error', {}).get('message', 'unknown')}")
                fail += len(batch)
                results.append({
                    "batch_start": batch_start,
                    "status": "api_error",
                    "error": str(data.get("error", {}))[:500],
                })
                continue

            # 解析飞书 API 返回:data.data 是 [[row1_values...], [row2_values...]]
            # 真实字段路径:data.data.record_id_list + data.data.field_id_list
            payload = data.get("data", {})
            if isinstance(payload, dict):
                record_id_list = payload.get("record_id_list", [])
            else:
                # 兜底:某些版本可能直接返回 records
                record_id_list = [r.get("record_id") for r in payload if r.get("record_id")] if payload else []

            created_count = len(record_id_list)
            success += created_count
            fail += len(batch) - created_count

            for rid in record_id_list:
                results.append({
                    "record_id": rid,
                    "status": "success",
                })

            print(f"   ✅ 成功 {created_count} / {len(batch)} 条 (record_ids: {record_id_list[:3]}{'...' if len(record_id_list) > 3 else ''})")

        except subprocess.TimeoutExpired:
            print(f"   ⏱️  批次超时")
            fail += len(batch)
            results.append({"batch_start": batch_start, "status": "timeout"})
        except Exception as e:
            print(f"   💥 批次异常: {e}")
            fail += len(batch)
            results.append({"batch_start": batch_start, "status": "exception", "error": str(e)})

    return success, fail, results


# ---------------------------------------------------------------------------
# 5. 降级处理:生成 .md 提示文件
# ---------------------------------------------------------------------------
def generate_fallback_guide(
    base_url: str,
    table_id: str,
    records: List[Dict[str, str]],
    bug_data_list: List[dict],
    reason: str,
) -> str:
    """
    当无法直接调用飞书 API 时,生成 .md 操作指南
    返回生成的 .md 文件路径
    """
    output_path = Path(SKILL_ROOT) / "examples" / f"feishu_base_import_guide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# 飞书 Base 导入操作指南 (降级模式)\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**目标 Base**: {base_url}\n\n")
        f.write(f"**目标表 ID**: {table_id}\n\n")
        f.write(f"**降级原因**: {reason}\n\n")
        f.write("---\n\n")
        f.write("## 操作步骤\n\n")
        f.write("1. 打开飞书 Base 链接\n")
        f.write("2. 切换到目标表\n")
        f.write("3. 在表格中按以下字段顺序逐条添加\n\n")
        f.write("---\n\n")
        f.write(f"## 待导入数据 ({len(records)} 条)\n\n")

        # 用 markdown 表格展示
        if records:
            headers = list(records[0].keys())
            f.write("| " + " | ".join(headers) + " |\n")
            f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
            for r in records:
                row_values = []
                for h in headers:
                    val = str(r.get(h, "")).replace("|", "\\|").replace("\n", "<br>")
                    row_values.append(val)
                f.write("| " + " | ".join(row_values) + " |\n")

        f.write("\n\n---\n\n")
        f.write("## 原始 Bug JSON 数据 (参考)\n\n")
        f.write("```json\n")
        f.write(json.dumps(bug_data_list, ensure_ascii=False, indent=2))
        f.write("\n```\n")

    return str(output_path)


# ---------------------------------------------------------------------------
# 6. CLI 主流程
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="飞书 Base 一键导入器 v1.1.1")
    parser.add_argument("--bug", help="单条 bug JSON 文件")
    parser.add_argument("--bug-list", help="批量 bug JSON 文件")
    parser.add_argument("--base-url", required=True, help="飞书 Base URL")
    parser.add_argument("--base-token", help="Base token(默认从 URL 提取)")
    parser.add_argument("--table-id", required=True, help="目标表 ID")
    parser.add_argument("--mapping", help="用户自定义映射配置(默认: config/feishu_field_mapping.user.json)")
    parser.add_argument("--batch-size", type=int, default=50, help="每批处理条数(默认 50)")
    parser.add_argument("--dry-run", action="store_true", help="干跑,只生成 record 不写入")
    parser.add_argument("--output", help="导入回执输出文件")

    args = parser.parse_args()

    # 1. 加载数据
    print("=" * 60)
    print("🚀 飞书 Base 一键导入器 v1.1.1")
    print("=" * 60)
    print()

    try:
        bugs = load_bugs(args)
    except Exception as e:
        print(f"❌ 加载 bug 数据失败: {e}")
        return 1
    print(f"📦 加载 {len(bugs)} 条 bug 数据")

    # 2. 加载映射
    try:
        mapping = load_mapping(args)
    except Exception as e:
        print(f"❌ 加载映射配置失败: {e}")
        return 1
    print(f"📋 映射配置加载完成 (字段数: {len(mapping.get('field_mapping', {}))})")
    print()

    # 3. 转换所有 bug 到 record
    print("🔄 转换 bug → 飞书 record ...")
    records = []
    all_warnings = []
    select_options_meta = mapping.get("select_options_meta")

    for idx, bug in enumerate(bugs, 1):
        try:
            record, warnings = convert_bug_to_record(bug, mapping, select_options_meta)
            records.append(record)
            if warnings:
                all_warnings.extend([f"  [{idx}] {w}" for w in warnings])
        except Exception as e:
            print(f"   ❌ 第 {idx} 条转换失败: {e}")
            all_warnings.append(f"[{idx}] 转换失败: {e}")

    print(f"   ✅ 成功转换 {len(records)} / {len(bugs)} 条")
    if all_warnings:
        print()
        print("⚠️  警告:")
        for w in all_warnings:
            print(w)
    print()

    # 4. 检查授权
    if not args.dry_run:
        print("🔐 检查 lark-cli 飞书授权...")
        auth_ok, auth_msg = check_lark_auth()
        print(f"   {auth_msg}")
        if not auth_ok:
            print()
            print("⚠️  飞书未授权,降级为生成操作指南 .md 文件")
            guide_path = generate_fallback_guide(
                args.base_url, args.table_id, records, bugs, auth_msg,
            )
            print(f"📄 操作指南已生成: {guide_path}")
            return 0
    print()

    # 5. 执行导入
    base_token = args.base_token or args.base_url.rstrip("/").split("/")[-1].split("?")[0]
    base_url_short = args.base_url[:50] + ("..." if len(args.base_url) > 50 else "")
    print(f"📍 目标 Base: {base_url_short}")
    print(f"📍 目标表: {args.table_id}")
    print(f"📦 批次大小: {args.batch_size}")
    print()

    success, fail, results = import_records(
        base_token=base_token,
        table_id=args.table_id,
        records=records,
        mapping=mapping,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    # 6. 输出回执
    print()
    print("=" * 60)
    print("📊 导入结果")
    print("=" * 60)
    print(f"   总条数:    {len(bugs)}")
    print(f"   成功:      {success} ✅")
    print(f"   失败:      {fail} ❌")
    if args.dry_run:
        print(f"   模式:      DRY RUN (未真实写入)")
    print(f"   Base URL:  {args.base_url}")
    print()

    if success > 0 and not args.dry_run:
        print(f"🎉 导入成功!请打开飞书 Base 查看 {success} 条新增记录")
        print(f"   {args.base_url}")

    if all_warnings:
        print()
        print("⚠️  本次导入警告汇总:")
        for w in all_warnings[:20]:  # 最多显示 20 条
            print(w)
        if len(all_warnings) > 20:
            print(f"   ... 还有 {len(all_warnings) - 20} 条警告")

    # 保存回执
    if args.output:
        receipt = {
            "timestamp": datetime.now().isoformat(),
            "base_url": args.base_url,
            "table_id": args.table_id,
            "total": len(bugs),
            "success": success,
            "fail": fail,
            "dry_run": args.dry_run,
            "results": results,
            "warnings": all_warnings,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(receipt, f, ensure_ascii=False, indent=2)
        print()
        print(f"💾 导入回执已保存: {args.output}")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
