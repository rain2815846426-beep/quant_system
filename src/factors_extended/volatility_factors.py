"""
波动率因子 (10 个)

realized_volatility, downside_volatility, upside_volatility, atr, price_range
high_low_ratio, volatility_5, volatility_10, volatility_20, volatility_rank
"""
import pandas as pd
import numpy as np


def realized_volatility(df: pd.DataFrame) -> pd.Series:
    """已实现波动率（20 日年化）"""
    returns = df['close'].pct_change()
    return returns.rolling(20, min_periods=1).std() * np.sqrt(252)


def downside_volatility(df: pd.DataFrame) -> pd.Series:
    """下行波动率"""
    returns = df['close'].pct_change()
    downside_returns = returns.where(returns < 0, 0)
    return downside_returns.rolling(20, min_periods=1).std() * np.sqrt(252)


def upside_volatility(df: pd.DataFrame) -> pd.Series:
    """上行波动率"""
    returns = df['close'].pct_change()
    upside_returns = returns.where(returns > 0, 0)
    return upside_returns.rolling(20, min_periods=1).std() * np.sqrt(252)


def atr(df: pd.DataFrame) -> pd.Series:
    """平均真实波幅 (ATR)"""
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close_prev)
    tr3 = abs(low - close_prev)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=1).mean()


def price_range(df: pd.DataFrame) -> pd.Series:
    """价格范围（最高 - 最低）/ 收盘"""
    return (df['high'] - df['low']) / df['close']


def high_low_ratio(df: pd.DataFrame) -> pd.Series:
    """高低比率"""
    return df['high'] / df['low']


def volatility_5(df: pd.DataFrame) -> pd.Series:
    """5 日波动率"""
    returns = df['close'].pct_change()
    return returns.rolling(5, min_periods=1).std() * np.sqrt(252)


def volatility_10(df: pd.DataFrame) -> pd.Series:
    """10 日波动率"""
    returns = df['close'].pct_change()
    return returns.rolling(10, min_periods=1).std() * np.sqrt(252)


def volatility_20(df: pd.DataFrame) -> pd.Series:
    """20 日波动率"""
    returns = df['close'].pct_change()
    return returns.rolling(20, min_periods=1).std() * np.sqrt(252)


def volatility_rank(df: pd.DataFrame) -> pd.Series:
    """波动率排名"""
    returns = df['close'].pct_change()
    vol = returns.rolling(20, min_periods=1).std()
    return vol.rolling(252, min_periods=1).apply(lambda x: x.rank(pct=True).iloc[-1], raw=False)
