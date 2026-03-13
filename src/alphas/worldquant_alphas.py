"""
WorldQuant 101 Alpha 因子实现

基于论文《101 Formulaic Alphas》的实现
参考：https://arxiv.org/pdf/1601.00991.pdf

注意：
- 所有输入应为 pandas Series
- 输出为 alpha 因子值
"""
import pandas as pd
import numpy as np
from src.operators import (
    rank, delay, delta, ts_rank, ts_max, ts_min, ts_mean,
    correlation, covariance, decay_linear, scale,
    signed_power, abs_value, log_value, indicator
)


def alpha_1(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Alpha 1
    
    (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns,20) : close), 2.), 5)) - 0.5
    
    简化版本：
    - 当收益率为负时，使用 20 日标准差
    - 否则使用收盘价
    - 计算 5 日最大值的排名
    """
    returns = close.pct_change()
    stddev_20 = returns.rolling(20, min_periods=1).std()
    
    # 条件选择
    conditional = np.where(returns < 0, stddev_20, close)
    conditional = pd.Series(conditional, index=close.index)
    
    # 平方
    powered = signed_power(conditional, 2.)
    
    # 5 日最大值
    ts_max_5 = ts_max(powered, 5)
    
    # 排名
    result = rank(ts_max_5) - 0.5
    
    return result


def alpha_2(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 2
    
    ((-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6)) * -1
    
    逻辑：
    - 成交量的对数差分排名
    - 开盘收盘变化率排名
    - 6 日相关性
    """
    # 成交量对数差分
    log_vol = np.log(volume)
    delta_log_vol = delta(log_vol, 2)
    rank_delta_log_vol = rank(delta_log_vol)
    
    # 开盘收盘变化率
    close_open_ratio = (close - open_p) / open_p
    rank_close_open = rank(close_open_ratio)
    
    # 6 日相关性
    corr = correlation(rank_delta_log_vol, rank_close_open, 6)
    
    result = -1 * corr * -1
    
    return result


def alpha_3(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Alpha 3
    
    (-1 * correlation(rank(open), rank(volume), 10))
    
    逻辑：
    - 开盘价排名
    - 成交量排名
    - 10 日负相关性
    """
    rank_open = rank(open_p)
    rank_volume = rank(volume)
    
    corr = correlation(rank_open, rank_volume, 10)
    
    result = -1 * corr
    
    return result


def alpha_4(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Alpha 4
    
    (-1 * Ts_Rank(rank(low), 9))
    
    逻辑：
    - 最低价排名
    - 时间序列排名（9 日）
    - 取负
    """
    rank_low = rank(low)
    ts_rank_9 = ts_rank(rank_low, 9)
    
    result = -1 * ts_rank_9
    
    return result


def alpha_5(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 5
    
    (rank(open - (sum(vwap, 10) / 10))) * (-1 * abs(rank(close - vwap)))
    
    逻辑：
    - VWAP 计算
    - 开盘价与 VWAP 均值的差
    - 收盘价与 VWAP 的差
    """
    # 近似 VWAP
    vwap = (high + low + close + close) / 4  # 简化 VWAP
    
    # VWAP 均值
    vwap_mean = ts_mean(vwap, 10)
    
    # 开盘价差异
    open_diff = open_p - vwap_mean
    rank_open_diff = rank(open_diff)
    
    # 收盘价差异
    close_diff = close - vwap
    rank_close_diff = rank(close_diff)
    
    result = rank_open_diff * (-1 * abs_value(rank_close_diff))
    
    return result


def alpha_6(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 6
    
    (-1 * correlation(open, volume, 10))
    
    逻辑：
    - 开盘价与成交量的 10 日相关性
    - 取负
    """
    corr = correlation(open_p, volume, 10)
    
    result = -1 * corr
    
    return result


def alpha_7(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 7
    
    ((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1 * 1))
    
    逻辑：
    - 20 日平均成交量与当前成交量比较
    - 如果当前成交量大于平均，计算 7 日差分绝对值的时间序列排名
    - 否则返回 -1
    """
    adv20 = ts_mean(volume, 20)
    delta_close_7 = delta(close, 7)
    
    # 条件判断
    condition = adv20 < volume
    
    # 真分支
    true_val = (-1 * ts_rank(abs_value(delta_close_7), 60)) * np.sign(delta_close_7)
    
    # 假分支
    false_val = -1 * 1
    
    result = np.where(condition, true_val, false_val)
    result = pd.Series(result, index=close.index)
    
    return result


def alpha_8(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 8
    
    (-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))))
    
    逻辑：
    - 5 日开盘价和
    - 5 日收益率和
    - 乘积与 10 日前值的差
    """
    returns = close.pct_change()
    
    sum_open_5 = ts_mean(open_p, 5) * 5
    sum_returns_5 = ts_mean(returns, 5) * 5
    
    product = sum_open_5 * sum_returns_5
    delta_product = delta(product, 10)
    
    result = -1 * rank(delta_product)
    
    return result


def alpha_9(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 9
    
    ((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))
    
    逻辑：
    - 1 日差分
    - 5 日最小值 > 0，返回差分
    - 5 日最大值 < 0，返回差分
    - 否则返回负差分
    """
    delta_close_1 = delta(close, 1)
    
    ts_min_5 = ts_min(delta_close_1, 5)
    ts_max_5 = ts_max(delta_close_1, 5)
    
    # 条件 1
    cond1 = ts_min_5 > 0
    # 条件 2
    cond2 = ts_max_5 < 0
    
    result = np.where(cond1, delta_close_1,
             np.where(cond2, delta_close_1,
                      -1 * delta_close_1))
    
    result = pd.Series(result, index=close.index)
    
    return result


def alpha_10(open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Alpha 10
    
    rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))
    
    逻辑：
    - 与 Alpha 9 类似，但使用 4 日窗口
    - 然后排名
    """
    delta_close_1 = delta(close, 1)
    
    ts_min_4 = ts_min(delta_close_1, 4)
    ts_max_4 = ts_max(delta_close_1, 4)
    
    cond1 = ts_min_4 > 0
    cond2 = ts_max_4 < 0
    
    inner = np.where(cond1, delta_close_1,
            np.where(cond2, delta_close_1,
                     -1 * delta_close_1))
    
    inner = pd.Series(inner, index=close.index)
    
    result = rank(inner)
    
    return result


def get_alpha_names() -> list:
    """返回所有 Alpha 因子名称"""
    return [f'alpha_{i}' for i in range(1, 11)]
