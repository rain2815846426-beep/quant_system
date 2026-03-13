"""
交易成本模型

计算交易成本对收益的影响
"""
import pandas as pd
import numpy as np
from typing import Dict


class TransactionCostModel:
    """交易成本模型"""
    
    def __init__(
        self,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        market_impact: float = 0.001
    ):
        """
        初始化
        
        Args:
            commission_rate: 手续费率（默认 0.1%）
            slippage_rate: 滑点（默认 0.05%）
            market_impact: 市场冲击成本
        """
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.market_impact = market_impact
    
    def calculate_cost(self, turnover: float) -> float:
        """
        计算交易成本
        
        Args:
            turnover: 换手率
            
        Returns:
            交易成本
        """
        # 固定成本：手续费 + 滑点
        fixed_cost = self.commission_rate + self.slippage_rate
        
        # 可变成本：市场冲击（与换手率成正比）
        variable_cost = turnover * self.market_impact
        
        # 总成本
        total_cost = fixed_cost + variable_cost
        
        return total_cost
    
    def calculate_net_return(
        self,
        gross_return: float,
        turnover: float
    ) -> float:
        """
        计算净收益
        
        Args:
            gross_return: 毛收益
            turnover: 换手率
            
        Returns:
            净收益
        """
        cost = self.calculate_cost(turnover)
        return gross_return - cost


def apply_transaction_costs(
    gross_returns: pd.Series,
    turnover: pd.Series,
    cost_model: TransactionCostModel = None
) -> pd.Series:
    """
    应用交易成本
    
    Args:
        gross_returns: 毛收益时间序列
        turnover: 换手率时间序列
        cost_model: 交易成本模型
        
    Returns:
        净收益时间序列
    """
    if cost_model is None:
        cost_model = TransactionCostModel()
    
    net_returns = []
    
    for i in range(len(gross_returns)):
        gross_ret = gross_returns.iloc[i]
        
        if i < len(turnover):
            turn = turnover.iloc[i]
        else:
            turn = 0
        
        net_ret = cost_model.calculate_net_return(gross_ret, turn)
        net_returns.append(net_ret)
    
    return pd.Series(net_returns, index=gross_returns.index)


def calculate_cost_statistics(
    gross_returns: pd.Series,
    net_returns: pd.Series,
    turnover: pd.Series
) -> Dict:
    """
    计算成本统计
    
    Args:
        gross_returns: 毛收益
        net_returns: 净收益
        turnover: 换手率
        
    Returns:
        统计指标字典
    """
    # 总成本
    total_cost = (gross_returns - net_returns).sum()
    
    # 年均成本
    annual_cost = (gross_returns - net_returns).mean() * 252
    
    # 成本占比
    cost_ratio = total_cost / gross_returns.sum() if gross_returns.sum() != 0 else np.nan
    
    return {
        'total_cost': total_cost,
        'annual_cost': annual_cost,
        'cost_ratio': cost_ratio,
        'avg_daily_turnover': turnover.mean(),
        'annual_turnover': turnover.mean() * 252
    }
