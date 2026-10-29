#!/usr/bin/env python3
"""
Bug报告格式转换脚本 - 飞书列表格式导出 v1.1.0

将标准Markdown格式的Bug报告转换为飞书思维笔记兼容的列表格式。

修复历史：
- v1.0.0 (2026-04-23): 初始版本
- v1.1.0 (2026-06-29): 增加Bug ID/创建人/状态/优先级等字段映射，
                       输出格式兼容飞书多维表格Base字段名

用法：
    python export_to_feishu_md.py --input bug_report.md --output feishu_bug.md
    python export_to_feishu_md.py --input bug_report.md  # 输出到同目录
"""

import argparse
import re
import sys
import os


def parse_bug_report(content: str) -> dict:
    """解析标准Markdown格式的Bug报告，提取各字段"""
    bug = {
        "title": "",
        "bug_id": "",
        "severity": "",
        "priority": "",
        "type": "",
        "module": "",
        "version": "",
        "os": "",
        "device": "",
        "app_version": "",
        "network": "",
        "assignee": "",
        "reporter": "",
        "status": "",
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
    # 备用：从一级标题提取
    if not bug["title"]:
        h1_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if h1_match:
            bug["title"] = h1_match.group(1).strip()

    # Bug ID（如 BUG-2026-001）
    id_match = re.search(r'BUG-\d{4}-\d{3,}', content)
    if id_match:
        bug["bug_id"] = id_match.group(0)

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
        "assignee": r'\*\*(?:处理人|负责人|Assignee)\*\*\s*\|\s*(.+?)\s*\|',
        "reporter": r'\*\*(?:创建人|报告人|Reporter)\*\*\s*\|\s*(.+?)\s*\|',
        "status": r'\*\*(?:当前状态|状态|Status)\*\*\s*\|\s*(.+?)\s*\|',
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


def to_feishu_format(bug: dict) -> str:
    """将Bug数据转换为飞书列表格式"""
    lines = []

    # 主标题
    if bug.get("bug_id"):
        lines.append(f"# {bug['bug_id']} - {bug['title'] or 'Bug报告'}")
    else:
        lines.append(f"# {bug['title'] or 'Bug报告'}")
    lines.append("")

    # 基本信息
    lines.append("- 基本信息")
    if bug.get("bug_id"):
        lines.append(f"  - Bug ID：{bug['bug_id']}")
    if bug["title"]:
        lines.append(f"  - Bug标题：{bug['title']}")
    if bug["severity"]:
        lines.append(f"  - 严重度：{bug['severity']}")
    if bug["priority"]:
        lines.append(f"  - 优先级：{bug['priority']}")
    if bug["type"]:
        lines.append(f"  - Bug类型：{bug['type']}")
    if bug["module"]:
        lines.append(f"  - 所属模块：{bug['module']}")
    if bug["version"]:
        lines.append(f"  - 发现版本：{bug['version']}")
    if bug.get("status"):
        lines.append(f"  - 当前状态：{bug['status']}")
    if bug.get("assignee"):
        lines.append(f"  - 处理人：{bug['assignee']}")
    if bug.get("reporter"):
        lines.append(f"  - 创建人：{bug['reporter']}")

    # 环境信息
    env_fields = [bug["os"], bug["device"], bug["app_version"], bug["network"]]
    if any(env_fields):
        lines.append("- 环境信息")
        if bug["os"]:
            lines.append(f"  - 操作系统：{bug['os']}")
        if bug["device"]:
            lines.append(f"  - 设备型号：{bug['device']}")
        if bug["app_version"]:
            lines.append(f"  - APP版本：{bug['app_version']}")
        if bug["network"]:
            lines.append(f"  - 网络环境：{bug['network']}")

    # 复现步骤
    if bug["steps"]:
        lines.append("- 复现步骤")
        for i, step in enumerate(bug["steps"], 1):
            lines.append(f"  - 步骤{i}：{step}")

    # 预期结果
    if bug["expected"]:
        lines.append("- 预期结果")
        # 多行预期结果分行显示
        for line in bug["expected"].split('\n'):
            line = line.strip()
            if line:
                lines.append(f"  - {line}")

    # 实际结果
    if bug["actual"]:
        lines.append("- 实际结果")
        for line in bug["actual"].split('\n'):
            line = line.strip()
            if line:
                lines.append(f"  - {line}")

    # 错误信息
    if bug["error_log"]:
        lines.append("- 错误信息")
        for line in bug["error_log"].split('\n'):
            line = line.strip()
            if line:
                lines.append(f"  - {line}")

    # 影响范围
    if bug["impact"]:
        lines.append("- 影响范围")
        for line in bug["impact"].split('\n'):
            line = line.strip().lstrip('- ')
            if line:
                lines.append(f"  - {line}")

    return '\n'.join(lines)


def convert_file(input_path: str, output_path: str = None) -> str:
    """转换Bug报告文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    bug = parse_bug_report(content)
    feishu_md = to_feishu_format(bug)

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}-飞书版.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(feishu_md)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Bug报告转飞书格式')
    parser.add_argument('--input', '-i', required=True, help='输入Bug报告Markdown文件')
    parser.add_argument('--output', '-o', help='输出飞书格式文件（默认同名-飞书版.md）')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 文件不存在：{args.input}")
        sys.exit(1)

    output = convert_file(args.input, args.output)
    print(f"✅ 飞书格式Bug报告已生成：{output}")
    print(f"📋 导入方式：复制内容 → 飞书文档 → 粘贴")


if __name__ == '__main__':
    main()
