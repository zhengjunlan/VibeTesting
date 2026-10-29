#!/usr/bin/env python3
"""
Bug报告HTML可视化脚本 v1.1.0

将Markdown格式的Bug报告转换为3视图HTML报告：
- dev 视图：技术细节（开发人员视角）—— 完整复现步骤、错误日志、堆栈、环境
- qa 视图：流程视角（测试人员视角）—— 状态流转、用例关联、影响范围
- mgmt 视图：管理视角（项目经理视角）—— 严重度分布、处理人、阻塞关系

用法：
    python report_to_html.py --input bug_report.md --output bug_report.html --view dev
    python report_to_html.py --input bug_report.md --output bug_report.html --view qa
    python report_to_html.py --input bug_report.md --output bug_report.html --view mgmt
    python report_to_html.py --input bug_report.md --output all_views/ --all
"""

import argparse
import re
import sys
import os
import json
from pathlib import Path

# 3视图配色
VIEW_COLORS = {
    'dev': {'primary': '#1E40AF', 'light': '#DBEAFE', 'name': '开发视图', 'icon': '⚙️'},
    'qa': {'primary': '#059669', 'light': '#D1FAE5', 'name': '测试视图', 'icon': '🧪'},
    'mgmt': {'primary': '#DC2626', 'light': '#FEE2E2', 'name': '管理视图', 'icon': '📊'},
}


