"""
因子回测模块

实现分层回测，避免前视偏差
"""
import pandas as pd
import numpy as np
from typing import Dict


def factor_group_backtest(
    factor_values: pd.DataFrame,
    forward_returns: pd.DataFrame,
    n_groups: int = 5
) -> Dict:
    """
    因子分层回测
    
    Args:
        factor_values: 因子值（t 日）
        forward_returns: 未来收益（t 日因子对应的收益）
        n_groups: 分组数
        
    Returns:
        回测结果字典
    """
    # 计算各组收益
    group_returns = {}
    
    for i in range(n_groups):
        group_name = f'Q{i+1}'
        
        # 每日各组收益
        daily_returns = []
        dates = []
        
        common_dates = factor_values.index.intersection(forward_returns.index)
        
        for date in common_dates:
            factor_date = factor_values.loc[date]
            ret_date = forward_returns.loc[date]
            
            common = factor_date.index.intersection(ret_date.index)
            
            if len(common) < n_groups * 3:
                continue
            
            # 按因子值排序分组
            factor_sorted = factor_date.loc[common].dropna()
            ret_sorted = ret_date.loc[common].dropna()
            
            common2 = factor_sorted.index.intersection(ret_sorted.index)
            
            if len(common2) < n_groups * 3:
                continue
            
            # 分组
            try:
                quantiles = pd.qcut(factor_sorted.loc[common2], q=n_groups, labels=False)
                group_mask = quantiles == i
                
                if group_mask.sum() > 0:
                    group_ret = ret_sorted.loc[common2][group_mask].mean()
                    daily_returns.append(group_ret)
                    dates.append(date)
            except:
                continue
        
        if daily_returns:
            group_returns[group_name] = pd.Series(daily_returns, index=dates)
    
    # 计算累计收益
    cumulative = {}
    for name, returns in group_returns.items():
        cumulative[name] = (1 + returns).cumprod() - 1
    
    # 多空组合（Q5 - Q1 或 Qn_groups - Q1）
    if f'Q{n_groups}' in group_returns and 'Q1' in group_returns:
        common = group_returns[f'Q{n_groups}'].index.intersection(group_returns['Q1'].index)
        ls_returns = group_returns[f'Q{n_groups}'].loc[common] - group_returns['Q1'].loc[common]
        ls_cumulative = (1 + ls_returns).cumprod() - 1
        
        group_returns['Long_Short'] = ls_returns
        cumulative['Long_Short'] = ls_cumulative
    
    return {
        'daily_returns': pd.DataFrame(group_returns),
        'cumulative_returns': pd.DataFrame(cumulative)
    }


def calculate_group_statistics(backtest_result: Dict) -> pd.DataFrame:
    """
    计算各组统计指标
    
    Args:
        backtest_result: 回测结果
        
    Returns:
        统计指标 DataFrame
    """
    daily_returns = backtest_result['daily_returns']
    
    stats = {}
    
    for col in daily_returns.columns:
        returns = daily_returns[col].dropna()
        
        if len(returns) < 10:
            continue
        
        # 年化收益
        ann_return = returns.mean() * 252
        
        # 年化波动率
        ann_vol = returns.std() * np.sqrt(252)
        
        # 夏普比率
        sharpe = ann_return / ann_vol if ann_vol > 1e-10 else np.nan
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        stats[col] = {
            'annual_return': ann_return,
            'annual_vol': ann_vol,
            'sharpe': sharpe,
            'max_drawdown': max_dd
        }
    
    return pd.DataFrame(stats).T
