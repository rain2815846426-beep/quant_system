"""
行业中性化模块

目的：
- 去除因子在行业上的暴露
- 避免因子值集中在某些行业
- 降低过拟合风险

方法：
1. 行业内标准化
2. 回归残差法
3. 行业权重约束

使用：
    from src.factor_processing.industry_neutralization import IndustryNeutralizer
    
    neutralizer = IndustryNeutralizer(industry_map)
    neutralized_factor = neutralizer.neutralize(factor_values, date)
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from pathlib import Path
import sys

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


class IndustryNeutralizer:
    """
    行业中性化器
    
    提供三种中性化方法：
    1. 行业内标准化
    2. 回归残差法
    3. 行业权重约束
    """
    
    def __init__(
        self,
        industry_map: Dict[str, str],
        method: str = 'regression'
    ):
        """
        初始化
        
        Args:
            industry_map: {ts_code: industry_name}
            method: 'within_industry' / 'regression' / 'weight_constraint'
        """
        self.industry_map = industry_map
        self.method = method
        
        # 反向映射：行业 → 股票列表
        self.industry_stocks = {}
        for ts_code, industry in industry_map.items():
            if industry not in self.industry_stocks:
                self.industry_stocks[industry] = []
            self.industry_stocks[industry].append(ts_code)
    
    def neutralize(
        self,
        factor_values: pd.Series,
        date: Optional[str] = None
    ) -> pd.Series:
        """
        执行行业中性化
        
        Args:
            factor_values: 因子值 Series (index: ts_code)
            date: 交易日期（可选）
            
        Returns:
            中性化后的因子值
        """
        if self.method == 'within_industry':
            return self._within_industry_standardize(factor_values)
        elif self.method == 'regression':
            return self._regression_residual(factor_values)
        elif self.method == 'weight_constraint':
            return self._weight_constraint(factor_values)
        else:
            raise ValueError(f"未知方法：{self.method}")
    
    def _within_industry_standardize(
        self,
        factor_values: pd.Series
    ) -> pd.Series:
        """
        行业内标准化
        
        方法：
        对每个行业内的因子值进行标准化
        z = (x - mean_industry) / std_industry
        
        优点：
        - 简单快速
        - 完全去除行业影响
        
        缺点：
        - 可能改变因子排序
        """
        result = factor_values.copy()
        
        for industry, stocks in self.industry_stocks.items():
            # 获取行业内股票
            industry_stocks = [s for s in stocks if s in factor_values.index]
            
            if len(industry_stocks) < 3:
                continue
            
            # 行业内因子值
            industry_factor = factor_values.loc[industry_stocks]
            
            # 标准化
            mean = industry_factor.mean()
            std = industry_factor.std()
            
            if std > 1e-10:
                result.loc[industry_stocks] = (industry_factor - mean) / std
            else:
                result.loc[industry_stocks] = 0
        
        return result
    
    def _regression_residual(
        self,
        factor_values: pd.Series
    ) -> pd.Series:
        """
        回归残差法
        
        方法：
        factor = β0 + β1*industry_dummies + ε
        返回：ε
        
        优点：
        - 保留因子原始信息
        - 只去除行业相关部分
        
        缺点：
        - 计算较慢
        """
        # 构建回归数据
        valid_stocks = [s for s in factor_values.index if s in self.industry_map]
        
        if len(valid_stocks) < 10:
            return factor_values
        
        y = factor_values.loc[valid_stocks].values
        
        # 行业虚拟变量
        industries = [self.industry_map[s] for s in valid_stocks]
        unique_industries = list(set(industries))
        
        if len(unique_industries) < 2:
            return factor_values
        
        # 构建设计矩阵（去掉一个行业作为基准）
        n = len(valid_stocks)
        k = len(unique_industries) - 1
        
        X = np.ones((n, k + 1))  # 截距 + k-1 个行业
        
        for i, (stock, ind) in enumerate(zip(valid_stocks, industries)):
            if ind != unique_industries[0]:  # 基准行业
                col_idx = unique_industries.index(ind)
                if col_idx > 0:
                    X[i, col_idx] = 1
        
        # OLS 回归
        try:
            # 使用正规方程
            XtX = X.T @ X
            reg = 1e-8 * np.eye(XtX.shape[0])  # 正则化
            beta = np.linalg.solve(XtX + reg, X.T @ y)
            
            # 计算残差
            y_pred = X @ beta
            residuals = y - y_pred
            
            # 返回残差
            result = factor_values.copy()
            result.loc[valid_stocks] = residuals
            
            return result
            
        except Exception as e:
            print(f"  回归失败：{e}，返回原因子")
            return factor_values
    
    def _weight_constraint(
        self,
        factor_values: pd.Series,
        max_industry_weight: float = 0.3
    ) -> pd.Series:
        """
        行业权重约束
        
        方法：
        限制每个行业在选股中的权重
        
        优点：
        - 灵活控制行业暴露
        - 保留部分行业信息
        
        缺点：
        - 需要调整参数
        """
        # 按因子值排序
        sorted_factors = factor_values.sort_values(ascending=False)
        
        # 记录已选股票和行业权重
        selected = []
        industry_count = {}
        total_selected = 0
        
        for ts_code in sorted_factors.index:
            industry = self.industry_map.get(ts_code, 'unknown')
            
            # 检查行业权重
            current_weight = industry_count.get(industry, 0) / (total_selected + 1e-10)
            
            if current_weight < max_industry_weight:
                selected.append(ts_code)
                industry_count[industry] = industry_count.get(industry, 0) + 1
                total_selected += 1
        
        # 返回选中的股票（保持原始因子值）
        result = pd.Series(0, index=factor_values.index)
        result.loc[selected] = factor_values.loc[selected]
        
        return result


def get_industry_data(db_path=DATABASE_PATH) -> Dict[str, str]:
    """
    从数据库加载行业数据
    
    Returns:
        {ts_code: industry_name}
    """
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query("""
            SELECT DISTINCT ts_code, industry_name
            FROM industry_classification
        """, conn)
    
    if df.empty:
        print("  ⚠️  行业数据为空，需要下载行业分类数据")
        return {}
    
    return dict(zip(df['ts_code'], df['industry_name']))


def test_industry_neutralization():
    """测试行业中性化"""
    print("="*70)
    print("行业中性化测试")
    print("="*70)
    
    # 加载行业数据
    print("\n[1/4] 加载行业数据...")
    industry_map = get_industry_data()
    
    if not industry_map:
        print("  ❌ 行业数据为空，跳过测试")
        return
    
    print(f"  行业数据：{len(industry_map)} 只股票")
    print(f"  行业数量：{len(set(industry_map.values()))}")
    
    # 创建模拟因子
    print("\n[2/4] 创建模拟因子...")
    np.random.seed(42)
    
    stocks = list(industry_map.keys())[:500]
    factor_values = pd.Series(
        np.random.randn(len(stocks)),
        index=stocks
    )
    
    # 添加行业效应（某些行业因子值偏高）
    for ts_code in stocks:
        industry = industry_map.get(ts_code, '')
        if 'technology' in industry.lower() or '科技' in industry:
            factor_values[ts_code] += 1.0
        elif 'finance' in industry.lower() or '金融' in industry:
            factor_values[ts_code] -= 0.5
    
    print(f"  因子数量：{len(factor_values)}")
    
    # 测试不同方法
    print("\n[3/4] 测试中性化方法...")
    
    methods = ['within_industry', 'regression', 'weight_constraint']
    
    for method in methods:
        print(f"\n  方法：{method}")
        neutralizer = IndustryNeutralizer(industry_map, method=method)
        
        neutralized = neutralizer.neutralize(factor_values)
        
        # 计算行业相关性
        print(f"    中性化前均值：{factor_values.mean():.4f}")
        print(f"    中性化后均值：{neutralized.mean():.4f}")
        print(f"    中性化前标准差：{factor_values.std():.4f}")
        print(f"    中性化后标准差：{neutralized.std():.4f}")
    
    # 详细测试回归法
    print("\n[4/4] 回归法详细测试...")
    neutralizer = IndustryNeutralizer(industry_map, method='regression')
    neutralized = neutralizer.neutralize(factor_values)
    
    # 检查行业内相关性
    print("\n  行业内因子相关性（中性化后应降低）:")
    for industry in list(industry_map.values())[:5]:
        industry_stocks = [s for s in stocks if industry_map.get(s) == industry]
        
        if len(industry_stocks) >= 3:
            orig_corr = factor_values.loc[industry_stocks].std()
            neut_corr = neutralized.loc[industry_stocks].std()
            
            print(f"    {industry}: {orig_corr:.4f} → {neut_corr:.4f}")
    
    print("\n" + "="*70)
    print("行业中性化测试完成！")
    print("="*70)


if __name__ == "__main__":
    test_industry_neutralization()
