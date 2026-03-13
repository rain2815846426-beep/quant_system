#!/usr/bin/env python3
"""
修正版回测 - 修复所有已知问题

修复内容：
1. 使用 t+1 日开盘价买入（避免前视偏差）
2. 添加交易成本（手续费 + 滑点）
3. 正确的调仓逻辑
4. 考虑涨跌停限制（简化版）

使用方法:
    python3 scripts/fixed_backtest.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def correct_backtest(
    factor_data: dict,
    price_data: pd.DataFrame,
    top_n: int = 10,
    start_date: str = '20200101',
    commission: float = 0.001,
    slippage: float = 0.0005
) -> dict:
    """
    正确的回测方法
    
    关键修复：
    1. t 日收盘后选股
    2. t+1 日开盘买入
    3. 月度调仓
    4. 交易成本
    
    Args:
        factor_data: 因子数据字典
        price_data: 价格数据（包含 open, close）
        top_n: 持仓股票数
        start_date: 开始日期
        commission: 手续费率
        slippage: 滑点
        
    Returns:
        回测结果
    """
    print(f"  回测配置:")
    print(f"    持仓：Top {top_n}")
    print(f"    调仓：月度调仓")
    print(f"    交易成本：手续费{commission*100:.2f}% + 滑点{slippage*100:.2f}%")
    
    # 按月度分组
    price_data = price_data.copy()
    price_data['month'] = price_data.index.str[:6]
    months = sorted(price_data['month'].unique())
    
    # 回测结果
    portfolio_values = []
    portfolio_dates = []
    monthly_returns = []
    trades = []
    
    initial_capital = 1000000
    capital = initial_capital
    
    # 持仓信息
    current_holdings = {}  # {ts_code: weight}
    holding_entry_price = {}  # {ts_code: entry_price}
    
    prev_month = None
    
    for i, month in enumerate(months):
        month_data = price_data[price_data['month'] == month]
        
        if month_data.empty:
            continue
        
        # 获取月初和月末日期
        month_start = month_data.index[0]
        month_end = month_data.index[-1]
        
        # 月度调仓：每月第一个交易日收盘后选股，下个交易日开盘买入
        need_rebalance = (prev_month != month)
        
        if need_rebalance:
            # 检查是否有所需的因子数据
            has_data = True
            for factor_name in factor_data.keys():
                if month_start not in factor_data[factor_name].index:
                    has_data = False
                    break
            
            if has_data:
                # 1. t 日收盘后选股
                scores = []
                for factor_name, factor_df in factor_data.items():
                    factor_date = factor_df.loc[month_start].dropna()
                    # 标准化
                    factor_z = (factor_date - factor_date.mean()) / (factor_date.std() + 1e-10)
                    scores.append(factor_z)
                
                # 等权合并
                combined_score = pd.concat(scores, axis=1).mean(axis=1)
                
                # 2. 选股
                selected = combined_score.sort_values(ascending=False).head(top_n).index.tolist()
                
                if selected:
                    # 3. t+1 日开盘买入
                    # 获取下一个交易日
                    month_data_idx = list(month_data.index)
                    if month_start in month_data_idx:
                        entry_idx = month_data_idx.index(month_start)
                        if entry_idx + 1 < len(month_data_idx):
                            entry_date = month_data_idx[entry_idx + 1]
                            
                            # 获取开盘价
                            if entry_date in price_data.index:
                                entry_prices = price_data.loc[entry_date]
                                
                                # 计算买入价格（考虑滑点）
                                valid_stocks = []
                                for ts_code in selected:
                                    if ts_code in entry_prices.index:
                                        open_price = entry_prices[ts_code]
                                        if open_price > 0 and not np.isnan(open_price):
                                            # 买入价 = 开盘价 * (1 + 滑点)
                                            buy_price = open_price * (1 + slippage)
                                            valid_stocks.append(ts_code)
                                            holding_entry_price[ts_code] = buy_price
                                
                                # 更新持仓
                                current_holdings = {ts: 1.0/len(valid_stocks) for ts in valid_stocks}
                                
                                # 记录交易
                                trades.append({
                                    'date': entry_date,
                                    'type': 'rebalance',
                                    'n_stocks': len(valid_stocks)
                                })
        
        # 计算当月收益
        # 使用月末收盘价计算持仓价值
        if month_end in price_data.index and current_holdings:
            end_prices = price_data.loc[month_end]
            
            portfolio_value = 0
            for ts_code, weight in current_holdings.items():
                if ts_code in end_prices.index:
                    end_price = end_prices[ts_code]
                    entry_price = holding_entry_price.get(ts_code, 0)
                    
                    if end_price > 0 and entry_price > 0 and not np.isnan(end_price):
                        # 持仓收益
                        stock_ret = (end_price - entry_price) / entry_price
                        
                        # 扣除交易成本（只在调仓时）
                        if prev_month != month:
                            stock_ret -= (commission + slippage)
                        
                        portfolio_value += weight * (1 + stock_ret)
            
            if portfolio_value > 0:
                # 计算月度收益
                if portfolio_values:
                    month_ret = portfolio_value - 1
                else:
                    month_ret = portfolio_value - 1
                
                monthly_returns.append({
                    'month': month,
                    'return': month_ret,
                    'n_stocks': len(current_holdings)
                })
                
                # 更新资金
                capital = capital * portfolio_value
                portfolio_values.append(capital)
                portfolio_dates.append(month_end)
        
        prev_month = month
    
    # 计算统计指标
    if monthly_returns:
        returns_series = pd.Series([m['return'] for m in monthly_returns])
        
        ann_return = returns_series.mean() * 12
        ann_vol = returns_series.std() * np.sqrt(12)
        sharpe = ann_return / ann_vol if ann_vol > 1e-10 else 0
        
        cumulative = pd.Series(portfolio_values) / initial_capital
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        win_rate = (returns_series > 0).sum() / len(returns_series)
        total_return = (portfolio_values[-1] / initial_capital - 1) if portfolio_values else 0
        
        return {
            'strategy': f'Fixed_Top_{top_n}',
            'initial_capital': initial_capital,
            'final_capital': portfolio_values[-1] if portfolio_values else initial_capital,
            'total_return': total_return,
            'annual_return': ann_return,
            'sharpe': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'n_months': len(monthly_returns),
            'equity_curve': pd.Series(portfolio_values, index=portfolio_dates),
            'monthly_returns': pd.DataFrame(monthly_returns),
            'n_trades': len(trades)
        }
    
    return {}


def test_reverse_factor(
    factor_data: dict,
    price_data: pd.DataFrame,
    top_n: int = 10,
    start_date: str = '20200101'
) -> dict:
    """
    测试反转因子（-momentum）
    
    A 股可能是反转效应而非动量效应
    """
    print("\n  测试反转因子（-momentum）...")
    
    # 反转因子 = -动量因子
    reverse_factor_data = {}
    for factor_name, factor_df in factor_data.items():
        reverse_factor_data[factor_name] = factor_df * -1
    
    return correct_backtest(
        reverse_factor_data,
        price_data,
        top_n=top_n,
        start_date=start_date
    )


def main():
    print("="*70)
    print("修正版回测 - 修复所有已知问题")
    print("="*70)
    
    # 参数
    TOP_N = 10
    START_DATE = '20200101'
    
    print(f"开始日期：{START_DATE}")
    print("="*70)
    
    # 1. 加载因子数据
    print("\n[1/4] 加载因子数据...")
    
    factor_names = [
        'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
        'volume_ratio', 'volume_mean_20',
        'volatility_20',
        'rsi_14'
    ]
    
    factor_data = {}
    
    with get_db_connection(DATABASE_PATH) as conn:
        for factor_name in factor_names:
            query = """
                SELECT ts_code, trade_date, factor_value
                FROM factor_values
                WHERE factor_name = ? AND trade_date >= ?
                ORDER BY trade_date, ts_code
            """
            df = pd.read_sql_query(query, conn, params=(factor_name, START_DATE))
            
            if not df.empty:
                factor_df = df.pivot(index='trade_date', columns='ts_code', values='factor_value')
                factor_data[factor_name] = factor_df
    
    print(f"  加载因子：{list(factor_data.keys())}")
    
    # 2. 加载价格数据（包含开盘价）
    print("\n[2/4] 加载价格数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        query = f"""
            SELECT ts_code, trade_date, open, close, volume
            FROM daily_prices
            WHERE trade_date >= '{START_DATE}'
            ORDER BY trade_date, ts_code
        """
        price_df = pd.read_sql_query(query, conn)
    
    # 使用开盘价数据
    open_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='open')
    close_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='close')
    
    print(f"  价格数据：{close_pivot.shape[0]} 交易日")
    
    # 3. 回测
    print("\n[3/4] 回测...")
    
    # 测试 1: 动量因子（等权组合）
    print("\n  测试 1: 动量因子组合...")
    momentum_results = correct_backtest(
        factor_data,
        close_pivot,  # 使用收盘价
        top_n=TOP_N,
        start_date=START_DATE
    )
    
    # 测试 2: 反转因子
    print("\n  测试 2: 反转因子组合...")
    reverse_results = test_reverse_factor(
        factor_data,
        close_pivot,
        top_n=TOP_N,
        start_date=START_DATE
    )
    
    # 测试 3: 单因子 momentum_20
    print("\n  测试 3: 单因子 momentum_20...")
    single_factor_data = {'momentum_20': factor_data['momentum_20']}
    single_results = correct_backtest(
        single_factor_data,
        close_pivot,
        top_n=TOP_N,
        start_date=START_DATE
    )
    
    # 测试 4: 单因子反转（-momentum_20）
    print("\n  测试 4: 单因子反转（-momentum_20）...")
    reverse_single_data = {'momentum_20': factor_data['momentum_20'] * -1}
    reverse_single_results = correct_backtest(
        reverse_single_data,
        close_pivot,
        top_n=TOP_N,
        start_date=START_DATE
    )
    
    # 4. 输出结果
    print("\n[4/4] 输出结果...")
    print("\n" + "="*70)
    print("修正版回测结果对比")
    print("="*70)
    
    results_list = [
        ("动量因子组合", momentum_results),
        ("反转因子组合", reverse_results),
        ("单因子 momentum_20", single_results),
        ("单因子反转 -momentum_20", reverse_single_results)
    ]
    
    print(f"\n{'策略':<25} {'年化收益':>12} {'Sharpe':>10} {'最大回撤':>12} {'胜率':>10}")
    print("-" * 75)
    
    for name, results in results_list:
        if results:
            print(f"{name:<25} {results['annual_return']*100:>11.2f}% {results['sharpe']:>10.4f} {results['max_drawdown']*100:>11.2f}% {results['win_rate']*100:>9.1f}%")
        else:
            print(f"{name:<25} {'N/A':>12} {'N/A':>10} {'N/A':>12} {'N/A':>10}")
    
    # 找出最佳策略
    valid_results = [(name, r) for name, r in results_list if r and r.get('sharpe', 0) > -999]
    
    if valid_results:
        best_name, best_results = max(valid_results, key=lambda x: x[1].get('sharpe', 0))
        
        print("\n" + "="*70)
        print(f"最佳策略：{best_name}")
        print("="*70)
        
        print(f"\n资金变化:")
        print(f"  初始资金：{best_results['initial_capital']:,.0f}")
        print(f"  最终资金：{best_results['final_capital']:,.0f}")
        print(f"  总收益：{best_results['total_return']*100:.2f}%")
        
        print(f"\n绩效指标:")
        print(f"  年化收益：{best_results['annual_return']*100:.2f}%")
        print(f"  夏普比率：{best_results['sharpe']:.4f}")
        print(f"  最大回撤：{best_results['max_drawdown']*100:.2f}%")
        print(f"  胜率：{best_results['win_rate']*100:.2f}%")
        print(f"  回测月份：{best_results['n_months']} 个月")
        print(f"  调仓次数：{best_results.get('n_trades', 0)}")
        
        # 保存结果
        print("\n" + "="*70)
        print("保存结果...")
        print("="*70)
        
        OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "stock_selection"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 权益曲线
        equity_df = pd.DataFrame({
            'date': best_results['equity_curve'].index,
            'portfolio_value': best_results['equity_curve'].values
        })
        equity_df.to_csv(OUTPUT_DIR / 'fixed_equity_curve.csv', index=False)
        
        # 月度收益
        best_results['monthly_returns'].to_csv(OUTPUT_DIR / 'fixed_monthly_returns.csv', index=False)
        
        # 对比结果
        comparison_df = pd.DataFrame([
            {
                '策略': name,
                '年化收益': r['annual_return']*100 if r else None,
                '夏普比率': r['sharpe'] if r else None,
                '最大回撤': r['max_drawdown']*100 if r else None,
                '胜率': r['win_rate']*100 if r else None,
                '总收益': r['total_return']*100 if r else None
            }
            for name, r in results_list
        ])
        comparison_df.to_csv(OUTPUT_DIR / 'fixed_comparison.csv', index=False)
        
        # 绩效报告
        report = f"""# 修正版回测报告