def parse_bug(content: str) -> dict:
    """解析Bug报告Markdown为结构化数据"""
    bug = {
        "title": "",
        "bug_id": "",
        "severity": "",
        "priority": "",
        "type": "",
        "module": "",
        "version": "",
        "os": "",
        "browser": "",
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

    # 标题
    title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
    if title_match:
        bug["title"] = title_match.group(1).strip()
    # 备用：从表格提取
    if not bug["title"]:
        title_match = re.search(r'\*\*Bug标题\*\*\s*\|\s*(.+?)\s*\|', content)
        if title_match:
            bug["title"] = title_match.group(1).strip()

    # Bug ID
    id_match = re.search(r'BUG-\d{4}-\d{3,}', content)
    if id_match:
        bug["bug_id"] = id_match.group(0)

    # 表格字段
    field_patterns = {
        "severity": r'\*\*(?:严重度|严重程度)\*\*\s*\|\s*(.+?)\s*\|',
        "priority": r'\*\*优先级\*\*\s*\|\s*(.+?)\s*\|',
        "type": r'\*\*Bug类型\*\*\s*\|\s*(.+?)\s*\|',
        "module": r'\*\*所属模块\*\*\s*\|\s*(.+?)\s*\|',
        "version": r'\*\*发现版本\*\*\s*\|\s*(.+?)\s*\|',
        "os": r'\*\*操作系统\*\*\s*\|\s*(.+?)\s*\|',
        "browser": r'\*\*(?:浏览器|运行环境)\*\*\s*\|\s*(.+?)\s*\|',
        "app_version": r'\*\*APP版本\*\*\s*\|\s*(.+?)\s*\|',
        "network": r'\*\*网络环境\*\*\s*\|\s*(.+?)\s*\|',
        "assignee": r'\*\*(?:处理人|负责人)\*\*\s*\|\s*(.+?)\s*\|',
        "reporter": r'\*\*(?:创建人|报告人)\*\*\s*\|\s*(.+?)\s*\|',
        "status": r'\*\*(?:当前状态|状态)\*\*\s*\|\s*(.+?)\s*\|',
    }
    for field, pattern in field_patterns.items():
        m = re.search(pattern, content)
        if m:
            bug[field] = m.group(1).strip()

    # 复现步骤
    steps_match = re.search(r'###\s*复现步骤\s*\n((?:\d+\..+\n?)+)', content)
    if steps_match:
        bug["steps"] = [
            re.sub(r'^\d+\.\s*', '', line.strip())
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

    return bug


def generate_html(bug: dict, view: str = 'dev') -> str:
    """生成指定视图的HTML"""
    color = VIEW_COLORS[view]
    title = bug.get("title") or "Bug报告"
    bug_id = bug.get("bug_id") or "未分配ID"

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title} - {color['name']}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #F9FAFB;
    color: #1F2937;
    line-height: 1.6;
    padding: 20px;
}}
.header {{
    background: linear-gradient(135deg, {color['primary']} 0%, {color['light']} 100%);
    color: white;
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}
.header h1 {{
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 8px;
}}
.header .subtitle {{
    font-size: 14px;
    opacity: 0.95;
    color: #ffffff;
}}
.badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 8px;
    background: rgba(255,255,255,0.2);
    color: #ffffff;
}}
.severity-P0, .severity-致命 {{ background: #DC2626 !important; }}
.severity-P1, .severity-严重 {{ background: #EA580C !important; }}
.severity-P2, .severity-一般 {{ background: #CA8A04 !important; }}
.severity-P3, .severity-轻微 {{ background: #65A30D !important; }}
.severity-P4, .severity-建议 {{ background: #6B7280 !important; }}
.section {{
    background: white;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border-left: 4px solid {color['primary']};
}}
.section h2 {{
    color: {color['primary']};
    font-size: 18px;
    margin-bottom: 12px;
    font-weight: 600;
}}
.section h3 {{
    color: #374151;
    font-size: 15px;
    margin: 12px 0 8px;
    font-weight: 600;
}}
.info-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
}}
.info-table th, .info-table td {{
    text-align: left;
    padding: 8px 12px;
    border-bottom: 1px solid #E5E7EB;
    font-size: 14px;
}}
.info-table th {{
    background: {color['light']};
    color: {color['primary']};
    width: 120px;
    font-weight: 600;
}}
.steps-list {{
    list-style: none;
    counter-reset: step;
    padding-left: 0;
}}
.steps-list li {{
    counter-increment: step;
    padding: 8px 12px 8px 40px;
    margin: 6px 0;
    background: {color['light']};
    border-radius: 6px;
    position: relative;
}}
.steps-list li::before {{
    content: counter(step);
    position: absolute;
    left: 12px;
    top: 8px;
    width: 22px;
    height: 22px;
    background: {color['primary']};
    color: white;
    border-radius: 50%;
    text-align: center;
    line-height: 22px;
    font-size: 12px;
    font-weight: 700;
}}
pre, code {{
    background: #1F2937;
    color: #F9FAFB;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 13px;
    overflow-x: auto;
    font-family: "SF Mono", "Monaco", "Menlo", monospace;
}}
pre {{ white-space: pre-wrap; word-break: break-all; }}
.impact {{
    background: #FEF3C7;
    border-left-color: #F59E0B;
}}
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-top: 12px;
}}
.kpi {{
    background: {color['light']};
    padding: 12px 16px;
    border-radius: 8px;
    text-align: center;
}}
.kpi-value {{
    font-size: 24px;
    font-weight: 700;
    color: {color['primary']};
}}
.kpi-label {{
    font-size: 12px;
    color: #6B7280;
    margin-top: 4px;
}}
</style>
</head>
<body>
<div class="header">
    <h1>{color['icon']} {bug_id} - {title}</h1>
    <div class="subtitle">
        <span class="badge severity-{bug.get('severity', 'P2')}">严重度：{bug.get('severity', '待定')}</span>
        <span class="badge">优先级：{bug.get('priority', '中')}</span>
        <span class="badge">状态：{bug.get('status', '待处理')}</span>
        <span class="badge">模块：{bug.get('module', '未分类')}</span>
    </div>
</div>
'''

    # 基本信息
    html += '''
<div class="section">
    <h2>📋 基本信息</h2>
    <table class="info-table">
'''
    fields = [
        ('Bug ID', bug.get('bug_id') or '未分配'),
        ('严重度', bug.get('severity') or '待定'),
        ('优先级', bug.get('priority') or '中'),
        ('Bug类型', bug.get('type') or '未分类'),
        ('所属模块', bug.get('module') or '未分类'),
        ('发现版本', bug.get('version') or '待补充'),
        ('处理人', bug.get('assignee') or '待指派'),
        ('创建人', bug.get('reporter') or 'Jasmine'),
        ('当前状态', bug.get('status') or '待处理'),
    ]
    for label, value in fields:
        html += f'<tr><th>{label}</th><td>{value}</td></tr>\n'
    html += '</table>\n</div>\n'

    # 环境信息（dev 视图重点）
    if view == 'dev':
        html += '''
<div class="section">
    <h2>🖥️ 环境信息</h2>
    <table class="info-table">
'''
        env_fields = [
            ('操作系统', bug.get('os') or '待补充'),
            ('浏览器', bug.get('browser') or 'N/A'),
            ('APP版本', bug.get('app_version') or bug.get('version') or '待补充'),
            ('网络环境', bug.get('network') or '待补充'),
        ]
        for label, value in env_fields:
            html += f'<tr><th>{label}</th><td>{value}</td></tr>\n'
        html += '</table>\n</div>\n'

    # 复现步骤
    if bug.get('steps'):
        html += '<div class="section"><h2>🔄 复现步骤</h2><ol class="steps-list">\n'
        for step in bug['steps']:
            html += f'<li>{step}</li>\n'
        html += '</ol></div>\n'

    # 预期/实际
    html += '<div class="section"><h2>✅ 预期 / ❌ 实际</h2>\n'
    if bug.get('expected'):
        html += f'<h3>预期结果</h3><p>{bug["expected"]}</p>\n'
    if bug.get('actual'):
        html += f'<h3>实际结果</h3><p>{bug["actual"]}</p>\n'
    html += '</div>\n'

    # 错误日志（dev 视图重点）
    if bug.get('error_log') and view == 'dev':
        html += '<div class="section"><h2>📜 错误日志</h2><pre><code>'
        html += bug['error_log'].replace('<', '&lt;').replace('>', '&gt;')
        html += '</code></pre></div>\n'

    # 影响范围（mgmt 视图重点）
    if bug.get('impact'):
        html += f'<div class="section impact"><h2>💥 影响范围</h2><p>{bug["impact"]}</p></div>\n'

    # mgmt 视图：增加 KPI
    if view == 'mgmt':
        html += '<div class="section"><h2>📊 关键指标</h2><div class="kpi-grid">\n'
        html += f'<div class="kpi"><div class="kpi-value">{bug.get("severity", "P2")}</div><div class="kpi-label">严重度</div></div>\n'
        html += f'<div class="kpi"><div class="kpi-value">{len(bug.get("steps", []))}</div><div class="kpi-label">复现步骤数</div></div>\n'
        html += f'<div class="kpi"><div class="kpi-value">{bug.get("status", "待处理")}</div><div class="kpi-label">当前状态</div></div>\n'
        html += '</div></div>\n'

    # qa 视图：增加流程信息
    if view == 'qa':
        html += '<div class="section"><h2>🧪 测试流程</h2><table class="info-table">\n'
        html += f'<tr><th>用例关联</th><td>[关联测试用例ID]</td></tr>\n'
        html += f'<tr><th>发现时间</th><td>[发现时间]</td></tr>\n'
        html += f'<tr><th>回归状态</th><td>[待回归 / 已回归 / 回归失败]</td></tr>\n'
        html += f'<tr><th>阻塞关系</th><td>[阻塞X个用例 / 被X阻塞]</td></tr>\n'
        html += '</table></div>\n'

    # 底部
    html += f'''
<div class="section" style="border-left-color: #6B7280; background: #F9FAFB;">
    <p style="text-align: center; color: #6B7280; font-size: 12px;">
        生成于 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · bug-report-writer v1.1.0 · {color['name']}
    </p>
</div>
</body>
</html>'''

    return html


def main():
    parser = argparse.ArgumentParser(description='Bug报告HTML可视化 v1.1.0')
    parser.add_argument('--input', '-i', required=True, help='输入Bug报告Markdown文件')
    parser.add_argument('--output', '-o', help='输出HTML文件路径（单视图模式）')
    parser.add_argument('--view', '-v', choices=['dev', 'qa', 'mgmt'], default='dev', help='视图类型：dev/qa/mgmt')
    parser.add_argument('--all', action='store_true', help='生成全部3个视图到输出目录')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 文件不存在：{args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    bug = parse_bug(content)
    print(f"📋 解析Bug：{bug.get('title', 'N/A')[:50]}")
    print(f"   严重度：{bug.get('severity', 'N/A')}, 步骤数：{len(bug.get('steps', []))}")

    if args.all:
        # 生成3个视图
        out_dir = args.output or './bug_views'
        os.makedirs(out_dir, exist_ok=True)
        bug_id = bug.get('bug_id') or Path(args.input).stem
        for view in ['dev', 'qa', 'mgmt']:
            html = generate_html(bug, view=view)
            out_path = os.path.join(out_dir, f"{bug_id}-{view}.html")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  ✅ {VIEW_COLORS[view]['icon']} {VIEW_COLORS[view]['name']}：{out_path} ({len(html)} chars)")
        print(f"\n💡 浏览器打开 {out_dir}/ 目录下的HTML文件预览")
    else:
        # 单视图
        out_path = args.output or args.input.replace('.md', f'-{args.view}.html')
        html = generate_html(bug, view=args.view)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ {VIEW_COLORS[args.view]['name']}已生成：{out_path} ({len(html)} chars)")


if __name__ == '__main__':
    main()
