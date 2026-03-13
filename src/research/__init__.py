"""
因子研究模块

用于评估因子的有效性，包括：
- IC 分析
- RankIC 分析
- 因子分层回测
"""
from .ic_analysis import calculate_ic, calculate_rank_ic
from .factor_group_backtest import factor_group_backtest

__all__ = [
    "calculate_ic",
    "calculate_rank_ic",
    "factor_group_backtest",
]
