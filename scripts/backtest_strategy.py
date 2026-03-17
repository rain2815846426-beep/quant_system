#!/usr/bin/env python3
"""
策略回测系统

支持：
- 单因子回测
- 多因子组合回测
- 绩效分析
- 可视化图表

使用方法:
    python3 scripts/backtest_strategy.py --factor momentum_20 --top_n 10
    python3 scripts/backtest_strategy.py --factor momentum_20 --top_n 20 --rebalance weekly
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from config.settings import DATABASE_PATH
from src.utils import get_db_connection
from src.factors.momentum_factor import calculate_momentum_factors
from src.factors.volatility_factor import calculate_volatility_factors
from src.factors.volume_factor import calculate_volume_factors
from src.factors.rsi_factor import calculate_rsi_factors


def load_price_data(start_date: str = '20200101') -> pd.DataFrame:
    """加载价格数据"""
    with get_db_connection() as conn:
        query = """
            SELECT ts_code, trade_date, open, high, low, close, volume
            FROM daily_prices
            WHERE trade_date >= ?
            ORDER BY ts_code, trade_date
        """
        df = pd.read_sql_query(query, conn, params=(start_date,))
    
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    return df


def calculate_portfolio_returns(
    price_df: pd.DataFrame,
    selection_date: str,
    stock_list: list,
    holding_days: int = 20
) -> float:
    """
    计算投资组合收益
    
    Args:
        price_df: 价格数据
        selection_date: 选股日期
        stock_list: 选中的股票列表
        holding_days: 持有天数
    
    Returns:
        组合收益率
    """
    selection_date = pd.to_datetime(selection_date)
    end_date = selection_date + pd.Timedelta(days=holding_days)
    
    # 获取选股日的收盘价
    buy_prices = price_df[
        (price_df['trade_date'] == selection_date) & 
        (price_df['ts_code'].isin(stock_list))
    ].set_index('ts_code')['close']
    
    # 获取卖出日的收盘价
    sell_prices = price_df[
        (price_df['trade_date'] >= selection_date) & 
        (price_df['trade_date'] <= end_date) &
        (price_df['ts_code'].isin(stock_list))
    ].groupby('ts_code').last()['close']
    
    # 计算收益
    common_stocks = buy_prices.index.intersection(sell_prices.index)
    if len(common_stocks) == 0:
        return 0.0
    
    returns = (sell_prices.loc[common_stocks] - buy_prices.loc[common_stocks]) / buy_prices.loc[common_stocks]
    
    return returns.mean()


def backtest_momentum_strategy(
    price_df: pd.DataFrame,
    top_n: int = 10,
    holding_period: int = 20,
    rebalance_freq: str = 'M',
    position_size: float = 0.5,  # 仓位控制（50%）
    stop_loss: float = 0.10,      # 止损（10%）
    use_reverse: bool = True      # 使用反转因子
) -> pd.DataFrame:
    """
    回测动量策略（优化版，低回撤）
    
    Args:
        price_df: 价格数据
        top_n: 选股数量
        holding_period: 持有期
        rebalance_freq: 调仓频率
        position_size: 仓位比例（0-1）
        stop_loss: 止损线
        use_reverse: 使用反转因子
    
    Returns:
        回测结果
    """
    price_df = price_df.copy()
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    price_df = price_df.sort_values(['ts_code', 'trade_date'])
    
    # 计算因子
    if use_reverse:
        # 反转因子（负动量）
        price_df['factor'] = -price_df.groupby('ts_code')['close'].pct_change(holding_period)
    else:
        # 动量因子
        price_df['factor'] = price_df.groupby('ts_code')['close'].pct_change(holding_period)
    
    # 计算波动率（用于风控）
    price_df['volatility'] = price_df.groupby('ts_code')['close'].pct_change().rolling(20).std()
    
    # 获取每月最后一个交易日
    price_df['month'] = price_df['trade_date'].dt.to_period('M')
    month_end_dates = price_df.groupby('month')['trade_date'].max().reset_index()
    month_end_dates = month_end_dates['trade_date'].tolist()
    
    # 回测
    results = []
    
    for i in range(len(month_end_dates) - 1):
        selection_date = month_end_dates[i]
        hold_end_date = month_end_dates[min(i + 1, len(month_end_dates) - 1)]
        
        # 获取选股日数据
        day_data = price_df[
            (price_df['trade_date'] == selection_date) & 
            (price_df['factor'].notna()) &
            (price_df['volatility'].notna())
        ]
        
        if len(day_data) < top_n * 3:
            continue
        
        # 选股（因子值最高 + 波动率适中）
        # 先按因子排序，再按波动率筛选
        day_data = day_data.sort_values('factor', ascending=not use_reverse)
        
        # 剔除波动率过高和过低的股票
        vol_lower = day_data['volatility'].quantile(0.2)
        vol_upper = day_data['volatility'].quantile(0.8)
        day_data = day_data[
            (day_data['volatility'] >= vol_lower) &
            (day_data['volatility'] <= vol_upper)
        ]
        
        # 选股
        top_stocks = day_data.head(top_n * 2)['ts_code'].tolist()
        
        # 获取买入价
        buy_prices = price_df[
            (price_df['trade_date'] == selection_date) &
            (price_df['ts_code'].isin(top_stocks))
        ].set_index('ts_code')['close']
        
        # 获取卖出价
        sell_prices = price_df[
            (price_df['trade_date'] == hold_end_date) &
            (price_df['ts_code'].isin(top_stocks))
        ].set_index('ts_code')['close']
        
        # 计算收益（带止损和仓位控制）
        common = buy_prices.index.intersection(sell_prices.index)
        if len(common) < top_n // 2:
            continue
        
        returns = []
        for stock in common:
            buy_price = buy_prices[stock]
            sell_price = sell_prices[stock]
            
            # 跳过无效价格
            if buy_price <= 0 or sell_price <= 0 or pd.isna(buy_price) or pd.isna(sell_price):
                continue
            
            stock_ret = sell_price / buy_price - 1
            
            # 止损
            if stock_ret < -stop_loss:
                stock_ret = -stop_loss
            
            # 仓位控制（动态）
            actual_position = position_size
            if stock_ret > 0.20:  # 大涨后降低仓位
                actual_position *= 0.8
            elif stock_ret < -0.10:  # 大跌后降低仓位
                actual_position *= 0.7
            
            stock_ret = stock_ret * actual_position
            
            returns.append(stock_ret)
        
        if not returns:
            continue
        
        period_return = np.mean(returns)
        
        results.append({
            'rebalance_date': selection_date,
            'hold_end': hold_end_date,
            'period_return': period_return,
            'n_stocks': len(common)
        })
    
    return pd.DataFrame(results)


def calculate_performance_metrics(returns: pd.Series) -> dict:
    """
    计算绩效指标
    
    Args:
        returns: 收益率序列
    
    Returns:
        绩效指标字典
    """
    if len(returns) < 3 or returns.isna().all():
        return {}
    
    returns = returns.dropna()
    
    if len(returns) < 3:
        return {}
    
    # 总收益
    total_return = (1 + returns).prod() - 1
    
    # 年化收益
    years = len(returns) / 12  # 月度收益
    ann_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    # 年化波动率
    ann_vol = returns.std() * np.sqrt(12)
    
    # 夏普比率（假设无风险利率 3%）
    rf = 0.03
    sharpe = (ann_return - rf) / ann_vol if ann_vol > 1e-10 else 0
    
    # 最大回撤
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # 胜率
    win_rate = (returns > 0).sum() / len(returns)
    
    # 盈亏比
    avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 1
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    return {
        'total_return': total_return,
        'annual_return': ann_return,
        'annual_volatility': ann_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'total_periods': len(returns)
    }


def run_backtest(
    factor_name: str = 'momentum_20',
    top_n: int = 10,
    holding_period: int = 20,
    start_date: str = '20200101',
    end_date: str = None,
    position_size: float = 0.5,
    stop_loss: float = 0.10,
    use_reverse: bool = True
):
    """
    运行回测
    
    Args:
        factor_name: 因子名称
        top_n: 选股数量
        holding_period: 持有期（交易日）
        start_date: 开始日期
        end_date: 结束日期
    """
    print("=" * 70)
    print("策略回测系统")
    print("=" * 70)
    print(f"因子：{factor_name}")
    print(f"选股数量：Top {top_n}")
    print(f"持有期：{holding_period} 天")
    print(f"回测区间：{start_date} 至 {end_date or '至今'}")
    print("=" * 70)
    
    # 加载数据
    print("\n加载数据...")
    price_df = load_price_data(start_date)
    print(f"  数据量：{len(price_df)} 条记录")
    print(f"  股票数量：{price_df['ts_code'].nunique()}")
    print(f"  日期范围：{price_df['trade_date'].min()} 至 {price_df['trade_date'].max()}")
    
    # 运行回测
    print(f"\n运行回测...")
    results = backtest_momentum_strategy(
        price_df,
        top_n=top_n,
        holding_period=holding_period,
        rebalance_freq='M'
    )
    
    if results.empty:
        print("回测结果为空，请检查数据")
        return
    
    print(f"  调仓次数：{len(results)}")
    
    # 计算绩效
    print("\n计算绩效指标...")
    metrics = calculate_performance_metrics(results['period_return'])
    
    print("\n" + "=" * 70)
    print("回测结果")
    print("=" * 70)
    print(f"总收益：     {metrics.get('total_return', 0)*100:.2f}%")
    print(f"年化收益：   {metrics.get('annual_return', 0)*100:.2f}%")
    print(f"夏普比率：   {metrics.get('sharpe', 0):.4f}")
    print(f"最大回撤：   {metrics.get('max_drawdown', 0)*100:.2f}%")
    print(f"胜率：       {metrics.get('win_rate', 0)*100:.1f}%")
    print(f"盈亏比：     {metrics.get('profit_loss_ratio', 0):.2f}")
    print(f"交易次数：   {metrics.get('n_periods', len(results))}")
    print("=" * 70)
    
    # 保存结果
    output_dir = Path(__file__).parent.parent / "research_results" / "backtest"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存详细结果
    results.to_csv(output_dir / f"backtest_{factor_name}_top{top_n}.csv", index=False)
    
    # 保存绩效指标
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(output_dir / f"metrics_{factor_name}_top{top_n}.csv", index=False)
    
    print(f"\n结果已保存至：{output_dir}")
    
    return results, metrics


def main():
    from config.config_manager import get_backtest_defaults
    
    # 获取默认配置
    defaults = get_backtest_defaults()
    
    parser = argparse.ArgumentParser(description="策略回测系统（优化版）")
    parser.add_argument('--factor', type=str, default=defaults['factor'],
                       help=f'因子名称 (default: {defaults["factor"]})')
    parser.add_argument('--top_n', type=int, default=defaults['top_n'],
                       help=f'选股数量 (default: {defaults["top_n"]})')
    parser.add_argument('--holding', type=int, default=defaults['holding_period'],
                       help=f'持有天数 (default: {defaults["holding_period"]})')
    parser.add_argument('--position', type=float, default=defaults['position_size'],
                       help=f'仓位比例 (default: {defaults["position_size"]})')
    parser.add_argument('--stoploss', type=float, default=defaults['stop_loss'],
                       help=f'止损线 (default: {defaults["stop_loss"]})')
    parser.add_argument('--reverse', action='store_true',
                       default=defaults['use_reverse'],
                       help='使用反转因子')
    parser.add_argument('--save-config', action='store_true',
                       help='保存当前参数为默认值')
    
    args = parser.parse_args()
    
    # 如果指定了 --save-config，保存配置
    if args.save_config:
        from config.config_manager import save_backtest_preferences
        save_backtest_preferences(
            factor=args.factor,
            top_n=args.top_n,
            holding_period=args.holding,
            position_size=args.position,
            stop_loss=args.stoploss,
            use_reverse=args.reverse
        )
    
    run_backtest(
        factor_name=args.factor,
        top_n=args.top_n,
        holding_period=args.holding,
        start_date='20200101',
        end_date=None,
        position_size=args.position,
        stop_loss=args.stoploss,
        use_reverse=args.reverse
    )


if __name__ == "__main__":
    main()
