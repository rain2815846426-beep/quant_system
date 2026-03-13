"""
成交量因子 (10 个)

volume_ratio, volume_change, volume_spike, volume_rank_20, volume_mean_ratio
turnover_rate, turnover_change, adv20_ratio, volume_volatility, volume_price_corr
"""
import pandas as pd
import numpy as np
from .factor_factory import create_ratio_factor, create_correlation_factor


def volume_ratio(df: pd.DataFrame) -> pd.Series:
    """成交量比率（当日/5 日均）"""
    return df['volume'] / df['volume'].rolling(5, min_periods=1).mean()


def volume_change(df: pd.DataFrame) -> pd.Series:
    """成交量变化"""
    return df['volume'].pct_change()


def volume_spike(df: pd.DataFrame) -> pd.Series:
    """成交量突增"""
    vol_mean = df['volume'].rolling(20, min_periods=1).mean()
    vol_std = df['volume'].rolling(20, min_periods=1).std()
    return (df['volume'] - vol_mean) / vol_std


def volume_rank_20(df: pd.DataFrame) -> pd.Series:
    """20 日成交量排名"""
    return df['volume'].rolling(20, min_periods=1).apply(lambda x: x.rank(pct=True).iloc[-1], raw=False)


def volume_mean_ratio(df: pd.DataFrame) -> pd.Series:
    """成交量均值比（5 日/20 日）"""
    vol_5 = df['volume'].rolling(5, min_periods=1).mean()
    vol_20 = df['volume'].rolling(20, min_periods=1).mean()
    return vol_5 / vol_20


def turnover_rate(df: pd.DataFrame) -> pd.Series:
    """换手率（成交量/流通股本，简化为成交量比率）"""
    return df['volume'] / df['volume'].rolling(252, min_periods=1).mean()


def turnover_change(df: pd.DataFrame) -> pd.Series:
    """换手率变化"""
    turnover = df['volume'] / df['volume'].rolling(252, min_periods=1).mean()
    return turnover.pct_change()


def adv20_ratio(df: pd.DataFrame) -> pd.Series:
    """20 日平均成交量比率"""
    adv20 = df['volume'].rolling(20, min_periods=1).mean()
    return df['volume'] / adv20


def volume_volatility(df: pd.DataFrame) -> pd.Series:
    """成交量波动率"""
    vol_change = df['volume'].pct_change()
    return vol_change.rolling(20, min_periods=1).std()


def volume_price_corr(df: pd.DataFrame) -> pd.Series:
    """量价相关性"""
    return df['volume'].rolling(20, min_periods=1).corr(df['close'])
