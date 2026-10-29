#!/usr/bin/env python3
"""
Bug报告 → JSON协议转换脚本 v1.1.0

将Markdown格式的Bug报告转换为标准JSON协议 `bug-reports/standard/v1`，
用于与 perf-report-writer / test-report-writer 等上游Skill的双向数据流转。

JSON协议格式：
{
    "protocol": "bug-reports/standard/v1",
    "bug": {
        "id": "BUG-2026-001",
        "title": "...",
        "severity": "P0|P1|P2|P3|P4",
        "type": "functional|performance|ai_model|...",
        "status": "open|in_progress|resolved|...",
        "environment": {...},
        "reproduce_steps": [...],
        "expected": "...",
        "actual": "...",
        "attachments": [...],
        "metadata": {...}
    },
    "downstream": {
        "perf_report_link": null,
        "test_report_link": null
    }
}

用法：
    python bug_to_json.py --input bug.md --output bug.json
    python bug_to_json.py --input bugs/ --output bugs.json --batch
"""

import argparse
import re
import sys
import os
import json
import glob
from pathlib import Path


# 严重度标准化映射
SEVERITY_MAP = {
    'P0': 'P0', 'p0': 'P0', '致命': 'P0', 'fatal': 'P0', '4': 'P0', '4-致命': 'P0',
    'P1': 'P1', 'p1': 'P1', '严重': 'P1', 'critical': 'P1', '3': 'P1', '3-严重': 'P1',
    'P2': 'P2', 'p2': 'P2', '一般': 'P2', 'major': 'P2', '2': 'P2', '2-一般': 'P2',
    'P3': 'P3', 'p3': 'P3', '轻微': 'P3', 'minor': 'P3', '1': 'P3', '1-轻微': 'P3',
    'P4': 'P4', 'p4': 'P4', '建议': 'P4', 'suggestion': 'P4',
}

# 状态标准化映射
STATUS_MAP = {
    'open': 'open', '待处理': 'open', '新建': 'open', '新': 'open',
    'in_progress': 'in_progress', '处理中': 'in_progress', '修复中': 'in_progress', '进行中': 'in_progress',
    'resolved': 'resolved', '已解决': 'resolved', '已修复': 'resolved', '修复完成': 'resolved',
    'closed': 'closed', '已关闭': 'closed', '关闭': 'closed',
    'reopened': 'reopened', '重开': 'reopened', '重新打开': 'reopened',
    'verified': 'verified', '已验证': 'verified',
    'deferred': 'deferred', '延期': 'deferred', '挂起': 'deferred',
    'rejected': 'rejected', '已拒绝': 'rejected', '拒绝': 'rejected',
}

# 类型标准化映射
TYPE_MAP = {
    'functional': 'functional', '功能': 'functional', '功能错误': 'functional',
    'performance': 'performance', '性能': 'performance',
    'compatibility': 'compatibility', '兼容': 'compatibility', '兼容性': 'compatibility',
    'security': 'security', '安全': 'security',
    'ui': 'ui', 'ui问题': 'ui', '界面': 'ui',
    'data': 'data', '数据': 'data', '数据问题': 'data',
    'interface': 'interface', '接口': 'interface', 'api': 'interface', 'API': 'interface',
    'ai_model': 'ai_model', '幻觉': 'ai_model', '模型退化': 'ai_model', '拒答': 'ai_model',
    'ai_agent': 'ai_agent', '工具调用': 'ai_agent', 'agent': 'ai_agent',
    'multimodal': 'multimodal', '多模态': 'multimodal', '图像': 'multimodal', '视频': 'multimodal', '语音': 'multimodal',
    'prompt_injection': 'prompt_injection', 'prompt注入': 'prompt_injection', '注入': 'prompt_injection',
    'code_error': 'code_error', '代码错误': 'code_error', '代码': 'code_error',
}


def normalize_severity(s: str) -> str:
    """标准化严重度为P0-P4"""
    if not s:
        return 'P2'
    s_clean = s.strip()
    return SEVERITY_MAP.get(s_clean, SEVERITY_MAP.get(s_clean.lower(), s_clean))


