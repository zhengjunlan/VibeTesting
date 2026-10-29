#!/usr/bin/env python3
"""
Bug报告格式转换脚本 - 通用格式转换 v1.1.0

支持在不同Bug报告格式间转换：标准Markdown ↔ 飞书 ↔ 禅道 ↔ TAPD ↔ Jira

修复历史：
- v1.0.0 (2026-04-23): 初始版本
- v1.1.0 (2026-06-29): 修复导入路径 + 实现markdown格式 + 新增TAPD支持
                       + 保留Jira格式支持 + 复用export_to_feishu_md公共函数

用法：
    python convert_format.py --input bug_report.md --format feishu --output feishu_bug.md
    python convert_format.py --input bug_report.md --format jira --output jira_bug.md
    python convert_format.py --input bug_report.md --format zentao --output zentao_bug.md
    python convert_format.py --input bug_report.md --format tapd --output tapd_bug.md
    python convert_format.py --input bug_report.md --format markdown --output std_bug.md
"""

import argparse
import sys
import os

# 修复导入路径：脚本可直接运行也可作为模块被导入
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from export_to_feishu_md import parse_bug_report, to_feishu_format
from export_to_zentao_md import generate_zentao_report
from export_to_jira_md import to_jira_format


def detect_input_format(content: str) -> str:
    """自动检测输入文件的格式"""
    if content.strip().startswith('# ') and '- ' in content and '||' not in content:
        return 'feishu'
    if '【Bug标题】' in content or '【严重程度】' in content:
        return 'zentao'
    if '[TAPD]' in content or '| 缺陷标题 |' in content:
        return 'tapd'
    if '{code}' in content or '*Summary*' in content or 'h3.' in content:
        return 'jira'
    return 'markdown'


def to_tapd_format(bug: dict) -> str:
    """转换为TAPD格式（腾讯系常用）"""
    severity_map = {
        'P0': '致命', 'P1': '严重', 'P2': '一般', 'P3': '轻微', 'P4': '建议',
        'fatal': '致命', 'critical': '严重', 'major': '一般', 'minor': '轻微', 'suggestion': '建议'
    }
    sev = bug.get('severity', '')
    sev_cn = severity_map.get(sev, sev if sev else '一般')

    lines = []
    lines.append(f"[TAPD] 缺陷报告")
    lines.append("")
    lines.append(f"| 字段 | 内容 |")
    lines.append(f"|------|------|")
    lines.append(f"| **缺陷标题** | {bug.get('title', '待补充')} |")
    lines.append(f"| **严重程度** | {sev_cn} |")
    lines.append(f"| **优先级** | {bug.get('priority', '中')} |")
    lines.append(f"| **处理人** | {bug.get('assignee', '待指派')} |")
    lines.append(f"| **创建人** | {bug.get('reporter', 'Jasmine')} |")
    lines.append(f"| **所属模块** | {bug.get('module', '待补充')} |")
    lines.append(f"| **影响版本** | {bug.get('version', bug.get('app_version', '待补充'))} |")
    lines.append(f"| **当前状态** | {bug.get('status', '待处理')} |")
    lines.append("")

    # 描述
    lines.append("### 缺陷描述")
    title = bug.get('title', '')
    actual = bug.get('actual', '')
    impact = bug.get('impact', '')
    desc = []
    if actual:
        desc.append(actual)
    if impact:
        desc.append(f"影响：{impact}")
    lines.append(" ".join(desc) if desc else "待补充")
    lines.append("")

    # 复现步骤
    lines.append("### 复现步骤")
    steps_val = bug.get('steps')
    if isinstance(steps_val, list):
        lines.append('\n'.join(f"{i+1}. {s}" for i, s in enumerate(steps_val)) if steps_val else '1. [待补充]')
    elif steps_val:
        lines.append(steps_val)
    else:
        lines.append('1. [待补充]')
    lines.append("")

    # 预期/实际
    lines.append("### 预期结果")
    lines.append(bug.get('expected', '待补充'))
    lines.append("")
    lines.append("### 实际结果")
    lines.append(bug.get('actual', '待补充'))
    lines.append("")

    # 错误日志
    if bug.get('error_log'):
        lines.append("### 错误日志")
        lines.append("```")
        lines.append(bug['error_log'])
        lines.append("```")
        lines.append("")

    # 环境
    lines.append("### 环境信息")
    lines.append(f"- 操作系统：{bug.get('os', '待补充')}")
    if bug.get('browser'):
        lines.append(f"- 浏览器：{bug['browser']}")
    if bug.get('app_version'):
        lines.append(f"- 应用版本：{bug['app_version']}")
    lines.append("")

    return "\n".join(lines)


