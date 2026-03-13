"""
资金流因子 (10 个)

money_flow, price_volume_trend, volume_weighted_return, vwap_deviation, large_trade_ratio
accumulation_distribution, volume_pressure, order_imbalance, smart_money, price_impact
"""
import pandas as pd
import numpy as np


def money_flow(df: pd.DataFrame) -> pd.Series:
    """资金流（典型价格 * 成交量）"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return typical_price * df['volume']


def price_volume_trend(df: pd.DataFrame) -> pd.Series:
    """价量趋势"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    mflow = typical_price * df['volume']
    return mflow.rolling(20, min_periods=1).sum()


def volume_weighted_return(df: pd.DataFrame) -> pd.Series:
    """成交量加权收益"""
    returns = df['close'].pct_change()
    vol_weighted = returns * df['volume']
    return vol_weighted.rolling(20, min_periods=1).mean()


def vwap_deviation(df: pd.DataFrame) -> pd.Series:
    """VWAP 偏离度"""
    # VWAP 近似
    vwap = (df['high'] + df['low'] + df['close'] * 2) / 4
    return (df['close'] - vwap) / vwap


def large_trade_ratio(df: pd.DataFrame) -> pd.Series:
    """大单比率（简化为高成交量日比率）"""
    vol_mean = df['volume'].rolling(20, min_periods=1).mean()
    large_days = (df['volume'] > vol_mean * 1.5).astype(int)
    return large_days.rolling(20, min_periods=1).sum() / 20


def accumulation_distribution(df: pd.DataFrame) -> pd.Series:
    """累积分布线"""
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']
    
    clv = ((close - low) - (high - close)) / (high - low + 1e-10)
    ad = clv * volume
    return ad.rolling(20, min_periods=1).sum()


def volume_pressure(df: pd.DataFrame) -> pd.Series:
    """成交量压力"""
    # 上涨成交量 vs 下跌成交量
    returns = df['close'].pct_change()
    up_vol = df['volume'].where(returns > 0, 0)
    down_vol = df['volume'].where(returns < 0, 0)
    
    up_sum = up_vol.rolling(20, min_periods=1).sum()
    down_sum = down_vol.rolling(20, min_periods=1).sum()
    
    return (up_sum - down_sum) / (up_sum + down_sum + 1e-10)


def order_imbalance(df: pd.DataFrame) -> pd.Series:
    """订单不平衡"""
    # 简化：收盘价位置
    high = df['high']
    low = df['low']
    close = df['close']
    
    position = (close - low) / (high - low + 1e-10)
    return position * df['volume']


def smart_money(df: pd.DataFrame) -> pd.Series:
    """聪明钱"""
    # 价格上涨且成交量放大
    returns = df['close'].pct_change()
    vol_change = df['volume'].pct_change()
    
    smart = (returns > 0) & (vol_change > 0)
    return smart.astype(int).rolling(20, min_periods=1).sum() / 20


def price_impact(df: pd.DataFrame) -> pd.Series:
    """价格冲击"""
    # 单位成交量的价格变化
    returns = df['close'].pct_change()
    return returns / (df['volume'] + 1e-10)
