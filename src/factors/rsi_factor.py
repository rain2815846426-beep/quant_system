"""
RSI 因子计算模块

RSI（相对强弱指标）是常用的技术分析指标。

因子列表：
- rsi_14: 14 日 RSI

计算公式：
RS = 平均上涨幅度 / 平均下跌幅度
RSI = 100 - 100 / (1 + RS)

RSI 值范围：0-100
- RSI > 70: 超买
- RSI < 30: 超卖
"""
import pandas as pd
import numpy as np


def calculate_rsi_factors(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算 RSI 因子
    
    Args:
        df: 包含 ts_code, trade_date, close 字段的 DataFrame
        period: RSI 计算周期，默认 14
        
    Returns:
        pd.DataFrame: 包含 RSI 因子的 DataFrame
    """
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
    
    # 初始化 RSI 列
    df[f'rsi_{period}'] = np.nan
    
    # 按股票分组计算 RSI
    for ts_code in df['ts_code'].unique():
        mask = df['ts_code'] == ts_code
        close = df.loc[mask, 'close'].reset_index(drop=True)
        
        # 计算价格变化
        delta = close.diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        # 计算平均涨幅和平均跌幅（使用指数移动平均）
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        
        # 计算 RS 和 RSI
        rs = avg_gain / avg_loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        
        # 处理无穷大的情况
        rsi = rsi.replace([np.inf, -np.inf], np.nan)
        
        # 赋值回去
        df.loc[mask, f'rsi_{period}'] = rsi.values
    
    return df


def get_rsi_factor_names(period: int = 14) -> list:
    """返回 RSI 因子名称列表"""
    return [f'rsi_{period}']
