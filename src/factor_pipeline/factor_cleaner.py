"""
因子清洗模块

关键：所有处理只使用截面数据（同一交易日），避免前视偏差
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Tuple, Optional


def winsorize_factor(
    factor_values: pd.Series,
    method: str = 'mad',
    n_std: float = 3.0
) -> pd.Series:
    """
    去极值（截面去极值，避免前视偏差）
    
    Args:
        factor_values: 因子值（单交易日截面）
        method: 'mad' (中位数绝对差) 或 'std' (标准差)
        n_std: 倍数（默认 3 倍）
        
    Returns:
        去极值后的因子值
        
    注意：
    - 只使用当前截面的数据
    - 不使用历史统计量
    """
    if factor_values.empty:
        return factor_values
    
    if method == 'mad':
        # MAD 方法（更稳健）
        median = factor_values.median()
        mad = (factor_values - median).abs().median()
        
        if mad == 0:
            return factor_values
        
        lower = median - n_std * mad * 1.4826  # 1.4826 使 MAD 与 std 等价
        upper = median + n_std * mad * 1.4826
        
    else:  # std 方法
        mean = factor_values.mean()
        std = factor_values.std()
        
        if std == 0:
            return factor_values
        
        lower = mean - n_std * std
        upper = mean + n_std * std
    
    return factor_values.clip(lower=lower, upper=upper)


def zscore_factor(
    factor_values: pd.Series,
    use_median: bool = False
) -> pd.Series:
    """
    标准化（截面标准化，避免前视偏差）
    
    Args:
        factor_values: 因子值（单交易日截面）
        use_median: 是否使用中位数代替均值
        
    Returns:
        标准化后的因子值（均值 0，标准差 1）
        
    注意：
    - 只使用当前截面的均值和标准差
    - 不使用历史统计量
    """
    if factor_values.empty:
        return factor_values
    
    if use_median:
        median = factor_values.median()
        mad = (factor_values - median).abs().median()
        if mad == 0:
            return factor_values
        return (factor_values - median) / (mad * 1.4826)
    else:
        mean = factor_values.mean()
        std = factor_values.std()
        
        if std == 0 or std < 1e-10:
            return pd.Series(0, index=factor_values.index)
        
        return (factor_values - mean) / std


def neutralize_factor(
    factor_values: pd.Series,
    industry: pd.Series,
    log_market_cap: pd.Series,
    industry_column: str = 'industry'
) -> pd.Series:
    """
    行业市值中性化（截面回归，避免前视偏差）
    
    使用 t 日的行业分类和市值数据，对 t 日的因子值进行中性化
    
    Args:
        factor_values: 因子值（单交易日截面）
        industry: 行业分类（单交易日截面）
        log_market_cap: 对数市值（单交易日截面）
        industry_column: 行业列名
        
    Returns:
        中性化后的因子值（残差）
        
    方法：
    factor = β0 + β1*industry + β2*ln(market_cap) + ε
    返回：ε
    
    注意：
    - 只使用当前截面的数据
    - 不使用未来或历史的行业/市值数据
    """
    # 构建数据框
    df = pd.DataFrame({
        'factor': factor_values,
        'industry': industry,
        'log_mv': log_market_cap
    })
    
    # 删除缺失值
    df = df.dropna()
    
    if df.empty:
        return pd.Series(index=factor_values.index, dtype=float)
    
    # 行业虚拟变量
    industry_dummies = pd.get_dummies(df['industry'], prefix='ind')
    
    # 构建回归矩阵
    X = pd.concat([
        pd.Series(1, index=df.index, name='const'),  # 截距
        industry_dummies,
        df['log_mv']
    ], axis=1)
    
    y = df['factor']
    
    # 检查共线性
    if X.shape[0] <= X.shape[1]:
        # 样本不足，返回原因子
        return df['factor']
    
    try:
        # OLS 回归
        # 使用 numpy 进行快速回归
        X_matrix = X.values
        y_vector = y.values
        
        # 添加小正则项避免奇异矩阵
        XtX = X_matrix.T @ X_matrix
        reg = 1e-8 * np.eye(XtX.shape[0])
        beta = np.linalg.solve(XtX + reg, X_matrix.T @ y_vector)
        
        # 计算残差
        y_pred = X_matrix @ beta
        residuals = y_vector - y_pred
        
        # 返回残差
        result = pd.Series(residuals, index=df.index)
        
        # 重新索引到原始 index
        return result.reindex(factor_values.index)
        
    except Exception as e:
        # 回归失败，返回原因子
        return factor_values


def process_factor(
    factor_values: pd.Series,
    industry: Optional[pd.Series] = None,
    log_market_cap: Optional[pd.Series] = None,
    winsorize_method: str = 'mad',
    winsorize_nstd: float = 3.0,
    neutralize: bool = True
) -> pd.Series:
    """
    完整的因子处理流程（截面处理，避免前视偏差）
    
    流程：
    1. 去极值（截面）
    2. 标准化（截面）
    3. 中性化（截面，可选）
    
    Args:
        factor_values: 因子值（单交易日截面）
        industry: 行业分类（可选）
        log_market_cap: 对数市值（可选）
        winsorize_method: 去极值方法
        winsorize_nstd: 去极值倍数
        neutralize: 是否中性化
        
    Returns:
        处理后的因子值
    """
    # 1. 去极值（截面）
    factor_clean = winsorize_factor(
        factor_values,
        method=winsorize_method,
        n_std=winsorize_nstd
    )
    
    # 2. 标准化（截面）
    factor_standardized = zscore_factor(factor_clean)
    
    # 3. 中性化（截面，可选）
    if neutralize and industry is not None and log_market_cap is not None:
        factor_neutralized = neutralize_factor(
            factor_standardized,
            industry,
            log_market_cap
        )
        # 中性化后再标准化一次
        return zscore_factor(factor_neutralized)
    
    return factor_standardized
