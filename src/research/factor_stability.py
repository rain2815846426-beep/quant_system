"""
因子稳定性分析模块

关键：分析因子 IC 的时间稳定性
"""
import pandas as pd
import numpy as np
from typing import Dict, List


def calculate_rolling_ic(
    ic_series: pd.Series,
    windows: List[int] = [60, 120, 252]
) -> Dict[int, pd.Series]:
    """
    计算 Rolling IC
    
    Args:
        ic_series: IC 时间序列
        windows: 滚动窗口（交易日）
        
    Returns:
        Dict[window -> rolling_ic_series]
    """
    rolling_ic = {}
    
    for window in windows:
        rolling_ic[window] = ic_series.rolling(window, min_periods=window//2).mean()
    
    return rolling_ic


def calculate_ic_yearly_breakdown(ic_series: pd.Series) -> pd.DataFrame:
    """
    IC 年度分解
    
    Args:
        ic_series: IC 时间序列（index 为日期）
        
    Returns:
        年度 IC 统计 DataFrame
    """
    # 按年分组
    ic_by_year = ic_series.groupby(ic_series.index.year).agg([
        'mean', 'std', 'min', 'max', 'count'
    ])
    
    # 计算 IR
    ic_by_year['ir'] = ic_by_year['mean'] / ic_by_year['std']
    
    # 胜率（IC>0 的比例）
    yearly_win_rate = ic_series.groupby(ic_series.index.year).apply(
        lambda x: (x > 0).sum() / len(x)
    )
    
    ic_by_year['win_rate'] = yearly_win_rate
    
    return ic_by_year


def calculate_ic_quarterly(ic_series: pd.Series) -> pd.DataFrame:
    """
    IC 季度分解
    
    Args:
        ic_series: IC 时间序列
        
    Returns:
        季度 IC 统计 DataFrame
    """
    # 按年 - 季度分组
    ic_by_quarter = ic_series.groupby([
        ic_series.index.year,
        ic_series.index.quarter
    ]).agg(['mean', 'std', 'count'])
    
    ic_by_quarter['ir'] = ic_by_quarter[('mean', '')] / ic_by_quarter[('std', '')]
    
    return ic_by_quarter


def factor_stability_analysis(ic_series: pd.Series) -> Dict:
    """
    完整的因子稳定性分析
    
    Args:
        ic_series: IC 时间序列
        
    Returns:
        分析结果字典
    """
    results = {}
    
    # 1. Rolling IC
    results['rolling_ic'] = calculate_rolling_ic(ic_series, windows=[60, 120, 252])
    
    # 2. 年度分解
    results['yearly_breakdown'] = calculate_ic_yearly_breakdown(ic_series)
    
    # 3. 季度分解
    results['quarterly_breakdown'] = calculate_ic_quarterly(ic_series)
    
    # 4. 稳定性指标
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    
    # IC 变异系数（越小越稳定）
    ic_cv = ic_std / abs(ic_mean) if abs(ic_mean) > 1e-10 else np.inf
    
    # 胜率
    win_rate = (ic_series > 0).sum() / len(ic_series)
    
    results['stability_metrics'] = {
        'ic_mean': ic_mean,
        'ic_std': ic_std,
        'ic_cv': ic_cv,
        'win_rate': win_rate,
        'n_periods': len(ic_series)
    }
    
    return results


def save_stability_report(
    stability_results: Dict,
    output_path: str
):
    """
    保存稳定性报告
    
    Args:
        stability_results: 稳定性分析结果
        output_path: 输出路径
    """
    # 年度分解
    yearly_df = stability_results['yearly_breakdown']
    yearly_df.to_csv(output_path.replace('.csv', '_yearly.csv'))
    
    # 季度分解
    quarterly_df = stability_results['quarterly_breakdown']
    quarterly_df.to_csv(output_path.replace('.csv', '_quarterly.csv'))
    
    # 稳定性指标
    metrics = stability_results['stability_metrics']
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(output_path, index=False)
    
    print(f"稳定性报告已保存：{output_path}")
