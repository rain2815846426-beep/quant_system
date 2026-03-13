"""
风险过滤模块

适用于集中持仓的风险控制
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict


class RiskFilter:
    """风险过滤器"""
    
    def __init__(
        self,
        volatility_percentile: float = 0.90,
        min_daily_turnover: float = 5e7,  # 5000 万
        filter_st: bool = True
    ):
        """
        初始化
        
        Args:
            volatility_percentile: 波动率过滤分位数（默认剔除>90% 分位的股票）
            min_daily_turnover: 最小日成交额（默认 5000 万）
            filter_st: 是否过滤 ST 股票
        """
        self.volatility_percentile = volatility_percentile
        self.min_daily_turnover = min_daily_turnover
        self.filter_st = filter_st
        
        # ST 股票列表（需要外部提供）
        self.st_stocks = set()
    
    def filter_by_volatility(
        self,
        stock_data: pd.DataFrame,
        volatility_series: pd.Series
    ) -> pd.Series:
        """
        波动率过滤
        
        Args:
            stock_data: 股票数据
            volatility_series: 波动率序列
            
        Returns:
            过滤后的波动率序列
        """
        # 计算波动率分位数
        vol_threshold = volatility_series.quantile(self.volatility_percentile)
        
        # 剔除高波动率股票
        filtered = volatility_series[volatility_series <= vol_threshold]
        
        return filtered
    
    def filter_by_liquidity(
        self,
        turnover_series: pd.Series
    ) -> pd.Series:
        """
        流动性过滤
        
        Args:
            turnover_series: 成交额序列
            
        Returns:
            过滤后的成交额序列
        """
        # 剔除低流动性股票
        filtered = turnover_series[turnover_series >= self.min_daily_turnover]
        
        return filtered
    
    def filter_st_stocks(
        self,
        stock_list: pd.Series
    ) -> pd.Series:
        """
        ST 股票过滤
        
        Args:
            stock_list: 股票列表
            
        Returns:
            过滤后的股票列表
        """
        if not self.filter_st:
            return stock_list
        
        # 剔除 ST 股票
        filtered = stock_list[~stock_list.index.isin(self.st_stocks)]
        
        return filtered
    
    def apply_all_filters(
        self,
        stock_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        应用所有过滤器
        
        Args:
            stock_data: 股票数据（包含 volatility, turnover 等列）
            date: 交易日期
            
        Returns:
            过滤后的股票数据
        """
        filtered = stock_data.copy()
        
        # 1. 波动率过滤
        if 'volatility' in filtered.columns:
            vol_threshold = filtered['volatility'].quantile(self.volatility_percentile)
            filtered = filtered[filtered['volatility'] <= vol_threshold]
        
        # 2. 流动性过滤
        if 'turnover' in filtered.columns:
            filtered = filtered[filtered['turnover'] >= self.min_daily_turnover]
        
        # 3. ST 过滤
        if self.filter_st and len(self.st_stocks) > 0:
            filtered = filtered[~filtered.index.isin(self.st_stocks)]
        
        return filtered


def create_volatility_filter(
    volatility_data: pd.DataFrame,
    lookback_window: int = 20,
    percentile: float = 0.90
) -> pd.DataFrame:
    """
    创建波动率过滤掩码
    
    Args:
        volatility_data: 波动率数据
        lookback_window: 回看窗口
        percentile: 分位数
        
    Returns:
        过滤掩码（True 表示保留）
    """
    # 计算滚动波动率分位数
    vol_threshold = volatility_data.rolling(lookback_window).quantile(percentile)
    
    # 生成掩码
    mask = volatility_data <= vol_threshold
    
    return mask


def create_liquidity_filter(
    turnover_data: pd.DataFrame,
    min_turnover: float = 5e7
) -> pd.DataFrame:
    """
    创建流动性过滤掩码
    
    Args:
        turnover_data: 成交额数据
        min_turnover: 最小成交额
        
    Returns:
        过滤掩码
    """
    mask = turnover_data >= min_turnover
    
    return mask
