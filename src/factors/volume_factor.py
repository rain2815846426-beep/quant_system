"""
成交量因子计算模块

成交量因子衡量股票成交量的变化特征。

因子列表：
- volume_mean_20: 20 日平均成交量
- volume_ratio: 成交量比率（当日成交量/20 日平均成交量）

计算公式：
volume_mean_20 = mean(volume_20)
volume_ratio = volume_today / volume_mean_20
"""
import pandas as pd
import numpy as np


def calculate_volume_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算成交量因子
    
    Args:
        df: 包含 ts_code, trade_date, volume 字段的 DataFrame
        
    Returns:
        pd.DataFrame: 包含成交量因子的 DataFrame
    """
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 计算 20 日平均成交量
    df['volume_mean_20'] = df.groupby('ts_code')['volume'].transform(
        lambda x: x.rolling(window=20).mean()
    )
    
    # 计算成交量比率
    df['volume_ratio'] = df['volume'] / df['volume_mean_20']
    
    return df


def get_volume_factor_names() -> list:
    """返回成交量因子名称列表"""
    return ['volume_mean_20', 'volume_ratio']
