"""
Alpha 评估器

计算 IC、RankIC、IC_IR 等指标
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from src.utils import get_db_connection
from config.settings import DATABASE_PATH


class AlphaEvaluator:
    """Alpha 评估器"""
    
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
    
    def calculate_forward_returns(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算未来收益"""
        return df.groupby('ts_code')['close'].transform(
            lambda x: x.shift(-period) / x - 1
        ) * 100
    
    def calculate_ic(self, alpha_values: pd.Series, forward_returns: pd.Series) -> float:
        """计算 IC（Pearson 相关系数）"""
        # 按交易日分组计算 IC
        ic_by_date = []
        
        for date in alpha_values['trade_date'].unique():
            date_mask = alpha_values['trade_date'] == date
            ret_mask = forward_returns.index.get_level_values('trade_date') == date
            
            alpha_date = alpha_values.loc[date_mask, 'alpha_value']
            ret_date = forward_returns.loc[ret_mask]
            
            if len(alpha_date) > 30 and len(ret_date) > 30:
                # 去极值
                alpha_clean = alpha_date.clip(alpha_date.mean() - 3*alpha_date.std(),
                                             alpha_date.mean() + 3*alpha_date.std())
                ret_clean = ret_date.clip(ret_date.mean() - 3*ret_date.std(),
                                         ret_date.mean() + 3*ret_date.std())
                
                ic = alpha_clean.corr(ret_clean, method='pearson')
                ic_by_date.append(ic)
        
        return np.mean(ic_by_date) if ic_by_date else np.nan
    
    def calculate_rank_ic(self, alpha_values: pd.Series, forward_returns: pd.Series) -> float:
        """计算 RankIC（Spearman 秩相关）"""
        ic_by_date = []
        
        for date in alpha_values['trade_date'].unique():
            date_mask = alpha_values['trade_date'] == date
            ret_mask = forward_returns.index.get_level_values('trade_date') == date
            
            alpha_date = alpha_values.loc[date_mask, 'alpha_value']
            ret_date = forward_returns.loc[ret_mask]
            
            if len(alpha_date) > 30 and len(ret_date) > 30:
                ic = alpha_date.corr(ret_date, method='spearman')
                ic_by_date.append(ic)
        
        return np.mean(ic_by_date) if ic_by_date else np.nan
    
    def evaluate_alpha(self, alpha_values: pd.Series, forward_returns: pd.Series) -> Dict:
        """
        评估 Alpha
        
        Returns:
            Dict: IC, RankIC, IC_IR, RankIC_IR
        """
        ic = self.calculate_ic(alpha_values, forward_returns)
        rank_ic = self.calculate_rank_ic(alpha_values, forward_returns)
        
        # 计算 IC 时间序列的标准差
        ic_std = alpha_values.groupby('trade_date')['alpha_value'].apply(
            lambda x: x.corr(forward_returns.loc[forward_returns.index.get_level_values('trade_date') == x.index.get_level_values('trade_date')[0]], 'pearson')
        ).std() if len(alpha_values) > 100 else 0.1
        
        ic_ir = ic / ic_std if ic_std > 0 else 0
        rank_ic_ir = rank_ic / ic_std if ic_std > 0 else 0
        
        return {
            'ic_mean': ic,
            'rank_ic_mean': rank_ic,
            'ic_ir': ic_ir,
            'rank_ic_ir': rank_ic_ir
        }
