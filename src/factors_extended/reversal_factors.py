"""
反转因子 (10 个)

reversal_1, reversal_3, reversal_5
short_term_reversal, gap_reversal, overnight_return
intraday_reversal, high_low_reversal, volatility_reversal, drawdown_reversal
"""
import pandas as pd
import numpy as np
from .factor_factory import create_reversal_factor


def reversal_1(df: pd.DataFrame) -> pd.Series:
    """1 日反转"""
    return create_reversal_factor(df['close'], 1)


def reversal_3(df: pd.DataFrame) -> pd.Series:
    """3 日反转"""
    return create_reversal_factor(df['close'], 3)


def reversal_5(df: pd.DataFrame) -> pd.Series:
    """5 日反转"""
    return create_reversal_factor(df['close'], 5)


def short_term_reversal(df: pd.DataFrame) -> pd.Series:
    """短期反转（5 日负收益）"""
    returns = df['close'].pct_change(5)
    return -returns


def gap_reversal(df: pd.DataFrame) -> pd.Series:
    """跳空反转"""
    # 开盘与前收盘的差距
    gap = df['open'] - df['close'].shift(1)
    gap_return = gap / df['close'].shift(1)
    return -gap_return


def overnight_return(df: pd.DataFrame) -> pd.Series:
    """隔夜收益"""
    overnight = df['open'] - df['close'].shift(1)
    return overnight / df['close'].shift(1)


def intraday_reversal(df: pd.DataFrame) -> pd.Series:
    """日内反转"""
    # 收盘价与开盘价的差
    intraday = df['close'] - df['open']
    return -intraday / df['open']


def high_low_reversal(df: pd.DataFrame) -> pd.Series:
    """高低点反转"""
    # (最高 - 最低) / 收盘
    hl_range = df['high'] - df['low']
    return -hl_range / df['close']


def volatility_reversal(df: pd.DataFrame) -> pd.Series:
    """波动率反转"""
    # 负波动率
    returns = df['close'].pct_change()
    volatility = returns.rolling(20, min_periods=1).std()
    return -volatility


def drawdown_reversal(df: pd.DataFrame) -> pd.Series:
    """回撤反转"""
    # 从最高点的回撤
    rolling_max = df['close'].rolling(20, min_periods=1).max()
    drawdown = (df['close'] - rolling_max) / rolling_max
    return -drawdown
