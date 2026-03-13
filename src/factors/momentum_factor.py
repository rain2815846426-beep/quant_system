"""
动量因子计算模块

动量因子衡量股票价格在一段时间内的涨跌幅度。

因子列表：
- momentum_5: 5 日动量（5 日收益率）
- momentum_20: 20 日动量（20 日收益率）
- momentum_60: 60 日动量（60 日收益率）

计算公式：
momentum_N = (close_today - close_N_days_ago) / close_N_days_ago * 100
"""
import pandas as pd
import numpy as np


def calculate_momentum_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算动量因子
    
    Args:
        df: 包含 ts_code, trade_date, close 字段的 DataFrame
        
    Returns:
        pd.DataFrame: 包含动量因子的 DataFrame
    """
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 计算 5 日动量
    df['momentum_5'] = df.groupby('ts_code')['close'].pct_change(periods=5) * 100
    
    # 计算 20 日动量
    df['momentum_20'] = df.groupby('ts_code')['close'].pct_change(periods=20) * 100
    
    # 计算 60 日动量
    df['momentum_60'] = df.groupby('ts_code')['close'].pct_change(periods=60) * 100
    
    return df


def get_momentum_factor_names() -> list:
    """返回动量因子名称列表"""
    return ['momentum_5', 'momentum_20', 'momentum_60']