def to_markdown_format(bug: dict) -> str:
    """转换为标准Markdown格式（v1.1.0新增）"""
    lines = []
    lines.append(f"# {bug.get('title', '待补充')}")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **严重程度**：{bug.get('severity', '待补充')}")
    lines.append(f"- **优先级**：{bug.get('priority', '待补充')}")
    lines.append(f"- **Bug类型**：{bug.get('type', '待补充')}")
    lines.append(f"- **所属模块**：{bug.get('module', '待补充')}")
    lines.append(f"- **影响版本**：{bug.get('version', bug.get('app_version', '待补充'))}")
    lines.append(f"- **处理人**：{bug.get('assignee', '待指派')}")
    lines.append(f"- **当前状态**：{bug.get('status', '待处理')}")
    lines.append("")

    lines.append("## 环境信息")
    lines.append("")
    lines.append(f"- **操作系统**：{bug.get('os', '待补充')}")
    if bug.get('browser'):
        lines.append(f"- **浏览器**：{bug['browser']}")
    if bug.get('app_version'):
        lines.append(f"- **应用版本**：{bug['app_version']}")
    lines.append("")

    lines.append("## 复现步骤")
    lines.append("")
    steps_val = bug.get('steps')
    if isinstance(steps_val, list):
        lines.append('\n'.join(f"{i+1}. {s}" for i, s in enumerate(steps_val)) if steps_val else '1. [待补充]')
    elif steps_val:
        lines.append(steps_val)
    else:
        lines.append('1. [待补充]')
    lines.append("")

    lines.append("## 预期结果")
    lines.append("")
    lines.append(bug.get('expected', '待补充'))
    lines.append("")

    lines.append("## 实际结果")
    lines.append("")
    lines.append(bug.get('actual', '待补充'))
    lines.append("")

    if bug.get('error_log'):
        lines.append("## 错误日志")
        lines.append("")
        lines.append("```")
        lines.append(bug['error_log'])
        lines.append("```")
        lines.append("")

    if bug.get('impact'):
        lines.append("## 影响范围")
        lines.append("")
        lines.append(f"- {bug['impact']}")
        lines.append("")

    if bug.get('attachments'):
        lines.append("## 附件")
        lines.append("")
        for a in bug['attachments']:
            lines.append(f"- {a}")
        lines.append("")

    return "\n".join(lines)


def convert_file(input_path: str, target_format: str, output_path: str = None) -> str:
    """转换Bug报告到目标格式"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    source_format = detect_input_format(content)
    bug = parse_bug_report(content)

    format_map = {
        'feishu': to_feishu_format,
        'zentao': lambda bug: generate_zentao_report(bug),
        'tapd': to_tapd_format,
        'jira': to_jira_format,
        'markdown': to_markdown_format,
    }

    if target_format not in format_map:
        print(f"❌ 不支持的目标格式：{target_format}")
        print(f"📋 支持的格式：{', '.join(format_map.keys())}")
        sys.exit(1)

    converter = format_map[target_format]
    result = converter(bug)

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        suffix = f"-{target_format}版" if target_format != 'markdown' else "-std"
        output_path = f"{base}{suffix}.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Bug报告格式转换 v1.1.0')
    parser.add_argument('--input', '-i', required=True, help='输入Bug报告文件')
    parser.add_argument('--format', '-f', required=True,
                       choices=['feishu', 'zentao', 'tapd', 'jira', 'markdown'],
                       help='目标格式：feishu/zentao/tapd/jira/markdown')
    parser.add_argument('--output', '-o', help='输出文件路径')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 文件不存在：{args.input}")
        sys.exit(1)

    output = convert_file(args.input, args.format, args.output)

    format_names = {
        'feishu': '飞书', 'zentao': '禅道', 'tapd': 'TAPD', 'jira': 'Jira', 'markdown': '标准Markdown'
    }
    print(f"✅ {format_names.get(args.format, args.format)}格式Bug报告已生成：{output}")


if __name__ == '__main__':
    main()
