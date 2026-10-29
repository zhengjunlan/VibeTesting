#!/usr/bin/env python3
"""
Bug报告质量自检脚本 v1.1.0

按 6 维度对Bug报告打分，60分及格，低于60分自动标红"需补充信息"。

6 维度：
1. 复现步骤（25分）—— 是否可独立复现、步骤是否连续编号
2. 预期/实际（20分）—— 是否都有明确描述
3. 环境信息（15分）—— 是否包含OS/浏览器/版本/模型版本
4. 严重度（15分）—— 是否与影响范围匹配
5. 附件（15分）—— 是否有截图/日志/录屏
6. 标题（10分）—— 是否简洁准确描述问题

用法：
    python bug_quality_checker.py --input bug_report.md
    python bug_quality_checker.py --input bug.md --output quality_report.md
    echo "..." | python bug_quality_checker.py --stdin
"""

import argparse
import re
import sys
import os
from pathlib import Path

# 严重度等级定义（数字越大越严重）
SEVERITY_LEVELS = {
    'P0': 4, 'P1': 3, 'P2': 2, 'P3': 1, 'P4': 0,
    'fatal': 4, 'critical': 3, 'major': 2, 'minor': 1, 'suggestion': 0,
    '致命': 4, '严重': 3, '一般': 2, '轻微': 1, '建议': 0,
    '4-致命': 4, '3-严重': 3, '2-一般': 2, '1-轻微': 1,
    'urgent': 3, 'high': 3, 'medium': 2, 'low': 1, 'p0': 4, 'p1': 3, 'p2': 2, 'p3': 1
}


