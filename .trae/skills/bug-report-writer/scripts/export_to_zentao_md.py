#!/usr/bin/env python3
"""
禅道Bug报告格式导出脚本

将标准Markdown格式的Bug报告转换为禅道Bug录入格式。
输出可直接对照禅道提Bug页面逐字段填写。

用法:
    python export_to_zentao_md.py --input bug_report.md --output zentao_bug.md
    python export_to_zentao_md.py --input bug_report.md  # 输出到控制台
"""

import argparse
import json
import re
import sys
from pathlib import Path


# 严重度映射：通用 → 禅道
SEVERITY_MAP = {
    "S1-致命": "1-致命",
    "S1": "1-致命",
    "致命": "1-致命",
    "S2-严重": "2-严重",
    "S2": "2-严重",
    "严重": "2-严重",
    "S3-一般": "3-一般",
    "S3": "3-一般",
    "一般": "3-一般",
    "S4-轻微": "4-轻微",
    "S4": "4-轻微",
    "轻微": "4-轻微",
}

# 优先级映射：通用 → 禅道
PRIORITY_MAP = {
    "P0-紧急": "1-紧急",
    "P0": "1-紧急",
    "紧急": "1-紧急",
    "P1-高": "2-高",
    "P1": "2-高",
    "高": "2-高",
    "P2-中": "3-中",
    "P2": "3-中",
    "中": "3-中",
    "P3-低": "4-低",
    "P3": "4-低",
    "低": "4-低",
}

# Bug类型映射：通用 → 禅道
TYPE_MAP = {
    "功能缺陷": "代码错误",
    "UI缺陷": "界面优化",
    "性能问题": "性能问题",
    "安全问题": "安全相关",
    "兼容性问题": "代码错误",
    "数据异常": "代码错误",
    "兼容性": "代码错误",
    "网络异常": "代码错误",
}


def parse_bug_report(content: str) -> dict:
    """从标准Markdown Bug报告中提取各字段"""
    bug = {}

    # 提取表格中的键值对
    table_pattern = r'\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|'
    tables = re.findall(table_pattern, content)
    for key, value in tables:
        key = key.strip()
        value = value.strip()
        if '标题' in key:
            bug['title'] = value
        elif '严重度' in key:
            bug['severity'] = value
        elif '优先级' in key:
            bug['priority'] = value
        elif '类型' in key:
            bug['type'] = value
        elif '模块' in key and '所属' in key:
            bug['module'] = value
        elif '版本' in key and '发现' in key:
            bug['version'] = value
        elif '版本' in key and 'APP' in key:
            bug['app_version'] = value
        elif '操作系统' in key:
            bug['os'] = value
        elif '设备' in key:
            bug['device'] = value
        elif '网络' in key:
            bug['network'] = value

    # 提取复现步骤
    steps_match = re.search(r'###?\s*复现步骤\s*\n((?:\d+\..+\n?)+)', content)
    if steps_match:
        bug['steps'] = steps_match.group(1).strip()

    # 提取预期结果
    expect_match = re.search(r'###?\s*预期结果\s*\n(.+?)(?=\n###|\n##|\Z)', content, re.DOTALL)
    if expect_match:
        bug['expected'] = expect_match.group(1).strip()

    # 提取实际结果
    actual_match = re.search(r'###?\s*实际结果\s*\n(.+?)(?=\n###|\n##|\Z)', content, re.DOTALL)
    if actual_match:
        bug['actual'] = actual_match.group(1).strip()

    # 提取错误信息
    error_match = re.search(r'###?\s*错误信息\s*\n```\n?(.*?)\n?```', content, re.DOTALL)
    if error_match:
        bug['error_log'] = error_match.group(1).strip()

    # 提取影响范围
    impact_match = re.search(r'###?\s*影响范围\s*\n(.+?)(?=\n###|\n##|\Z)', content, re.DOTALL)
    if impact_match:
        bug['impact'] = impact_match.group(1).strip()

    return bug


def map_severity(severity: str) -> str:
    """将通用严重度映射为禅道严重程度"""
    for key, value in SEVERITY_MAP.items():
        if key in severity:
            return value
    return "3-一般"  # 默认一般