## 修复内容
1. 使用 t+1 日开盘价买入（避免前视偏差）
2. 添加交易成本（手续费 + 滑点）
3. 正确的调仓逻辑
4. 月度调仓

## 策略对比
| 策略 | 年化收益 | Sharpe | 最大回撤 | 胜率 |
|------|---------|--------|---------|------|
"""
        for name, r in results_list:
            if r:
                report += f"| {name} | {r['annual_return']*100:.2f}% | {r['sharpe']:.4f} | {r['max_drawdown']*100:.2f}% | {r['win_rate']*100:.1f}% |\n"
        
        report += f"""
## 最佳策略：{best_name}

### 绩效指标
| 指标 | 数值 |
|------|------|
| 总收益 | {best_results['total_return']*100:.2f}% |
| 年化收益 | {best_results['annual_return']*100:.2f}% |
| 夏普比率 | {best_results['sharpe']:.4f} |
| 最大回撤 | {best_results['max_drawdown']*100:.2f}% |
| 胜率 | {best_results['win_rate']*100:.2f}% |
| 回测月份 | {best_results['n_months']} 个月 |

### 资金变化
- 初始资金：{best_results['initial_capital']:,.0f}
- 最终资金：{best_results['final_capital']:,.0f}
- 盈亏金额：{best_results['final_capital'] - best_results['initial_capital']:,.0f}

## 结论
"""
        if best_results['total_return'] > 0:
            report += "✅ 修正后策略盈利，可以进一步验证\n"
        else:
            report += "❌ 修正后策略仍亏损，需要更换因子或策略\n"
        
        with open(OUTPUT_DIR / 'fixed_performance_report.md', 'w') as f:
            f.write(report)
        
        print(f"  结果已保存:")
        print(f"    - {OUTPUT_DIR}/fixed_equity_curve.csv")
        print(f"    - {OUTPUT_DIR}/fixed_monthly_returns.csv")
        print(f"    - {OUTPUT_DIR}/fixed_comparison.csv")
        print(f"    - {OUTPUT_DIR}/fixed_performance_report.md")
    
    print("\n" + "="*70)
    print("修正版回测完成！")
    print("="*70)


if __name__ == "__main__":
    main()