def check_reproduce_steps(content: str) -> dict:
    """维度1：复现步骤（25分）"""
    score = 25
    issues = []

    # 提取复现步骤段
    steps_match = re.search(r'###\s*复现步骤\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if not steps_match:
        steps_match = re.search(r'【复现步骤】\s*\n(.+?)(?=\n【|\Z)', content, re.DOTALL)
    if not steps_match:
        return {"dim": "复现步骤", "score": 0, "max": 25, "issues": ["❌ 缺失复现步骤段"]}

    steps_text = steps_match.group(1).strip()

    # 检查是否包含「1. 2. 3.」编号
    numbered_steps = re.findall(r'^\s*\d+[\.、]\s*\S', steps_text, re.MULTILINE)
    if not numbered_steps:
        score -= 10
        issues.append("⚠️ 复现步骤未使用连续编号（1. 2. 3.）")
    elif len(numbered_steps) < 2:
        score -= 5
        issues.append("⚠️ 复现步骤少于2步，疑似不完整")

    # 检查是否包含具体操作关键词
    op_keywords = ['打开', '点击', '输入', '选择', '提交', '访问', '登录', '进入', '操作', '执行']
    if not any(kw in steps_text for kw in op_keywords):
        score -= 8
        issues.append("⚠️ 复现步骤缺少具体操作动词（打开/点击/输入/提交等）")

    # 检查前置条件
    precond_keywords = ['环境', '前提', '准备', '前提条件', '前置']
    if not any(kw in steps_text for kw in precond_keywords):
        score -= 2
        issues.append("ℹ️ 建议补充前置条件（环境/数据/账号）")

    return {"dim": "复现步骤", "score": max(0, score), "max": 25, "issues": issues}


def check_expected_actual(content: str) -> dict:
    """维度2：预期/实际（20分）"""
    score = 20
    issues = []

    has_expected = bool(re.search(r'###\s*预期结果|##\s*预期|【预期结果】', content))
    has_actual = bool(re.search(r'###\s*实际结果|##\s*实际|【实际结果】', content))

    if not has_expected:
        score -= 10
        issues.append("❌ 缺失预期结果描述")
    if not has_actual:
        score -= 10
        issues.append("❌ 缺失实际结果描述")

    # 检查内容是否过于简短（<5字视为占位符）
    exp_match = re.search(r'###\s*预期结果\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if exp_match and len(exp_match.group(1).strip()) < 5:
        score -= 3
        issues.append("⚠️ 预期结果描述过于简短")

    act_match = re.search(r'###\s*实际结果\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
    if act_match and len(act_match.group(1).strip()) < 5:
        score -= 3
        issues.append("⚠️ 实际结果描述过于简短")

    return {"dim": "预期/实际", "score": max(0, score), "max": 20, "issues": issues}


def check_environment(content: str) -> dict:
    """维度3：环境信息（15分）"""
    score = 15
    issues = []

    required_envs = [
        (r'操作系统|OS', '操作系统', 4),
        (r'浏览器|Browser|Chrome|Safari|Firefox|Edge', '浏览器', 3),
        (r'APP版本|应用版本|发现版本|version', '应用版本', 3),
        (r'设备|device|model|型号', '设备型号', 2),
        (r'网络|network|4G|5G|WiFi|WIFI', '网络环境', 2),
        (r'模型|model|gpt|claude|gemini|llm', 'AI模型版本', 1),
    ]

    for pattern, name, points in required_envs:
        if not re.search(pattern, content, re.IGNORECASE):
            score -= points
            issues.append(f"⚠️ 缺失{name}（-{points}分）")

    return {"dim": "环境信息", "score": max(0, score), "max": 15, "issues": issues}


def check_severity(content: str) -> dict:
    """维度4：严重度（15分）"""
    score = 15
    issues = []

    sev_match = re.search(r'\*\*(?:严重度|严重程度|severity)\*\*\s*[|:]\s*(.+?)(?:\n|\||$)', content, re.IGNORECASE)
    if not sev_match:
        return {"dim": "严重度", "score": 0, "max": 15, "issues": ["❌ 缺失严重度字段"]}

    severity = sev_match.group(1).strip().upper()
    severity_num = SEVERITY_LEVELS.get(severity, SEVERITY_LEVELS.get(sev_match.group(1).strip().lower(), None))

    if severity_num is None:
        score -= 8
        issues.append(f"⚠️ 严重度值未识别：{sev_match.group(1).strip()}（建议使用P0/P1/P2/P3/P4）")
    else:
        # 检查严重度与影响范围是否匹配
        impact_match = re.search(r'###\s*影响范围\s*\n(.+?)(?=\n###|\Z)', content, re.DOTALL)
        if impact_match:
            impact_text = impact_match.group(1).lower()
            # P0 应当影响 >50% 用户或有数据风险
            if severity_num == 4 and not re.search(r'100%|全部|所有|核心|资金|数据丢失|宕机|不可用|全局', impact_text):
                score -= 5
                issues.append("ℹ️ P0级Bug但影响范围描述较弱（建议明确为'100%用户受影响'或'资金/数据风险'）")
            # P3/P4 不应影响核心功能
            if severity_num <= 1 and re.search(r'100%|全部|宕机|不可用', impact_text):
                score -= 5
                issues.append("ℹ️ 严重度偏低（"+sev_match.group(1).strip()+"）但影响范围描述为全量，疑似严重度误判")

    return {"dim": "严重度", "score": max(0, score), "max": 15, "issues": issues}


def check_attachments(content: str) -> dict:
    """维度5：附件（15分）"""
    score = 15
    issues = []

    has_image = bool(re.search(r'!\[.*?\]\(.*?\)|screenshot|\.png|\.jpg|\.jpeg|\.gif', content, re.IGNORECASE))
    has_log = bool(re.search(r'```[\s\S]*?(?:error|exception|stack|fail|stacktrace)[\s\S]*?```', content, re.IGNORECASE))
    has_recording = bool(re.search(r'录屏|recording|\.mp4|\.mov|\.webm', content, re.IGNORECASE))
    has_attachment_section = bool(re.search(r'###\s*附件|##\s*附件|附件[：:]', content))

    if has_recording:
        pass  # 录屏满分
    elif has_image and has_log:
        pass  # 截图+日志满分
    elif has_image or has_log:
        score -= 5
        issues.append("⚠️ 仅有截图或日志其一，建议补充另一种")
    elif has_attachment_section:
        score -= 8
        issues.append("⚠️ 附件段存在但未识别到具体文件（截图/日志/录屏）")
    else:
        score -= 12
        issues.append("❌ 缺失附件（截图/日志/录屏）")

    return {"dim": "附件", "score": max(0, score), "max": 15, "issues": issues}


def check_title(content: str) -> dict:
    """维度6：标题（10分）"""
    score = 10
    issues = []

    # 提取标题
    title_match = re.search(r'^#\s+(.+?)$|^\*\*Bug标题\*\*\s*[|:]\s*(.+?)(?:\n|$)', content, re.MULTILINE)
    if not title_match:
        return {"dim": "标题", "score": 0, "max": 10, "issues": ["❌ 缺失Bug标题"]}

    title = (title_match.group(1) or title_match.group(2)).strip()

    # 检查长度
    if len(title) < 5:
        score -= 5
        issues.append(f"⚠️ 标题过短（{len(title)}字），建议至少5字")
    elif len(title) > 60:
        score -= 3
        issues.append(f"ℹ️ 标题过长（{len(title)}字），建议精简到60字以内")

    # 检查是否包含模糊词
    fuzzy_words = ['问题', '异常', '错误', 'bug', '不工作', '失败']
    if title.lower() in [w.lower() for w in fuzzy_words] or len(title) <= 4:
        score -= 5
        issues.append(f"⚠️ 标题过于模糊（'{title}'），建议明确问题现象+模块+场景")

    # 检查是否包含模块+现象
    if ' ' not in title and '：' not in title and '：' not in title:
        # 标题没空格可能是单个词
        if len(title) < 15:
            score -= 2
            issues.append("ℹ️ 建议标题格式：模块+现象（如'订单提交失败：500错误'）")

    return {"dim": "标题", "score": max(0, score), "max": 10, "issues": issues}


def check_bug_quality(content: str) -> dict:
    """综合6维度评分"""
    dimensions = [
        check_reproduce_steps(content),
        check_expected_actual(content),
        check_environment(content),
        check_severity(content),
        check_attachments(content),
        check_title(content),
    ]

    total_score = sum(d["score"] for d in dimensions)
    max_score = sum(d["max"] for d in dimensions)
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    passed = total_score >= 60

    all_issues = []
    for d in dimensions:
        for issue in d["issues"]:
            all_issues.append(f"[{d['dim']}] {issue}")

    return {
        "total_score": total_score,
        "max_score": max_score,
        "percentage": round(percentage, 1),
        "passed": passed,
        "dimensions": dimensions,
        "all_issues": all_issues,
    }


def format_report(result: dict, bug_name: str = "Bug报告") -> str:
    """生成可读的质量报告"""
    lines = []
    lines.append(f"# {bug_name} - 质量评分报告")
    lines.append("")
    lines.append(f"## 总分：{result['total_score']} / {result['max_score']} ({result['percentage']}%)")
    lines.append("")

    if result["passed"]:
        lines.append(f"✅ **及格**（>=60分）")
    else:
        lines.append(f"❌ **不通过**（<60分），需补充信息后重新提单")
    lines.append("")

    lines.append("## 6 维度评分")
    lines.append("")
    lines.append("| 维度 | 得分 | 满分 | 占比 | 状态 |")
    lines.append("|------|------|------|------|------|")
    for d in result["dimensions"]:
        status = "✅" if d["score"] >= d["max"] * 0.8 else ("⚠️" if d["score"] >= d["max"] * 0.5 else "❌")
        lines.append(f"| {d['dim']} | {d['score']} | {d['max']} | {d['score']/d['max']*100:.0f}% | {status} |")
    lines.append("")

    if result["all_issues"]:
        lines.append("## 问题清单")
        lines.append("")
        for issue in result["all_issues"]:
            lines.append(f"- {issue}")
        lines.append("")

    lines.append("---")
    lines.append(f"评分时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"评分器：bug-report-writer v1.1.0 bug_quality_checker.py")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Bug报告质量自检（6维度评分）')
    parser.add_argument('--input', '-i', help='输入Bug报告Markdown文件')
    parser.add_argument('--stdin', action='store_true', help='从stdin读取内容')
    parser.add_argument('--output', '-o', help='输出评分报告文件（默认输出到控制台）')
    parser.add_argument('--json', action='store_true', help='输出JSON格式评分结果')
    args = parser.parse_args()

    if args.stdin:
        content = sys.stdin.read()
    elif args.input:
        if not os.path.exists(args.input):
            print(f"❌ 文件不存在：{args.input}", file=sys.stderr)
            sys.exit(1)
        with open(args.input, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        print("❌ 必须指定 --input 或 --stdin", file=sys.stderr)
        sys.exit(1)

    result = check_bug_quality(content)

    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        bug_name = Path(args.input).name if args.input else "Bug报告"
        report = format_report(result, bug_name)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✅ 质量报告已生成：{args.output}")
            print(f"   总分：{result['total_score']}/{result['max_score']} ({result['percentage']}%) {'✅及格' if result['passed'] else '❌不通过'}")
        else:
            print(report)


if __name__ == '__main__':
    main()
