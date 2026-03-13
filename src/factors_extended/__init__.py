"""
A 股扩展因子库

5 类 50 个因子：
1. 动量因子 (10 个)
2. 反转因子 (10 个)
3. 成交量因子 (10 个)
4. 波动率因子 (10 个)
5. 资金流因子 (10 个)
"""
from .momentum_factors import (
    return_1, return_3, return_5, return_10, return_20,
    momentum_5, momentum_10, momentum_20, momentum_60, price_rank_20
)
from .reversal_factors import (
    reversal_1, reversal_3, reversal_5, short_term_reversal, gap_reversal,
    overnight_return, intraday_reversal, high_low_reversal, volatility_reversal, drawdown_reversal
)
from .volume_factors import (
    volume_ratio, volume_change, volume_spike, volume_rank_20, volume_mean_ratio,
    turnover_rate, turnover_change, adv20_ratio, volume_volatility, volume_price_corr
)
from .volatility_factors import (
    realized_volatility, downside_volatility, upside_volatility, atr, price_range,
    high_low_ratio, volatility_5, volatility_10, volatility_20, volatility_rank
)
from .moneyflow_factors import (
    money_flow, price_volume_trend, volume_weighted_return, vwap_deviation, large_trade_ratio,
    accumulation_distribution, volume_pressure, order_imbalance, smart_money, price_impact
)

__all__ = [
    # 动量因子
    'return_1', 'return_3', 'return_5', 'return_10', 'return_20',
    'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60', 'price_rank_20',
    # 反转因子
    'reversal_1', 'reversal_3', 'reversal_5', 'short_term_reversal', 'gap_reversal',
    'overnight_return', 'intraday_reversal', 'high_low_reversal', 'volatility_reversal', 'drawdown_reversal',
    # 成交量因子
    'volume_ratio', 'volume_change', 'volume_spike', 'volume_rank_20', 'volume_mean_ratio',
    'turnover_rate', 'turnover_change', 'adv20_ratio', 'volume_volatility', 'volume_price_corr',
    # 波动率因子
    'realized_volatility', 'downside_volatility', 'upside_volatility', 'atr', 'price_range',
    'high_low_ratio', 'volatility_5', 'volatility_10', 'volatility_20', 'volatility_rank',
    # 资金流因子
    'money_flow', 'price_volume_trend', 'volume_weighted_return', 'vwap_deviation', 'large_trade_ratio',
    'accumulation_distribution', 'volume_pressure', 'order_imbalance', 'smart_money', 'price_impact',
]
