"""
因子质量筛选模块

基于 IC 研究结果筛选优质因子
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


def filter_factors_by_ic(
    ic_results: pd.DataFrame,
    ic_mean_threshold: float = 0.02,
    ic_ir_threshold: float = 0.3,
    positive_rate_threshold: float = 0.55,
    top_n: int = 20
) -> List[str]:
    """
    基于 IC 筛选优质因子
    
    Args:
        ic_results: IC 结果 DataFrame
                   包含 columns: factor_name, ic_mean, ic_ir, positive_rate
        ic_mean_threshold: IC 均值阈值
        ic_ir_threshold: IC IR 阈值
        positive_rate_threshold: IC 为正的比例阈值
        top_n: 保留的因子数量
        
    Returns:
        筛选后的因子名称列表
        
    筛选规则：
    1. IC mean > 0.02
    2. IC IR > 0.3
    3. IC positive rate > 55%
    4. 按 IC IR 排序，保留 Top N
    """
    # 应用筛选规则
    filtered = ic_results[
        (ic_results['ic_mean'].abs() > ic_mean_threshold) &
        (ic_results['ic_ir'].abs() > ic_ir_threshold) &
        (ic_results['positive_rate'] > positive_rate_threshold)
    ].copy()
    
    if filtered.empty:
        # 如果没有满足条件的，放宽条件
        print("警告：没有因子满足所有条件，放宽条件...")
        filtered = ic_results.copy()
    
    # 按 IC IR 绝对值排序
    filtered['ic_ir_abs'] = filtered['ic_ir'].abs()
    filtered = filtered.sort_values('ic_ir_abs', ascending=False)
    
    # 保留 Top N
    top_factors = filtered.head(top_n)['factor_name'].tolist()
    
    return top_factors


def calculate_factor_ic_stats(
    factor_data: pd.DataFrame,
    forward_returns: pd.DataFrame
) -> pd.DataFrame:
    """
    计算各因子的 IC 统计
    
    Args:
        factor_data: 因子值 DataFrame (index: date, columns: factor_name)
        forward_returns: 未来收益 DataFrame
        
    Returns:
        IC 统计 DataFrame
    """
    ic_stats = []
    
    for factor_name in factor_data.columns:
        factor_series = factor_data[factor_name]
        
        # 计算 IC 时间序列
        ic_series = []
        for date in factor_series.index:
            if date not in forward_returns.index:
                continue
            
            factor_date = factor_series.loc[date].dropna()
            ret_date = forward_returns.loc[date].dropna()
            
            common = factor_date.index.intersection(ret_date.index)
            
            if len(common) < 30:
                continue
            
            ic = factor_date.loc[common].corr(ret_date.loc[common], method='pearson')
            if not np.isnan(ic):
                ic_series.append(ic)
        
        if not ic_series:
            continue
        
        ic_series = pd.Series(ic_series)
        
        # 统计指标
        stats = {
            'factor_name': factor_name,
            'ic_mean': ic_series.mean(),
            'ic_std': ic_series.std(),
            'ic_ir': ic_series.mean() / ic_series.std() if ic_series.std() > 1e-10 else 0,
            'ic_positive_rate': (ic_series > 0).sum() / len(ic_series),
            'ic_max': ic_series.max(),
            'ic_min': ic_series.min(),
            'n_periods': len(ic_series)
        }
        
        ic_stats.append(stats)
    
    return pd.DataFrame(ic_stats)


def factor_correlation_analysis(
    factor_data: pd.DataFrame,
    threshold: float = 0.8
) -> pd.DataFrame:
    """
    因子相关性分析
    
    Args:
        factor_data: 因子值 DataFrame
        threshold: 相关性阈值
        
    Returns:
        高相关性因子对
    """
    # 计算相关系数矩阵
    corr_matrix = factor_data.corr()
    
    # 找出高相关性因子对
    high_corr_pairs = []
    
    n_factors = len(corr_matrix.columns)
    for i in range(n_factors):
        for j in range(i + 1, n_factors):
            factor1 = corr_matrix.columns[i]
            factor2 = corr_matrix.columns[j]
            corr = corr_matrix.iloc[i, j]
            
            if abs(corr) > threshold:
                high_corr_pairs.append({
                    'factor1': factor1,
                    'factor2': factor2,
                    'correlation': corr
                })
    
    return pd.DataFrame(high_corr_pairs)
