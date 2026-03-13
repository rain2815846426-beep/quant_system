"""
Alpha 算子实现

基于 WorldQuant 101 Formulaic Alphas 的核心算子
"""
import pandas as pd
import numpy as np
from typing import Union


def rank(x: pd.Series) -> pd.Series:
    """
    横截面排序（百分位）
    
    rank(x) = x / x.count()
    
    Args:
        x: 输入序列
        
    Returns:
        排序后的百分位序列
    """
    return x.rank(pct=True)


def cs_rank(x: pd.Series) -> pd.Series:
    """
    横截面排序（另一种实现）
    
    Args:
        x: 输入序列
        
    Returns:
        排序结果
    """
    return x.rank(pct=True)


def delay(x: pd.Series, d: int = 1) -> pd.Series:
    """
    延迟 d 天
    
    delay(x, d) = x.shift(d)
    
    Args:
        x: 输入序列
        d: 延迟天数
        
    Returns:
        延迟后的序列
    """
    return x.shift(d)


def delta(x: pd.Series, d: int = 1) -> pd.Series:
    """
    差分
    
    delta(x, d) = x - x.shift(d)
    
    Args:
        x: 输入序列
        d: 差分天数
        
    Returns:
        差分后的序列
    """
    return x - x.shift(d)


def ts_rank(x: pd.Series, d: int = 252) -> pd.Series:
    """
    时间序列排序
    
    ts_rank(x, d) = x.rolling(d).apply(lambda y: rank(y).iloc[-1])
    
    Args:
        x: 输入序列
        d: 滚动窗口
        
    Returns:
        时间序列排序结果
    """
    def _ts_rank_func(series):
        if len(series.dropna()) < 2:
            return np.nan
        return series.rank(pct=True).iloc[-1]
    
    return x.rolling(window=d, min_periods=1).apply(_ts_rank_func, raw=False)


def ts_max(x: pd.Series, d: int = 252) -> pd.Series:
    """
    时间序列最大值
    
    Args:
        x: 输入序列
        d: 滚动窗口
        
    Returns:
        滚动最大值
    """
    return x.rolling(window=d, min_periods=1).max()


def ts_min(x: pd.Series, d: int = 252) -> pd.Series:
    """
    时间序列最小值
    
    Args:
        x: 输入序列
        d: 滚动窗口
        
    Returns:
        滚动最小值
    """
    return x.rolling(window=d, min_periods=1).min()


def ts_mean(x: pd.Series, d: int = 252) -> pd.Series:
    """
    时间序列均值
    
    Args:
        x: 输入序列
        d: 滚动窗口
        
    Returns:
        滚动均值
    """
    return x.rolling(window=d, min_periods=1).mean()


def ts_stddev(x: pd.Series, d: int = 252) -> pd.Series:
    """
    时间序列标准差
    
    Args:
        x: 输入序列
        d: 滚动窗口
        
    Returns:
        滚动标准差
    """
    return x.rolling(window=d, min_periods=1).std()


def correlation(x: pd.Series, y: pd.Series, d: int = 252) -> pd.Series:
    """
    滚动相关系数
    
    Args:
        x: 输入序列 1
        y: 输入序列 2
        d: 滚动窗口
        
    Returns:
        滚动相关系数
    """
    return x.rolling(window=d, min_periods=1).corr(y)


def covariance(x: pd.Series, y: pd.Series, d: int = 252) -> pd.Series:
    """
    滚动协方差
    
    Args:
        x: 输入序列 1
        y: 输入序列 2
        d: 滚动窗口
        
    Returns:
        滚动协方差
    """
    return x.rolling(window=d, min_periods=1).cov(y)


def decay_linear(x: pd.Series, d: int = 10) -> pd.Series:
    """
    线性衰减加权
    
    decay_linear(x, d) = WMA(x, d)
    权重：d, d-1, d-2, ..., 1
    
    Args:
        x: 输入序列
        d: 窗口长度
        
    Returns:
        线性衰减加权值
    """
    weights = np.arange(1, d + 1)
    
    def _weighted_mean(series):
        if len(series) < d:
            return np.nan
        return np.average(series, weights=weights)
    
    return x.rolling(window=d, min_periods=d).apply(_weighted_mean, raw=False)


def scale(x: pd.Series, target: float = 1.0) -> pd.Series:
    """
    归一化
    
    scale(x) = x * target / sum(|x|)
    
    Args:
        x: 输入序列
        target: 目标缩放值
        
    Returns:
        归一化后的序列
    """
    return x * target / x.abs().sum()


def signed_power(x: pd.Series, a: float = 1.0) -> pd.Series:
    """
    带符号幂运算
    
    signed_power(x, a) = sign(x) * |x|^a
    
    Args:
        x: 输入序列
        a: 幂次
        
    Returns:
        带符号幂运算结果
    """
    return np.sign(x) * np.power(np.abs(x), a)


def abs_value(x: pd.Series) -> pd.Series:
    """
    绝对值
    
    Args:
        x: 输入序列
        
    Returns:
        绝对值
    """
    return x.abs()


def log_value(x: pd.Series) -> pd.Series:
    """
    对数
    
    Args:
        x: 输入序列
        
    Returns:
        对数值
    """
    return np.log(x)


def indicator(x: pd.Series) -> pd.Series:
    """
    指示函数
    
    indicator(x) = 1 if x > 0 else 0
    
    Args:
        x: 输入序列
        
    Returns:
        指示函数结果
    """
    return (x > 0).astype(int)


def cs_neutralize(x: pd.Series, group: pd.Series = None) -> pd.Series:
    """
    行业中性化
    
    Args:
        x: 因子值
        group: 行业分组
        
    Returns:
        中性化后的因子
    """
    if group is not None:
        # 行业内标准化
        return x.groupby(group).transform(lambda s: (s - s.mean()) / s.std())
    else:
        # 整体标准化
        return (x - x.mean()) / x.std()


# 常用组合算子
def high_minus_low(high: pd.Series, low: pd.Series) -> pd.Series:
    """最高价 - 最低价"""
    return high - low


def high_minus_close(high: pd.Series, close: pd.Series) -> pd.Series:
    """最高价 - 收盘价"""
    return high - close


def close_minus_open(close: pd.Series, open_p: pd.Series) -> pd.Series:
    """收盘价 - 开盘价"""
    return close - open_p


def vwap_approx(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    近似 VWAP 计算
    
    VWAP = (high + low + close) / 3 * volume
    """
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()
