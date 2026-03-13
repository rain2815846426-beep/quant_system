"""
Alpha Ranking 模型

实现三种 Alpha Score 计算方法
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Literal


def alpha_score_equal_weight(
    factor_data: pd.DataFrame
) -> pd.Series:
    """
    等权 Alpha Score
    
    Args:
        factor_data: 因子值 DataFrame (index: stocks, columns: factors)
                    因子值应该已经标准化
        
    Returns:
        Alpha Score（每只股票一个分数）
        
    方法：
    score = mean(zscore(factors))
    """
    # 直接求均值（假设因子已经标准化）
    score = factor_data.mean(axis=1)
    
    return score


def alpha_score_ic_weight(
    factor_data: pd.DataFrame,
    ic_scores: Dict[str, float]
) -> pd.Series:
    """
    IC 加权 Alpha Score
    
    Args:
        factor_data: 因子值 DataFrame
        ic_scores: 各因子的 IC_IR 分数
        
    Returns:
        Alpha Score
        
    方法：
    weight_i = IC_i / sum(|IC|)
    score = Σ weight_i * factor_i
    """
    # 计算 IC 权重
    weights = {}
    total_ic = 0
    
    for factor_name in factor_data.columns:
        if factor_name in ic_scores:
            ic = abs(ic_scores[factor_name])
            if ic > 0:
                weights[factor_name] = ic
                total_ic += ic
    
    if total_ic == 0:
        # 如果没有 IC 数据，使用等权
        return alpha_score_equal_weight(factor_data)
    
    # 归一化权重
    for name in weights:
        weights[name] /= total_ic
    
    # 加权计算
    score = pd.Series(0, index=factor_data.index)
    
    for factor_name, weight in weights.items():
        if factor_name in factor_data.columns:
            score += factor_data[factor_name] * weight
    
    return score


def alpha_score_rank_average(
    factor_data: pd.DataFrame
) -> pd.Series:
    """
    排名平均 Alpha Score
    
    Args:
        factor_data: 因子值 DataFrame
        
    Returns:
        Alpha Score
        
    方法：
    score = mean(rank(factors))
    """
    # 对每个因子进行排名
    ranked_factors = pd.DataFrame(index=factor_data.index)
    
    for factor_name in factor_data.columns:
        factor_series = factor_data[factor_name].dropna()
        # 排名（百分位）
        ranked_factors[factor_name] = factor_series.rank(pct=True)
    
    # 平均排名
    score = ranked_factors.mean(axis=1)
    
    return score


def calculate_alpha_score(
    factor_data: pd.DataFrame,
    method: Literal['equal', 'ic', 'rank'] = 'equal',
    ic_scores: Dict[str, float] = None
) -> pd.Series:
    """
    计算 Alpha Score（统一接口）
    
    Args:
        factor_data: 因子值 DataFrame
        method: 计算方法
        ic_scores: IC 分数（仅当 method='ic' 时需要）
        
    Returns:
        Alpha Score
    """
    if method == 'equal':
        return alpha_score_equal_weight(factor_data)
    elif method == 'ic':
        if ic_scores is None:
            raise ValueError("IC 加权需要提供 ic_scores")
        return alpha_score_ic_weight(factor_data, ic_scores)
    elif method == 'rank':
        return alpha_score_rank_average(factor_data)
    else:
        raise ValueError(f"未知的方法：{method}")
