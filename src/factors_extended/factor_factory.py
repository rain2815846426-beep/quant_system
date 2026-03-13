"""
因子工厂基类

使用模板模式高效生成相似因子
"""
import pandas as pd
import numpy as np
from typing import Dict, Callable, List


class FactorFactory:
    """因子工厂基类"""
    
    def __init__(self):
        self.factors = {}
    
    def register_factor(self, name: str, func: Callable):
        """注册因子"""
        self.factors[name] = func
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有因子"""
        for name, func in self.factors.items():
            try:
                df[name] = func(df)
            except Exception as e:
                df[name] = np.nan
        return df
    
    def get_factor_names(self) -> List[str]:
        """获取因子名称列表"""
        return list(self.factors.keys())


def create_return_factor(close: pd.Series, period: int) -> pd.Series:
    """创建收益率因子"""
    return close.pct_change(period)


def create_momentum_factor(close: pd.Series, period: int) -> pd.Series:
    """创建动量因子"""
    return close.pct_change(period)


def create_reversal_factor(close: pd.Series, period: int) -> pd.Series:
    """创建反转因子（负动量）"""
    return -close.pct_change(period)


def create_ts_stats_factor(series: pd.Series, period: int, stats: str) -> pd.Series:
    """创建时间序列统计因子"""
    if stats == 'mean':
        return series.rolling(period, min_periods=1).mean()
    elif stats == 'std':
        return series.rolling(period, min_periods=1).std()
    elif stats == 'max':
        return series.rolling(period, min_periods=1).max()
    elif stats == 'min':
        return series.rolling(period, min_periods=1).min()
    elif stats == 'rank':
        return series.rolling(period, min_periods=1).apply(lambda x: x.rank(pct=True).iloc[-1], raw=False)
    else:
        return series.rolling(period, min_periods=1).mean()


def create_cross_sectional_rank(series: pd.Series, period: int = 20) -> pd.Series:
    """创建横截面排名因子"""
    return series.rolling(period, min_periods=1).apply(lambda x: x.rank(pct=True).iloc[-1], raw=False)


def create_delta_factor(series: pd.Series, period: int) -> pd.Series:
    """创建差分因子"""
    return series.diff(period)


def create_ratio_factor(series1: pd.Series, series2: pd.Series, period: int = None) -> pd.Series:
    """创建比率因子"""
    if period:
        series2 = series2.rolling(period, min_periods=1).mean()
    return series1 / series2


def create_correlation_factor(series1: pd.Series, series2: pd.Series, period: int) -> pd.Series:
    """创建相关性因子"""
    return series1.rolling(period, min_periods=1).corr(series2)
