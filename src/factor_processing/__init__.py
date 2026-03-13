"""
因子预处理模块

提供因子去极值、标准化等功能
"""
from .factor_preprocessing import (
    winsorize_mad,
    winsorize_sigma,
    winsorize_quantile,
    zscore,
    process_factor_cross_section
)

__all__ = [
    'winsorize_mad',
    'winsorize_sigma',
    'winsorize_quantile',
    'zscore',
    'process_factor_cross_section'
]
