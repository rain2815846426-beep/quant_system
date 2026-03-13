"""
波动率因子计算模块

波动率因子衡量股票价格波动的剧烈程度。

因子列表：
- volatility_20: 20 日波动率（20 日收益率的标准差）

计算公式：
volatility_20 = std(returns_20) * sqrt(252) * 100
（年化波动率）
"""
import pandas as pd
import numpy as np


def calculate_volatility_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算波动率因子
    
    Args:
        df: 包含 ts_code, trade_date, close 字段的 DataFrame
        
    Returns:
        pd.DataFrame: 包含波动率因子的 DataFrame
    """
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 计算日收益率
    df['daily_return'] = df.groupby('ts_code')['close'].pct_change()
    
    # 计算 20 日波动率（年化）
    df['volatility_20'] = df.groupby('ts_code')['daily_return'].transform(
        lambda x: x.rolling(window=20).std() * np.sqrt(252) * 100
    )
    
    # 删除临时列
    df = df.drop(columns=['daily_return'])
    
    return df


def get_volatility_factor_names() -> list:
    """返回波动率因子名称列表"""
    return ['volatility_20']
