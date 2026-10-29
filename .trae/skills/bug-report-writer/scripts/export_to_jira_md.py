#!/usr/bin/env python3
"""
Bug报告格式转换脚本 - Jira Wiki Markup导出

将标准Markdown格式的Bug报告转换为Jira兼容的Wiki Markup格式。

用法：
    python export_to_jira_md.py --input bug_report.md --output jira_bug.md
    python export_to_jira_md.py --input bug_report.md  # 输出到同目录
"""

import argparse
import re
import sys
import os


# Jira优先级映射
PRIORITY_MAP = {
    "P0": "Highest",
    "P0-紧急": "Highest",
    "P1": "High",
    "P1-高": "High",
    "P2": "Medium",
    "P2-中": "Medium",
    "P3": "Low",
    "P3-低": "Lowest",
}


def parse_bug_report(content: str) -> dict:
    """解析标准Markdown格式的Bug报告，提取各字段"""
    bug = {
        "title": "",
        "severity": "",
        "priority": "",
        "type": "",
        "module": "",
        "version": "",
        "os": "",
        "device": "",
        "app_version": "",
        "network": "",
        "steps": [],
        "expected": "",
        "actual": "",
        "error_log": "",
        "impact": "",
        "notes": "",
    }

    # 提取标题
    title_match = re.search(r'\*\*Bug标题\*\*\s*\|\s*(.+?)\s*\|', content)
    if title_match:
        bug["title"] = title_match.group(1).strip()

    # 提取基本信息表格字段
    field_patterns = {
        "severity": r'\*\*严重度\*\*\s*\|\s*(.+?)\s*\|',
        "priority": r'\*\*优先级\*\*\s*\|\s*(.+?)\s*\|',
        "type": r'\*\*Bug类型\*\*\s*\|\s*(.+?)\s*\|',
        "module": r'\*\*所属模块\*\*\s*\|\s*(.+?)\s*\|',
        "version": r'\*\*发现版本\*\*\s*\|\s*(.+?)\s*\|',
        "os": r'\*\*操作系统\*\*\s*\|\s*(.+?)\s*\|',
        "device": r'\*\*设备型号\*\*\s*\|\s*(.+?)\s*\|',
        "app_version": r'\*\*APP版本\*\*\s*\|\s*(.+?)\s*\|',
        "network": r'\*\*网络环境\*\*\s*\|\s*(.+?)\s*\|',
    }

    for field, pattern in field_patterns.items():
        match = re.search(pattern, content)
        if match:
            bug[field] = match.group(1).strip()

    # 提取复现步骤
    steps_section = re.search(r'### 复现步骤\s*\n((?:\d+\..+\n?)+)', content)
    if steps_section:
        steps_text = steps_section.group(1)
        bug["steps"] = [
            re.sub(r'^\d+\.\s*', '', line.strip())
            for line in steps_text.strip().split('\n')
            if line.strip()
        ]

    # 提取预期结果
    expected_match = re.search(r'### 预期结果\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if expected_match:
        bug["expected"] = expected_match.group(1).strip()

    # 提取实际结果
    actual_match = re.search(r'### 实际结果\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if actual_match:
        bug["actual"] = actual_match.group(1).strip()

    # 提取错误信息
    error_match = re.search(r'### 错误信息\s*\n```\s*\n(.*?)\n```', content, re.DOTALL)
    if error_match:
        bug["error_log"] = error_match.group(1).strip()

    # 提取影响范围
    impact_match = re.search(r'### 影响范围\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if impact_match:
        bug["impact"] = impact_match.group(1).strip()

    return bug


def to_jira_format(bug: dict) -> str:
    """将Bug数据转换为Jira Wiki Markup格式"""
    lines = []

    # Summary
    lines.append(f"*Summary*: {bug['title'] or 'Bug报告'}")
    lines.append("")

    # Issue Type & Priority
    lines.append("*Issue Type*: Bug")

    jira_priority = PRIORITY_MAP.get(bug["priority"], "Medium")
    lines.append(f"*Priority*: {jira_priority}")
    lines.append(f"*Severity*: {bug['severity'] or 'S3'}")
    lines.append("")

    # Description
    lines.append("*Description*:")
    lines.append("")

    # 环境信息
    lines.append("h3. 环境信息")
    lines.append("||字段||值||")
    if bug["module"]:
        lines.append(f"|所属模块|{bug['module']}|")
    if bug["version"]:
        lines.append(f"|发现版本|{bug['version']}|")
    if bug["os"]:
        lines.append(f"|操作系统|{bug['os']}|")
    if bug["device"]:
        lines.append(f"|设备型号|{bug['device']}|")
    if bug["app_version"]:
        lines.append(f"|APP版本|{bug['app_version']}|")
    if bug["network"]:
        lines.append(f"|网络环境|{bug['network']}|")
    lines.append("")

    # 复现步骤
    if bug["steps"]:
        lines.append("h3. 复现步骤")
        for i, step in enumerate(bug["steps"], 1):
            lines.append(f"# {step}")
        lines.append("")

    # 预期结果
    if bug["expected"]:
        lines.append("h3. 预期结果")
        lines.append(bug["expected"])
        lines.append("")

    # 实际结果
    if bug["actual"]:
        lines.append("h3. 实际结果")
        lines.append(bug["actual"])
        lines.append("")

    # 错误信息
    if bug["error_log"]:
        lines.append("h3. 错误信息")
        lines.append("{code}")
        lines.append(bug["error_log"])
        lines.append("{code}")
        lines.append("")

    # 影响范围
    if bug["impact"]:
        lines.append("h3. 影响范围")
        lines.append(bug["impact"])
        lines.append("")

    return '\n'.join(lines)


def convert_file(input_path: str, output_path: str = None) -> str:
    """转换Bug报告文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    bug = parse_bug_report(content)
    jira_md = to_jira_format(bug)

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}-Jira版.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(jira_md)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Bug报告转Jira格式')
    parser.add_argument('--input', '-i', required=True, help='输入Bug报告Markdown文件')
    parser.add_argument('--output', '-o', help='输出Jira格式文件（默认同名-Jira版.md）')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 文件不存在：{args.input}")
        sys.exit(1)

    output = convert_file(args.input, args.output)
    print(f"✅ Jira格式Bug报告已生成：{output}")
    print(f"📋 使用方式：复制内容 → Jira → 创建Issue → 粘贴到Description")


if __name__ == '__main__':
    main()
