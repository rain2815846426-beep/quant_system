"""
换手率分析模块

计算组合换手率和交易成本
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple


def calculate_daily_turnover(
    weights_prev: pd.Series,
    weights_curr: pd.Series,
    returns: pd.Series
) -> float:
    """
    计算单日换手率
    
    Args:
        weights_prev: 前一日权重
        weights_curr: 当日权重（调仓前）
        returns: 当日收益
        
    Returns:
        换手率
    """
    # 计算调仓前的权重（考虑收益变化）
    weights_before_rebalance = weights_prev * (1 + returns)
    
    # 归一化
    weights_before_rebalance = weights_before_rebalance / weights_before_rebalance.sum()
    
    # 换手率 = 0.5 * sum(|w_curr - w_before|)
    turnover = 0.5 * (weights_curr - weights_before_rebalance).abs().sum()
    
    return turnover


def calculate_portfolio_turnover(
    weights_history: pd.DataFrame,
    returns: pd.Series
) -> pd.Series:
    """
    计算组合历史换手率
    
    Args:
        weights_history: 权重历史（index: date, columns: stocks）
        returns: 收益序列
        
    Returns:
        每日换手率
    """
    daily_turnover = []
    dates = weights_history.index
    
    for i in range(1, len(dates)):
        prev_date = dates[i-1]
        curr_date = dates[i]
        
        weights_prev = weights_history.loc[prev_date]
        weights_curr = weights_history.loc[curr_date]
        
        # 获取当日收益
        if curr_date in returns.index:
            ret = returns.loc[curr_date]
        else:
            ret = pd.Series(0, index=weights_prev.index)
        
        turnover = calculate_daily_turnover(weights_prev, weights_curr, ret)
        daily_turnover.append(turnover)
    
    return pd.Series(daily_turnover, index=dates[1:])


def calculate_turnover_statistics(turnover_series: pd.Series) -> Dict:
    """
    换手率统计
    
    Args:
        turnover_series: 换手率时间序列
        
    Returns:
        统计指标字典
    """
    return {
        'daily_mean': turnover_series.mean(),
        'daily_std': turnover_series.std(),
        'annual_turnover': turnover_series.mean() * 252,
        'monthly_mean': turnover_series.rolling(20).mean().mean(),
        'max_daily': turnover_series.max(),
        'min_daily': turnover_series.min()
    }
