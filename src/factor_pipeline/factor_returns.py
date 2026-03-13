"""
因子收益分析模块

关键设计（避免前视偏差）：
1. t 日的因子值只能用于预测 t+1 及以后的收益
2. IC 计算必须是截面的、时序正确的
3. 不使用任何未来数据
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple


def calculate_forward_returns(
    close_prices: pd.DataFrame,
    periods: List[int] = [1, 5, 10, 20]
) -> Dict[int, pd.DataFrame]:
    """
    计算未来收益（正确的时间对齐）
    
    Args:
        close_prices: 收盘价 DataFrame (index: trade_date, columns: ts_code)
        periods: 预测周期列表
        
    Returns:
        Dict[period -> forward_returns DataFrame]
        
    注意：
    - forward_return[t, period] = (price[t+period] - price[t]) / price[t]
    - 使用 shift 确保不使用未来数据
    """
    forward_returns = {}
    
    for period in periods:
        # 正确的未来收益计算
        # t 日的未来收益 = (t+period 日的价格 - t 日的价格) / t 日的价格
        returns = close_prices.shift(-period) / close_prices - 1
        forward_returns[period] = returns
    
    return forward_returns


def calculate_ic_time_series(
    factor_values: pd.DataFrame,
    forward_returns: pd.DataFrame,
    method: str = 'pearson'
) -> pd.Series:
    """
    计算 IC 时间序列（正确的截面 IC）
    
    Args:
        factor_values: 因子值 DataFrame (index: trade_date, columns: ts_code)
                       这是 t 日的因子值
        forward_returns: 未来收益 DataFrame (index: trade_date, columns: ts_code)
                        这是 t 日因子对应的未来收益
        method: 'pearson' 或 'spearman'
        
    Returns:
        IC 时间序列（每个交易日一个 IC 值）
        
    关键：
    - factor_values 的 index 是 t 日
    - forward_returns 的 index 也应该是 t 日（表示 t 日因子预测的未来收益）
    - 每个交易日的 IC 是该日截面上因子值与未来收益的相关性
    """
    ic_series = []
    ic_dates = []
    
    # 对齐日期
    common_dates = factor_values.index.intersection(forward_returns.index)
    
    for date in common_dates:
        factor_date = factor_values.loc[date]
        ret_date = forward_returns.loc[date]
        
        # 对齐股票
        common_stocks = factor_date.index.intersection(ret_date.index)
        
        if len(common_stocks) < 30:  # 至少 30 个样本
            continue
        
        factor_clean = factor_date.loc[common_stocks].dropna()
        ret_clean = ret_date.loc[common_stocks].dropna()
        
        # 共同非空
        common = factor_clean.index.intersection(ret_clean.index)
        
        if len(common) < 30:
            continue
        
        # 去极值
        f = factor_clean.loc[common]
        r = ret_clean.loc[common]
        
        f_clean = f.clip(f.mean() - 3*f.std(), f.mean() + 3*f.std())
        r_clean = r.clip(r.mean() - 3*r.std(), r.mean() + 3*r.std())
        
        # 计算相关性
        if method == 'pearson':
            ic = f_clean.corr(r_clean, method='pearson')
        elif method == 'spearman':
            ic = f_clean.corr(r_clean, method='spearman')
        else:
            ic = np.nan
        
        if not np.isnan(ic):
            ic_series.append(ic)
            ic_dates.append(date)
    
    return pd.Series(ic_series, index=ic_dates, name=f'IC_{method}')


def calculate_ic_statistics(ic_series: pd.Series) -> Dict:
    """
    计算 IC 统计指标
    
    Args:
        ic_series: IC 时间序列
        
    Returns:
        IC 统计指标字典
    """
    ic_clean = ic_series.dropna()
    
    if len(ic_clean) < 10:
        return {
            'ic_mean': np.nan,
            'ic_std': np.nan,
            'ic_ir': np.nan,
            'ic_tstat': np.nan,
            'ic_pvalue': np.nan,
            'n_periods': len(ic_clean)
        }
    
    ic_mean = ic_clean.mean()
    ic_std = ic_clean.std()
    ic_ir = ic_mean / ic_std if ic_std > 1e-10 else np.nan
    
    # T 检验
    ic_tstat = ic_mean / (ic_std / np.sqrt(len(ic_clean))) if ic_std > 1e-10 else np.nan
    ic_pvalue = 2 * (1 - stats.t.cdf(abs(ic_tstat), len(ic_clean) - 1))
    
    return {
        'ic_mean': ic_mean,
        'ic_std': ic_std,
        'ic_ir': ic_ir,
        'ic_tstat': ic_tstat,
        'ic_pvalue': ic_pvalue,
        'n_periods': len(ic_clean)
    }


def calculate_factor_returns(
    factor_values: pd.DataFrame,
    forward_returns: pd.DataFrame,
    n_groups: int = 5
) -> pd.DataFrame:
    """
    计算因子收益（分层法，避免前视偏差）
    
    Args:
        factor_values: 因子值 DataFrame (index: trade_date, columns: ts_code)
        forward_returns: 未来收益 DataFrame
        n_groups: 分组数量
        
    Returns:
        各组收益时间序列
    """
    group_returns = {f'Q{i+1}': [] for i in range(n_groups)}
    dates = []
    
    common_dates = factor_values.index.intersection(forward_returns.index)
    
    for date in common_dates:
        factor_date = factor_values.loc[date]
        ret_date = forward_returns.loc[date]
        
        # 对齐股票
        common_stocks = factor_date.index.intersection(ret_date.index)
        
        if len(common_stocks) < n_groups * 5:  # 每组至少 5 个样本
            continue
        
        factor_clean = factor_date.loc[common_stocks].dropna()
        ret_clean = ret_date.loc[common_stocks].dropna()
        
        common = factor_clean.index.intersection(ret_clean.index)
        
        if len(common) < n_groups * 5:
            continue
        
        # 按因子值分组
        factor_vals = factor_clean.loc[common]
        returns_vals = ret_clean.loc[common]
        
        # 分组（使用分位数）
        try:
            groups = pd.qcut(factor_vals, q=n_groups, labels=False, duplicates='drop')
        except ValueError:
            # 分位数失败，使用排名
            groups = pd.cut(factor_vals.rank(pct=True), bins=n_groups, labels=False)
        
        # 计算各组平均收益
        valid = True
        for g in range(n_groups):
            group_mask = groups == g
            if group_mask.sum() > 0:
                group_ret = returns_vals[group_mask].mean()
                group_returns[f'Q{g+1}'].append(group_ret)
            else:
                valid = False
                break
        
        if valid:
            dates.append(date)
    
    # 转换为 DataFrame
    result = pd.DataFrame({
        key: pd.Series(values, index=dates)
        for key, values in group_returns.items()
    })
    
    return result


def calculate_long_short_returns(
    factor_values: pd.DataFrame,
    forward_returns: pd.DataFrame,
    top_pct: float = 0.2,
    bottom_pct: float = 0.2
) -> pd.Series:
    """
    计算多空收益（Long-Short Portfolio）
    
    Args:
        factor_values: 因子值 DataFrame
        forward_returns: 未来收益 DataFrame
        top_pct: 多头比例
        bottom_pct: 空头比例
        
    Returns:
        多空收益时间序列（Long - Short）
    """
    ls_returns = []
    dates = []
    
    common_dates = factor_values.index.intersection(forward_returns.index)
    
    for date in common_dates:
        factor_date = factor_values.loc[date]
        ret_date = forward_returns.loc[date]
        
        common_stocks = factor_date.index.intersection(ret_date.index)
        
        if len(common_stocks) < 10:
            continue
        
        factor_clean = factor_date.loc[common_stocks].dropna()
        ret_clean = ret_date.loc[common_stocks].dropna()
        
        common = factor_clean.index.intersection(ret_clean.index)
        
        if len(common) < 10:
            continue
        
        factor_vals = factor_clean.loc[common]
        returns_vals = ret_clean.loc[common]
        
        # 多头：因子值最高的 top_pct
        n_top = max(1, int(len(factor_vals) * top_pct))
        top_stocks = factor_vals.nlargest(n_top).index
        long_ret = returns_vals.loc[top_stocks].mean()
        
        # 空头：因子值最低的 bottom_pct
        n_bottom = max(1, int(len(factor_vals) * bottom_pct))
        bottom_stocks = factor_vals.nsmallest(n_bottom).index
        short_ret = returns_vals.loc[bottom_stocks].mean()
        
        # 多空收益
        ls_ret = long_ret - short_ret
        ls_returns.append(ls_ret)
        dates.append(date)
    
    return pd.Series(ls_returns, index=dates, name='Long_Short_Return')
