"""
因子预处理管道

关键设计原则（避免前视偏差）：
1. 所有处理只使用 t 日及之前的数据
2. 去极值、标准化使用截面数据（同一交易日）
3. 中性化使用 t 日的行业和市值数据
4. 因子值用于预测 t+1 到 t+N 的收益
"""
from .factor_cleaner import (
    winsorize_factor,
    zscore_factor,
    neutralize_factor,
    process_factor
)
from .factor_returns import (
    calculate_forward_returns,
    calculate_ic_time_series,
    calculate_ic_statistics,
    calculate_factor_returns,
    calculate_long_short_returns,
)
from .factor_backtest import (
    factor_group_backtest,
    calculate_group_statistics,
)
from .factor_combiner import (
    combine_factors_ic_weighted,
    combine_factors_equal_weighted,
)

__all__ = [
    # 预处理
    'winsorize_factor',
    'zscore_factor',
    'neutralize_factor',
    'process_factor',
    # 收益分析
    'calculate_forward_returns',
    'calculate_ic_time_series',
    'calculate_ic_statistics',
    'calculate_factor_returns',
    'calculate_long_short_returns',
    # 回测
    'factor_group_backtest',
    'calculate_group_statistics',
    # 组合
    'combine_factors_ic_weighted',
    'combine_factors_equal_weighted',
]
