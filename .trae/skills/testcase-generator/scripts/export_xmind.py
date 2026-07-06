"""
测试用例导出工具 - XMind 格式
将 Markdown 测试用例转换为 XMind 思维导图
"""
import sys
import argparse
from pathlib import Path
import xmind
from tc_parser import parse_testcase_markdown


def export_to_xmind(testcases: list, output_path: str, root_topic: str = "测试用例"):
    """
    将测试用例导出为 XMind 文件
    
    Args:
        testcases: 测试用例字典列表
        output_path: 输出文件路径
        root_topic: 根主题名称
    """
    if not testcases:
        print("警告: 没有测试用例可导出")
        return
    
    # 创建 XMind 工作簿
    workbook = xmind.load(output_path)
    sheet = workbook.getPrimarySheet()
    sheet.setTitle(root_topic)
    
    # 根主题
    root = sheet.getRootTopic()
    root.setTitle(root_topic)
    
    # 按模块分组
    modules = {}
    for tc in testcases:
        module = tc.get('所属模块', '未分类')
        if module not in modules:
            modules[module] = []
        modules[module].append(tc)
    
    # 创建模块主题
    for module_name, cases in modules.items():
        module_topic = root.addSubTopic()
        module_topic.setTitle(f"{module_name} ({len(cases)}条)")
        
        # 按优先级分组
        priorities = {}
        for tc in cases:
            priority = tc.get('优先级', 'P2')
            if priority not in priorities:
                priorities[priority] = []
            priorities[priority].append(tc)
        
        # 创建优先级主题
        for priority, priority_cases in sorted(priorities.items()):
            priority_topic = module_topic.addSubTopic()
            priority_topic.setTitle(f"{priority} ({len(priority_cases)}条)")
            
            # 创建用例主题
            for tc in priority_cases:
                tc_topic = priority_topic.addSubTopic()
                tc_id = tc.get('用例编号', 'TC_XXX')
                tc_title = tc.get('用例标题', '未命名')
                tc_topic.setTitle(f"{tc_id}: {tc_title}")
                
                # 添加详细信息作为备注
                details = []
                if tc.get('用例类型'):
                    details.append(f"类型: {tc['用例类型']}")
                if tc.get('前置条件'):
                    details.append(f"前置: {tc['前置条件']}")
                if tc.get('测试步骤'):
                    details.append(f"步骤: {tc['测试步骤']}")
                if tc.get('预期结果'):
                    details.append(f"预期: {tc['预期结果']}")
                
                if details:
                    tc_topic.addLabel('\n'.join(details))
    
    # 保存文件
    xmind.save(workbook, output_path)
    print(f"✓ XMind 导出成功: {output_path}")
    print(f"  共 {len(testcases)} 条测试用例，{len(modules)} 个模块")


def main():
    parser = argparse.ArgumentParser(description='将 Markdown 测试用例导出为 XMind')
    parser.add_argument('input', help='输入 Markdown 文件路径')
    parser.add_argument('-o', '--output', help='输出 XMind 文件路径（默认同名 .xmind）')
    parser.add_argument('-r', '--root', default='测试用例', help='根主题名称')
    
    args = parser.parse_args()
    
    # 读取 Markdown 文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在 {input_path}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 解析测试用例
    testcases = parse_testcase_markdown(md_content)
    
    if not testcases:
        print("错误: 未找到测试用例表格")
        sys.exit(1)
    
    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.xmind')
    
    # 导出
    export_to_xmind(testcases, str(output_path), args.root)


if __name__ == '__main__':
    main()