def normalize_status(s: str) -> str:
    """标准化状态"""
    if not s:
        return 'open'
    s_clean = s.strip()
    return STATUS_MAP.get(s_clean, STATUS_MAP.get(s_clean.lower(), s_clean))


def normalize_type(s: str) -> str:
    """标准化Bug类型"""
    if not s:
        return 'functional'
    s_clean = s.strip().lower()
    return TYPE_MAP.get(s_clean, TYPE_MAP.get(s_clean.lower(), s_clean))


def parse_md_to_protocol(content: str, source_file: str = None) -> dict:
    """将Markdown格式的Bug报告解析为标准JSON协议"""
    bug = {
        "id": "",
        "title": "",
        "severity": "P2",
        "priority": "medium",
        "type": "functional",
        "status": "open",
        "created_at": "",
        "environment": {
            "os": "",
            "browser": "",
            "app_version": "",
            "device": "",
            "network": "",
            "model_version": ""
        },
        "reproduce_steps": [],
        "expected": "",
        "actual": "",
        "error_log": "",
        "impact": "",
        "attachments": [],
        "labels": [],
        "assignee": "",
        "reporter": "",
        "source_file": source_file,
    }

    # Bug ID
    id_match = re.search(r'BUG-\d{4}-\d{3,}', content)
    if id_match:
        bug["id"] = id_match.group(0)

    # 标题
    title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    if title_match:
        bug["title"] = title_match.group(1).strip()
    if not bug["title"]:
        title_match = re.search(r'\*\*Bug标题\*\*\s*[|:]\s*(.+?)(?:\n|$)', content)
        if title_match:
            bug["title"] = title_match.group(1).strip()

    # 表格字段
    field_patterns = {
        "severity": (r'\*\*(?:严重度|严重程度)\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', 'severity'),
        "priority": (r'\*\*优先级\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "type": (r'\*\*Bug类型\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', 'type'),
        "status": (r'\*\*(?:当前状态|状态)\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', 'status'),
        "module": (r'\*\*所属模块\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "version": (r'\*\*发现版本\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "os": (r'\*\*操作系统\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "browser": (r'\*\*(?:浏览器|运行环境)\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "app_version": (r'\*\*APP版本\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "device": (r'\*\*设备型号\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "network": (r'\*\*网络环境\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "assignee": (r'\*\*(?:处理人|负责人)\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "reporter": (r'\*\*(?:创建人|报告人)\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
        "model_version": (r'\*\*模型版本\*\*\s*[|:]\s*(.+?)(?:\s*\||\n|$)', None),
    }

    for field, (pattern, normalize_key) in field_patterns.items():
        m = re.search(pattern, content)
        if m:
            value = m.group(1).strip()
            if field in ('os', 'browser', 'app_version', 'device', 'network', 'model_version'):
                bug["environment"][field] = value
            elif field == 'version':
                if not bug["environment"]["app_version"]:
                    bug["environment"]["app_version"] = value
            elif normalize_key:
                # 标准化
                if normalize_key == 'severity':
                    bug[field] = normalize_severity(value)
                elif normalize_key == 'type':
                    bug[field] = normalize_type(value)
                elif normalize_key == 'status':
                    bug[field] = normalize_status(value)
            else:
                bug[field] = value

    # 复现步骤
    steps_match = re.search(r'###\s*复现步骤\s*\n((?:\d+\..+\n?)+)', content)
    if not steps_match:
        steps_match = re.search(r'【复现步骤】\s*\n((?:\d+\..+\n?)+)', content)
    if steps_match:
        bug["reproduce_steps"] = [
            re.sub(r'^\d+[\.、]\s*', '', line.strip())
            for line in steps_match.group(1).strip().split('\n')
            if line.strip()
        ]

    # 预期/实际
    exp_match = re.search(r'###\s*预期结果\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if exp_match:
        bug["expected"] = exp_match.group(1).strip()
    act_match = re.search(r'###\s*实际结果\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if act_match:
        bug["actual"] = act_match.group(1).strip()

    # 错误日志
    err_match = re.search(r'###\s*错误信息?\s*\n```\s*\n(.*?)\n```', content, re.DOTALL)
    if err_match:
        bug["error_log"] = err_match.group(1).strip()

    # 影响
    impact_match = re.search(r'###\s*影响范围\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if impact_match:
        bug["impact"] = impact_match.group(1).strip()

    # 附件（图片/文件链接）
    bug["attachments"] = re.findall(r'!\[.*?\]\((.+?)\)|附件[：:]\s*(.+?)(?:\n|$)', content)

    # 标签
    tag_match = re.findall(r'#(\w+)', content)
    if tag_match:
        bug["labels"] = list(set(tag_match))

    # 创建时间（如果存在）
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
    if date_match:
        bug["created_at"] = date_match.group(1)

    # 包装为标准协议格式
    return {
        "protocol": "bug-reports/standard/v1",
        "bug": bug,
        "downstream": {
            "perf_report_link": None,
            "test_report_link": None,
            "linked_bugs": []
        },
        "metadata": {
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "generator": "bug-report-writer v1.1.0",
            "generator_version": "1.1.0",
            "source_format": "markdown"
        }
    }


def convert_file(input_path: str, output_path: str) -> str:
    """转换单个Markdown文件为JSON"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    result = parse_md_to_protocol(content, source_file=input_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Bug报告转JSON协议 v1.1.0')
    parser.add_argument('--input', '-i', required=True, help='输入Bug报告Markdown文件或目录（--batch模式）')
    parser.add_argument('--output', '-o', help='输出JSON文件路径（单文件模式）或目录（batch模式）')
    parser.add_argument('--batch', action='store_true', help='批量转换目录下所有.md文件')
    args = parser.parse_args()

    if args.batch:
        # 批量模式
        if not os.path.isdir(args.input):
            print(f"❌ --batch模式要求输入目录：{args.input}", file=sys.stderr)
            sys.exit(1)
        out_dir = args.output or args.input.rstrip('/') + '_json'
        os.makedirs(out_dir, exist_ok=True)

        md_files = glob.glob(os.path.join(args.input, '*.md'))
        if not md_files:
            print(f"❌ 目录下无.md文件：{args.input}", file=sys.stderr)
            sys.exit(1)

        all_bugs = []
        for md_file in md_files:
            try:
                json_file = os.path.join(out_dir, Path(md_file).stem + '.json')
                convert_file(md_file, json_file)
                # 收集到all_bugs
                with open(json_file, 'r', encoding='utf-8') as f:
                    all_bugs.append(json.load(f))
                print(f"  ✅ {os.path.basename(md_file)} -> {os.path.basename(json_file)}")
            except Exception as e:
                print(f"  ❌ {os.path.basename(md_file)} 失败：{e}", file=sys.stderr)

        # 写汇总文件
        all_bugs_path = os.path.join(out_dir, '_all_bugs.json')
        with open(all_bugs_path, 'w', encoding='utf-8') as f:
            json.dump({
                "protocol": "bug-reports/standard/v1",
                "batch": True,
                "count": len(all_bugs),
                "bugs": all_bugs
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 批量转换完成：{len(all_bugs)}个Bug -> {out_dir}/")
        print(f"   汇总文件：{all_bugs_path}")
    else:
        # 单文件模式
        if not os.path.exists(args.input):
            print(f"❌ 文件不存在：{args.input}", file=sys.stderr)
            sys.exit(1)
        out_path = args.output or args.input.replace('.md', '.json')
        convert_file(args.input, out_path)
        print(f"✅ JSON协议已生成：{out_path}")

        # 打印解析摘要
        with open(out_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        bug = result['bug']
        print(f"   ID: {bug['id'] or '(未分配)'}")
        print(f"   标题: {bug['title'][:50]}")
        print(f"   严重度: {bug['severity']} | 类型: {bug['type']} | 状态: {bug['status']}")
        print(f"   步骤数: {len(bug['reproduce_steps'])}")
        print(f"   协议: {result['protocol']}")


if __name__ == '__main__':
    main()
