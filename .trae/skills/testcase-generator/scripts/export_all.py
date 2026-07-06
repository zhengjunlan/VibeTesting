"""
测试用例批量导出工具
一键导出 Markdown 测试用例为 Excel 和 XMind 格式
"""
import sys
import argparse
from pathlib import Path
from tc_parser import parse_testcase_markdown
from export_excel import export_to_excel
from export_xmind import export_to_xmind


def export_all(input_path: str, output_dir: str = None, module_name: str = "测试用例"):
    """
    批量导出测试用例为所有支持的格式
    
    Args:
        input_path: 输入 Markdown 文件路径
        output_dir: 输出目录（默认与输入文件同目录）
        module_name: 工作表/根主题名称
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"错误: 文件不存在 {input_file}")
        return False
    
    # 确定输出目录
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_file.parent
    
    # 读取并解析
    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    testcases = parse_testcase_markdown(md_content)
    
    if not testcases:
        print("错误: 未找到测试用例表格")
        return False
    
    print(f"✓ 解析成功: 找到 {len(testcases)} 条测试用例")
    print()
    
    # 导出 Excel
    excel_file = output_path / f"{input_file.stem}.xlsx"
    try:
        export_to_excel(testcases, str(excel_file), module_name)
    except Exception as e:
        print(f"✗ Excel 导出失败: {e}")
    
    # 导出 XMind
    xmind_file = output_path / f"{input_file.stem}.xmind"
    try:
        export_to_xmind(testcases, str(xmind_file), module_name)
    except Exception as e:
        print(f"✗ XMind 导出失败: {e}")
    
    print()
    print("=" * 60)
    print("导出完成!")
    print(f"  Excel: {excel_file}")
    print(f"  XMind: {xmind_file}")
    print("=" * 60)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='一键导出 Markdown 测试用例为 Excel 和 XMind',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python export_all.py testcases.md
  python export_all.py testcases.md -o ./output
  python export_all.py testcases.md -m "购物车模块"
        """
    )
    
    parser.add_argument('input', help='输入 Markdown 文件路径')
    parser.add_argument('-o', '--output', help='输出目录（默认与输入文件同目录）')
    parser.add_argument('-m', '--module', default='测试用例', help='工作表/根主题名称')
    
    args = parser.parse_args()
    
    success = export_all(args.input, args.output, args.module)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
