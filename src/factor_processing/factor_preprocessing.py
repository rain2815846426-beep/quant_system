"""
因子预处理

实现：
1. 去极值（MAD、Sigma、分位数）
2. 横截面标准化
"""
import pandas as pd
import numpy as np
from typing import Literal


def winsorize_mad(
    series: pd.Series,
    n_std: float = 3.0
) -> pd.Series:
    """
    MAD 去极值
    
    Args:
        series: 因子值序列
        n_std: 倍数（默认 3 倍 MAD）
        
    Returns:
        去极值后的序列
        
    方法：
    lower = median - n_std * MAD * 1.4826
    upper = median + n_std * MAD * 1.4826
    
    其中 MAD = median(|x - median|)
    1.4826 使 MAD 与标准差等价
    """
    median = series.median()
    mad = (series - median).abs().median()
    
    if mad == 0 or mad < 1e-10:
        return series
    
    lower = median - n_std * mad * 1.4826
    upper = median + n_std * mad * 1.4826
    
    return series.clip(lower=lower, upper=upper)


def winsorize_sigma(
    series: pd.Series,
    n_std: float = 3.0
) -> pd.Series:
    """
    标准差去极值
    
    Args:
        series: 因子值序列
        n_std: 倍数（默认 3 倍标准差）
        
    Returns:
        去极值后的序列
        
    方法：
    lower = mean - n_std * std
    upper = mean + n_std * std
    """
    mean = series.mean()
    std = series.std()
    
    if std == 0 or std < 1e-10:
        return series
    
    lower = mean - n_std * std
    upper = mean + n_std * std
    
    return series.clip(lower=lower, upper=upper)


def winsorize_quantile(
    series: pd.Series,
    lower_pct: float = 0.01,
    upper_pct: float = 0.99
) -> pd.Series:
    """
    分位数去极值
    
    Args:
        series: 因子值序列
        lower_pct: 下分位数（默认 1%）
        upper_pct: 上分位数（默认 99%）
        
    Returns:
        去极值后的序列
        
    方法：
    lower = quantile(lower_pct)
    upper = quantile(upper_pct)
    """
    lower = series.quantile(lower_pct)
    upper = series.quantile(upper_pct)
    
    return series.clip(lower=lower, upper=upper)


def zscore(
    series: pd.Series,
    use_median: bool = False
) -> pd.Series:
    """
    横截面标准化
    
    Args:
        series: 因子值序列
        use_median: 是否使用中位数代替均值
        
    Returns:
        标准化后的序列（均值 0，标准差 1）
        
    方法：
    z = (x - mean) / std
    """
    if series.empty:
        return series
    
    if use_median:
        median = series.median()
        mad = (series - median).abs().median()
        if mad == 0 or mad < 1e-10:
            return pd.Series(0, index=series.index)
        return (series - median) / (mad * 1.4826)
    else:
        mean = series.mean()
        std = series.std()
        
        if std == 0 or std < 1e-10:
            return pd.Series(0, index=series.index)
        
        return (series - mean) / std


def process_factor_cross_section(
    factor_series: pd.Series,
    winsorize_method: Literal['mad', 'sigma', 'quantile'] = 'mad',
    winsorize_nstd: float = 3.0,
    standardize: bool = True
) -> pd.Series:
    """
    完整的因子截面预处理流程
    
    Args:
        factor_series: 因子值（单交易日截面）
        winsorize_method: 去极值方法
        winsorize_nstd: 去极值倍数
        standardize: 是否标准化
        
    Returns:
        预处理后的因子值
        
    流程：
    1. 去极值
    2. 标准化
    """
    # 1. 去极值
    if winsorize_method == 'mad':
        factor_clean = winsorize_mad(factor_series, n_std=winsorize_nstd)
    elif winsorize_method == 'sigma':
        factor_clean = winsorize_sigma(factor_series, n_std=winsorize_nstd)
    elif winsorize_method == 'quantile':
        factor_clean = winsorize_quantile(factor_series)
    else:
        factor_clean = factor_series
    
    # 2. 标准化
    if standardize:
        factor_processed = zscore(factor_clean)
    else:
        factor_processed = factor_clean
    
    return factor_processed
