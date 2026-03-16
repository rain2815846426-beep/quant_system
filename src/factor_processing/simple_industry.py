"""
简化行业数据（用于测试）

实际使用时应该从数据库加载真实行业数据
"""

# 简化行业分类（按股票代码前缀）
def get_simple_industry_map() -> dict:
    """
    获取简化行业映射
    
    基于股票代码前缀模拟行业分类
    """
    industries = {
        '600': '银行',
        '601': '保险',
        '603': '房地产',
        '605': '建筑材料',
        '000': '钢铁',
        '001': '有色金属',
        '002': '电子',
        '003': '计算机',
        '300': '医药生物',
        '301': '食品饮料',
        '302': '家用电器',
    }
    
    industry_map = {}
    
    # 为常见股票分配行业
    for prefix, industry in industries.items():
        for i in range(100):
            code = f"{prefix}{i:04d}"
            ts_code = f"{code}.SH" if code.startswith('6') else f"{code}.SZ"
            industry_map[ts_code] = industry
    
    return industry_map


if __name__ == "__main__":
    industry_map = get_simple_industry_map()
    print(f"简化行业数据：{len(industry_map)} 只股票")
    print(f"行业数量：{len(set(industry_map.values()))}")
