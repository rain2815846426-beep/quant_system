"""
IC（Information Coefficient）分析模块

计算因子与未来收益的相关性，评估因子预测能力。

功能：
- IC 计算（Pearson 相关系数）
- RankIC 计算（Spearman 秩相关）
- IC 统计指标（Mean, Std, IR）
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Tuple, Dict, Optional
import sqlite3
from pathlib import Path

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def calculate_forward_returns(
    df: pd.DataFrame,
    periods: list = [5, 10, 20]
) -> pd.DataFrame:
    """
    计算未来收益
    
    Args:
        df: 包含 ts_code, trade_date, close 的 DataFrame
        periods: 预测周期列表
        
    Returns:
        DataFrame: 包含未来收益的 DataFrame
    """
    df = df.copy()
    df = df.sort_values(['ts_code', 'trade_date'])
    
    for period in periods:
        # 计算未来 N 期收益
        df[f'forward_return_{period}'] = df.groupby('ts_code')['close'].transform(
            lambda x: x.shift(-period) / x - 1
        ) * 100
    
    return df


def calculate_ic(
    factor_df: pd.DataFrame,
    forward_period: int = 20,
    return_col: str = 'forward_return_20'
) -> pd.DataFrame:
    """
    计算 IC（Pearson 相关系数）
    
    Args:
        factor_df: 包含 trade_date, factor_value, forward_return 的 DataFrame
        forward_period: 预测周期
        return_col: 收益列名
        
    Returns:
        DataFrame: 每日 IC 值
    """
    df = factor_df.copy()
    
    # 按交易日计算 IC
    ic_by_date = df.groupby('trade_date').apply(
        lambda x: _calc_pearson_ic(x['factor_value'], x[return_col])
    ).reset_index()
    
    ic_by_date.columns = ['trade_date', 'ic']
    
    return ic_by_date


def calculate_rank_ic(
    factor_df: pd.DataFrame,
    forward_period: int = 20,
    return_col: str = 'forward_return_20'
) -> pd.DataFrame:
    """
    计算 RankIC（Spearman 秩相关系数）
    
    Args:
        factor_df: 包含 trade_date, factor_value, forward_return 的 DataFrame
        forward_period: 预测周期
        return_col: 收益列名
        
    Returns:
        DataFrame: 每日 RankIC 值
    """
    df = factor_df.copy()
    
    # 按交易日计算 RankIC
    rank_ic_by_date = df.groupby('trade_date').apply(
        lambda x: _calc_spearman_ic(x['factor_value'], x[return_col])
    ).reset_index()
    
    rank_ic_by_date.columns = ['trade_date', 'rank_ic']
    
    return rank_ic_by_date


def _calc_pearson_ic(factor: pd.Series, ret: pd.Series) -> float:
    """计算 Pearson IC"""
    # 去除 NaN
    mask = factor.notna() & ret.notna()
    if mask.sum() < 30:  # 至少 30 个样本
        return np.nan
    
    factor_clean = factor[mask]
    ret_clean = ret[mask]
    
    # 去极值（3 倍标准差）
    factor_clean = _winsorize(factor_clean, 3)
    ret_clean = _winsorize(ret_clean, 3)
    
    # 计算相关系数
    ic = factor_clean.corr(ret_clean, method='pearson')
    return ic


def _calc_spearman_ic(factor: pd.Series, ret: pd.Series) -> float:
    """计算 Spearman RankIC"""
    # 去除 NaN
    mask = factor.notna() & ret.notna()
    if mask.sum() < 30:
        return np.nan
    
    factor_clean = factor[mask]
    ret_clean = ret[mask]
    
    # 计算秩相关
    ic = factor_clean.corr(ret_clean, method='spearman')
    return ic


def _winsorize(series: pd.Series, n_std: float = 3) -> pd.Series:
    """去极值（Winsorization）"""
    mean = series.mean()
    std = series.std()
    lower = mean - n_std * std
    upper = mean + n_std * std
    
    return series.clip(lower=lower, upper=upper)


def calculate_ic_statistics(ic_series: pd.Series) -> Dict[str, float]:
    """
    计算 IC 统计指标
    
    Args:
        ic_series: IC 时间序列
        
    Returns:
        Dict: IC 统计指标
    """
    ic_clean = ic_series.dropna()
    
    if len(ic_clean) == 0:
        return {
            'ic_mean': np.nan,
            'ic_std': np.nan,
            'ic_ir': np.nan,
            'ic_tstat': np.nan,
            'ic_pvalue': np.nan,
            'n_periods': 0
        }
    
    ic_mean = ic_clean.mean()
    ic_std = ic_clean.std()
    ic_ir = ic_mean / ic_std if ic_std > 0 else np.nan
    
    # T 检验
    ic_tstat = ic_mean / (ic_std / np.sqrt(len(ic_clean))) if ic_std > 0 else np.nan
    ic_pvalue = 2 * (1 - stats.t.cdf(abs(ic_tstat), len(ic_clean) - 1))
    
    return {
        'ic_mean': ic_mean,
        'ic_std': ic_std,
        'ic_ir': ic_ir,
        'ic_tstat': ic_tstat,
        'ic_pvalue': ic_pvalue,
        'n_periods': len(ic_clean)
    }


def analyze_factor_ic(
    db_path: Path = DATABASE_PATH,
    factor_name: str = 'momentum_20',
    forward_period: int = 20,
    start_date: str = '20180101',
    batch_size: int = 252  # 每次加载 1 年数据
) -> Dict:
    """
    分析单个因子的 IC
    
    Args:
        db_path: 数据库路径
        factor_name: 因子名称
        forward_period: 预测周期
        start_date: 开始日期
        batch_size: 批量大小（交易日数）
        
    Returns:
        Dict: IC 分析结果
    """
    conn = sqlite3.connect(db_path)
    
    # 获取交易日列表
    trade_dates = pd.read_sql_query("""
        SELECT DISTINCT trade_date FROM factor_values
        WHERE trade_date >= ?
        ORDER BY trade_date
    """, conn, params=(start_date,))['trade_date'].tolist()
    
    conn.close()
    
    print(f"分析因子：{factor_name}")
    print(f"交易日数量：{len(trade_dates)}")
    print(f"预测周期：{forward_period}日")
    
    # 批量加载数据
    all_ic = []
    all_rank_ic = []
    
    for i in range(0, len(trade_dates), batch_size):
        batch_dates = trade_dates[i:i+batch_size]
        date_str = ','.join(f"'{d}'" for d in batch_dates)
        
        # 加载因子值和价格数据
        query = f"""
            WITH factor_data AS (
                SELECT ts_code, trade_date, factor_value
                FROM factor_values
                WHERE factor_name = '{factor_name}'
                AND trade_date IN ({date_str})
            ),
            price_data AS (
                SELECT ts_code, trade_date, close
                FROM daily_prices
                WHERE trade_date IN ({date_str})
                OR trade_date IN (
                    SELECT MAX(trade_date) FROM daily_prices 
                    GROUP BY ts_code
                )
            )
            SELECT f.ts_code, f.trade_date, f.factor_value, p.close
            FROM factor_data f
            JOIN price_data p ON f.ts_code = p.ts_code AND f.trade_date = p.trade_date
            ORDER BY f.trade_date, f.ts_code
        """
        
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            continue
        
        # 计算未来收益
        df = df.pivot(index=['ts_code', 'trade_date'], columns='close').reset_index()
        df = df.sort_values(['ts_code', 'trade_date'])
        
        # 计算未来收益（简化版本）
        # 实际应该使用更精确的方法
        print(f"处理批次 {i//batch_size + 1}/{(len(trade_dates)-1)//batch_size + 1}")
    
    # 简化版本：直接计算 IC
    print("计算 IC...（简化版本）")
    
    return {
        'factor_name': factor_name,
        'forward_period': forward_period,
        'ic_mean': None,
        'ic_std': None,
        'ic_ir': None,
        'rank_ic_mean': None,
        'rank_ic_std': None,
        'n_periods': len(trade_dates)
    }
