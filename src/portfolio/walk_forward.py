"""
Walk Forward 回测模块

滚动训练测试，避免过拟合
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class WalkForwardBacktester:
    """Walk Forward 回测器"""
    
    def __init__(
        self,
        train_window: int = 252 * 3,  # 3 年训练
        test_window: int = 252,       # 1 年测试
        step: int = 252               # 每年滚动一次
    ):
        """
        初始化
        
        Args:
            train_window: 训练窗口（交易日）
            test_window: 测试窗口（交易日）
            step: 滚动步长
        """
        self.train_window = train_window
        self.test_window = test_window
        self.step = step
    
    def generate_periods(
        self,
        dates: pd.DatetimeIndex
    ) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
        """
        生成训练测试期间
        
        Args:
            dates: 日期范围
            
        Returns:
            [(train_dates, test_dates), ...]
        """
        periods = []
        
        n_dates = len(dates)
        start_idx = 0
        
        while start_idx + self.train_window + self.test_window <= n_dates:
            # 训练期
            train_start = start_idx
            train_end = start_idx + self.train_window
            
            # 测试期
            test_start = train_end
            test_end = train_end + self.test_window
            
            train_dates = dates[train_start:train_end]
            test_dates = dates[test_start:test_end]
            
            periods.append((train_dates, test_dates))
            
            # 滚动
            start_idx += self.step
        
        return periods
    
    def backtest(
        self,
        factor_data: pd.DataFrame,
        forward_returns: pd.DataFrame,
        model_func,
        **kwargs
    ) -> Dict:
        """
        Walk Forward 回测
        
        Args:
            factor_data: 因子数据
            forward_returns: 未来收益
            model_func: 模型训练函数
            
        Returns:
            回测结果
        """
        dates = factor_data.index
        
        # 生成期间
        periods = self.generate_periods(dates)
        
        all_test_returns = []
        all_test_dates = []
        
        # 逐期回测
        for train_dates, test_dates in periods:
            print(f"训练期：{train_dates[0]} - {train_dates[-1]}")
            print(f"测试期：{test_dates[0]} - {test_dates[-1]}")
            
            # 训练数据
            train_factors = factor_data.loc[train_dates]
            train_returns = forward_returns.loc[train_dates]
            
            # 训练模型
            model = model_func(train_factors, train_returns, **kwargs)
            
            # 测试数据
            test_factors = factor_data.loc[test_dates]
            test_returns = forward_returns.loc[test_dates]
            
            # 预测
            predictions = model.predict(test_factors)
            
            # 计算收益
            if predictions is not None:
                period_returns = self.calculate_strategy_returns(
                    predictions, test_returns
                )
                all_test_returns.extend(period_returns)
                all_test_dates.extend(test_dates)
        
        return {
            'returns': pd.Series(all_test_returns, index=all_test_dates),
            'periods': periods
        }
    
    def calculate_strategy_returns(
        self,
        predictions: pd.Series,
        actual_returns: pd.DataFrame
    ) -> pd.Series:
        """
        计算策略收益
        
        Args:
            predictions: 预测值
            actual_returns: 实际收益
            
        Returns:
            策略收益
        """
        # 简化：按预测值排序，做多前 10%，做空后 10%
        strategy_returns = []
        
        for date in predictions.index:
            if date not in actual_returns.index:
                strategy_returns.append(np.nan)
                continue
            
            pred_date = predictions.loc[date]
            ret_date = actual_returns.loc[date]
            
            # 对齐
            common = pred_date.index.intersection(ret_date.index)
            
            if len(common) < 10:
                strategy_returns.append(np.nan)
                continue
            
            # 排序
            pred_sorted = pred_date.loc[common].sort_values(ascending=False)
            
            n = len(pred_sorted)
            n_top = max(1, int(n * 0.1))
            
            # 多头
            long_stocks = pred_sorted.head(n_top).index
            long_ret = ret_date.loc[long_stocks].mean()
            
            # 空头
            short_stocks = pred_sorted.tail(n_top).index
            short_ret = ret_date.loc[short_stocks].mean()
            
            # 多空收益
            strategy_ret = long_ret - short_ret
            strategy_returns.append(strategy_ret)
        
        return strategy_returns


def calculate_portfolio_statistics(returns: pd.Series) -> Dict:
    """
    计算组合统计指标
    
    Args:
        returns: 收益时间序列
        
    Returns:
        统计指标字典
    """
    if len(returns) < 10:
        return {}
    
    # 年化收益
    ann_return = returns.mean() * 252
    
    # 年化波动率
    ann_vol = returns.std() * np.sqrt(252)
    
    # 夏普比率
    sharpe = ann_return / ann_vol if ann_vol > 1e-10 else np.nan
    
    # 最大回撤
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()
    
    # 胜率
    win_rate = (returns > 0).sum() / len(returns)
    
    # 盈亏比
    avg_win = returns[returns > 0].mean() if (returns > 0).sum() > 0 else np.nan
    avg_loss = returns[returns < 0].mean() if (returns < 0).sum() > 0 else np.nan
    profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.nan
    
    return {
        'annual_return': ann_return,
        'annual_vol': ann_vol,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'n_periods': len(returns)
    }
