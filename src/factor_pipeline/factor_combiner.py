"""
多因子组合模块
"""
import pandas as pd
import numpy as np
from typing import List, Dict


def combine_factors_equal_weighted(
    factor_data: pd.DataFrame,
    factor_names: List[str]
) -> pd.Series:
    """
    等权组合因子
    
    Args:
        factor_data: 因子值 DataFrame (index: trade_date, columns: ts_code 或 factor_name)
        factor_names: 因子名称列表
        
    Returns:
        组合因子值
    """
    factors = []
    
    for name in factor_names:
        if name in factor_data.columns:
            factors.append(factor_data[name])
    
    if not factors:
        return pd.Series()
    
    # 等权平均
    combined = pd.concat(factors, axis=1).mean(axis=1)
    
    return combined


def combine_factors_ic_weighted(
    factor_data: pd.DataFrame,
    ic_scores: Dict[str, float],
    factor_names: List[str]
) -> pd.Series:
    """
    IC 加权组合因子
    
    Args:
        factor_data: 因子值 DataFrame
        ic_scores: 各因子的 IC_IR 分数
        factor_names: 因子名称列表
        
    Returns:
        IC 加权组合因子
    """
    # 获取 IC 权重
    weights = {}
    total_ic = 0
    
    for name in factor_names:
        if name in ic_scores:
            ic = abs(ic_scores[name])
            if ic > 0:
                weights[name] = ic
                total_ic += ic
    
    if total_ic == 0:
        # 如果 IC 都为 0，使用等权
        return combine_factors_equal_weighted(factor_data, factor_names)
    
    # 归一化权重
    for name in weights:
        weights[name] /= total_ic
    
    # 加权组合
    weighted_factors = []
    for name in factor_names:
        if name in factor_data.columns and name in weights:
            weighted_factors.append(factor_data[name] * weights[name])
    
    if weighted_factors:
        combined = pd.concat(weighted_factors, axis=1).sum(axis=1)
        return combined
    
    return pd.Series()