def map_priority(priority: str) -> str:
    """将通用优先级映射为禅道优先级"""
    for key, value in PRIORITY_MAP.items():
        if key in priority:
            return value
    return "3-中"  # 默认中


def map_type(bug_type: str) -> str:
    """将通用Bug类型映射为禅道Bug类型"""
    for key, value in TYPE_MAP.items():
        if key in bug_type:
            return value
    return "代码错误"  # 默认代码错误


def generate_zentao_report(bug: dict, product: str = "", project: str = "") -> str:
    """生成禅道格式的Bug报告（研发导向纯文本版）"""
    severity = map_severity(bug.get('severity', ''))
    priority = map_priority(bug.get('priority', ''))
    bug_type = map_type(bug.get('type', ''))

    lines = []
    # 标题
    lines.append(f"【Bug标题】{bug.get('title', '待补充')}")
    lines.append("")

    # 属性设置
    lines.append(f"【严重程度】{severity}")
    lines.append(f"【优先级】{priority}")
    lines.append(f"【Bug类型】{bug_type}")
    lines.append(f"【所属模块】{bug.get('module', '待补充')}")
    lines.append(f"【影响版本】{bug.get('version', bug.get('app_version', '待补充'))}")
    lines.append(f"【操作系统】{bug.get('os', '待补充')}")
    if bug.get('browser'):
        lines.append(f"【运行环境】{bug['browser']}")
    lines.append("")

    # 问题描述（一句话说清：什么操作 + 什么结果 + 什么影响）
    title = bug.get('title', '')
    actual = bug.get('actual', '')
    impact = bug.get('impact', '')
    desc_parts = []
    if actual:
        desc_parts.append(actual)
    if impact:
        desc_parts.append(f"该问题{impact}")
    if desc_parts:
        lines.append("【问题描述】")
        lines.append("，".join(desc_parts))
    lines.append("")

    # 复现步骤
    lines.append("【复现步骤】")
    steps_val = bug.get('steps')
    if isinstance(steps_val, list):
        lines.append('\n'.join(steps_val) if steps_val else '1. [待补充]')
    elif steps_val:
        lines.append(steps_val)
    else:
        lines.append("1. [待补充]")
    lines.append("")

    # 预期结果
    lines.append("【预期结果】")
    lines.append(bug.get('expected', '待补充'))
    lines.append("")

    # 实际结果
    lines.append("【实际结果】")
    lines.append(bug.get('actual', '待补充'))
    lines.append("")

    # 错误信息
    if bug.get('error_log'):
        lines.append("【错误信息】")
        lines.append(bug['error_log'])
        lines.append("")

    # 影响范围
    lines.append("【影响范围】")
    if bug.get('impact'):
        lines.append(f"- 影响用户：{impact}")
    else:
        lines.append("- 影响用户：待补充")
    lines.append("- 复现概率：必现 / 偶现（请选择）")

    # 如果Bug类型被映射了，补充说明原始类型
    original_type = bug.get('type', '')
    if original_type and original_type != bug_type:
        lines.append(f"- 原始分类：{original_type}（禅道映射为「{bug_type}」）")

    lines.append("")
    lines.append("【排查方向】")
    lines.append("1. [检查请求参数/接口调用]")
    lines.append("2. [检查后端服务状态/数据完整性]")
    lines.append("3. [检查前端逻辑/状态管理]")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="将Bug报告转换为禅道格式")
    parser.add_argument("--input", required=True, help="输入的Bug报告Markdown文件路径")
    parser.add_argument("--output", help="输出的禅道格式文件路径（不指定则输出到控制台）")
    parser.add_argument("--product", default="", help="所属产品名称")
    parser.add_argument("--project", default="", help="所属项目名称")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：文件不存在 {input_path}", file=sys.stderr)
        sys.exit(1)

    content = input_path.read_text(encoding='utf-8')
    bug = parse_bug_report(content)
    zentao_report = generate_zentao_report(bug, product=args.product, project=args.project)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(zentao_report, encoding='utf-8')
        print(f"✅ 禅道格式Bug报告已生成：{output_path}")
    else:
        print(zentao_report)


if __name__ == "__main__":
    main()
