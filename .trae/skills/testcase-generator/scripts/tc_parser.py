"""
测试用例 Markdown 解析器
从 Markdown 文件中提取结构化测试用例数据
"""
import re
from typing import List, Dict


def parse_testcase_markdown(md_content: str) -> List[Dict[str, str]]:
    """
    解析 Markdown 格式的测试用例表格
    
    Args:
        md_content: Markdown 文件内容
        
    Returns:
        测试用例字典列表，每个字典包含用例的所有字段
    """
    testcases = []
    
    # 匹配表格行（以 | 开头和结尾）
    lines = md_content.split('\n')
    table_lines = [line.strip() for line in lines if line.strip().startswith('|')]
    
    if len(table_lines) < 2:
        return testcases
    
    # 提取表头
    header_line = table_lines[0]
    headers = [cell.strip() for cell in header_line.split('|')[1:-1]]
    
    # 跳过分隔行（第二行通常是 ---）
    start_idx = 1
    if len(table_lines) > 1 and '---' in table_lines[1]:
        start_idx = 2
    
    # 解析数据行
    for line in table_lines[start_idx:]:
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if len(cells) == len(headers):
            testcase = dict(zip(headers, cells))
            testcases.append(testcase)
    
    return testcases


def extract_module_from_filename(filename: str) -> str:
    """
    从文件名提取模块名
    例如: TC_CART_001.md -> CART
    """
    match = re.search(r'TC_([A-Z]+)_\d+', filename)
    return match.group(1) if match else 'UNKNOWN'


if __name__ == '__main__':
    # 测试示例
    sample_md = """
| 用例编号 | 所属模块 | 用例标题 | 用例类型 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |
|---------|---------|---------|---------|-------|---------|---------|---------|
| TC_CART_001 | 购物车 | 添加商品到购物车 | 功能测试 | P0 | 用户已登录 | 1. 点击商品详情<br>2. 点击"加入购物车" | 商品成功添加到购物车，数量+1 |
| TC_CART_002 | 购物车 | 未登录添加购物车 | 异常测试 | P1 | 用户未登录 | 1. 点击"加入购物车" | 提示"请先登录" |
"""
    result = parse_testcase_markdown(sample_md)
    print(f"解析到 {len(result)} 条测试用例")
    for tc in result:
        print(tc)
