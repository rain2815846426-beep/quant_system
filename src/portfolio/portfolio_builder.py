"""
组合构建模块

实现多种组合构建方法
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


def build_long_short_portfolio(
    factor_values: pd.Series,
    top_pct: float = 0.1,
    bottom_pct: float = 0.1
) -> pd.Series:
    """
    构建多空组合
    
    Args:
        factor_values: 因子值（截面）
        top_pct: 多头比例
        bottom_pct: 空头比例
        
    Returns:
        权重 Series（long 为正，short 为负）
    """
    n_stocks = len(factor_values)
    n_long = max(1, int(n_stocks * top_pct))
    n_short = max(1, int(n_stocks * bottom_pct))
    
    # 排序
    factor_sorted = factor_values.sort_values(ascending=False)
    
    # 多头：因子值最高的 top_pct
    long_stocks = factor_sorted.head(n_long).index
    long_weight = 1.0 / n_long
    
    # 空头：因子值最低的 bottom_pct
    short_stocks = factor_sorted.tail(n_short).index
    short_weight = -1.0 / n_short
    
    # 构建权重
    weights = pd.Series(0, index=factor_values.index)
    weights.loc[long_stocks] = long_weight
    weights.loc[short_stocks] = short_weight
    
    return weights


def build_long_only_portfolio(
    factor_values: pd.Series,
    top_pct: float = 0.2
) -> pd.Series:
    """
    构建纯多头组合
    
    Args:
        factor_values: 因子值
        top_pct: 选股比例
        
    Returns:
        权重 Series
    """
    n_stocks = len(factor_values)
    n_select = max(1, int(n_stocks * top_pct))
    
    # 排序选股
    factor_sorted = factor_values.sort_values(ascending=False)
    selected_stocks = factor_sorted.head(n_select).index
    
    # 等权
    weight = 1.0 / n_select
    weights = pd.Series(0, index=factor_values.index)
    weights.loc[selected_stocks] = weight
    
    return weights


def build_ic_weighted_portfolio(
    factor_values: pd.DataFrame,
    ic_scores: Dict[str, float]
) -> pd.Series:
    """
    构建 IC 加权多因子组合
    
    Args:
        factor_values: 多因子值 DataFrame
        ic_scores: 各因子 IC_IR 分数
        
    Returns:
        组合权重
    """
    # 计算 IC 权重
    weights_dict = {}
    total_ic = 0
    
    for factor_name, ic in ic_scores.items():
        if factor_name in factor_values.columns:
            abs_ic = abs(ic)
            weights_dict[factor_name] = abs_ic
            total_ic += abs_ic
    
    if total_ic == 0:
        # 如果 IC 都为 0，使用等权
        return factor_values.mean(axis=1)
    
    # 归一化
    for name in weights_dict:
        weights_dict[name] /= total_ic
    
    # 加权合成因子
    combined_factor = pd.Series(0, index=factor_values.index)
    for factor_name, weight in weights_dict.items():
        combined_factor += factor_values[factor_name] * weight
    
    return combined_factor


def calculate_portfolio_returns(
    weights: pd.DataFrame,
    stock_returns: pd.DataFrame
) -> pd.Series:
    """
    计算组合收益
    
    Args:
        weights: 权重 DataFrame (index: date, columns: stocks)
        stock_returns: 个股收益 DataFrame
        
    Returns:
        组合收益时间序列
    """
    # 对齐日期和股票
    common_dates = weights.index.intersection(stock_returns.index)
    
    portfolio_returns = []
    
    for date in common_dates:
        w = weights.loc[date]
        ret = stock_returns.loc[date]
        
        # 对齐股票
        common_stocks = w.index.intersection(ret.index)
        
        if len(common_stocks) > 0:
            port_ret = (w.loc[common_stocks] * ret.loc[common_stocks]).sum()
            portfolio_returns.append(port_ret)
        else:
            portfolio_returns.append(np.nan)
    
    return pd.Series(portfolio_returns, index=common_dates)
