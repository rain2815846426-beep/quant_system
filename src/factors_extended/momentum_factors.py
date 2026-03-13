"""
动量因子 (10 个)

return_1, return_3, return_5, return_10, return_20
momentum_5, momentum_10, momentum_20, momentum_60
price_rank_20
"""
import pandas as pd
import numpy as np
from .factor_factory import create_return_factor, create_momentum_factor, create_cross_sectional_rank


def return_1(df: pd.DataFrame) -> pd.Series:
    """1 日收益率"""
    return create_return_factor(df['close'], 1)


def return_3(df: pd.DataFrame) -> pd.Series:
    """3 日收益率"""
    return create_return_factor(df['close'], 3)


def return_5(df: pd.DataFrame) -> pd.Series:
    """5 日收益率"""
    return create_return_factor(df['close'], 5)


def return_10(df: pd.DataFrame) -> pd.Series:
    """10 日收益率"""
    return create_return_factor(df['close'], 10)


def return_20(df: pd.DataFrame) -> pd.Series:
    """20 日收益率"""
    return create_return_factor(df['close'], 20)


def momentum_5(df: pd.DataFrame) -> pd.Series:
    """5 日动量"""
    return create_momentum_factor(df['close'], 5)


def momentum_10(df: pd.DataFrame) -> pd.Series:
    """10 日动量"""
    return create_momentum_factor(df['close'], 10)


def momentum_20(df: pd.DataFrame) -> pd.Series:
    """20 日动量"""
    return create_momentum_factor(df['close'], 20)


def momentum_60(df: pd.DataFrame) -> pd.Series:
    """60 日动量"""
    return create_momentum_factor(df['close'], 60)


def price_rank_20(df: pd.DataFrame) -> pd.Series:
    """20 日价格排名（横截面）"""
    return create_cross_sectional_rank(df['close'], 20)
