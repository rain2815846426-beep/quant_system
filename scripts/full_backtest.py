#!/usr/bin/env python3
"""
完整的选股回测脚本

使用真实的选股数据和价格数据进行回测
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

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "stock_selection"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_selection_data(
    db_path=DATABASE_PATH,
    factor_name: str = 'momentum_20',
    start_date: str = '20200101',
    top_n: int = 10
) -> pd.DataFrame:
    """
    基于因子值生成选股数据
    """
    with get_db_connection(db_path) as conn:
        query = """
            SELECT ts_code, trade_date, factor_value
            FROM factor_values
            WHERE factor_name = ? AND trade_date >= ?
            ORDER BY trade_date, ts_code
        """
        df = pd.read_sql_query(query, conn, params=(factor_name, start_date))
    
    # Pivot
    factor_df = df.pivot(index='trade_date', columns='ts_code', values='factor_value')
    
    # 每日选股
    selections = []
    
    for date in factor_df.index:
        factor_date = factor_df.loc[date].dropna()
        
        # 排序选股
        top_stocks = factor_date.sort_values(ascending=False).head(top_n)
        
        for ts_code in top_stocks.index:
            selections.append({
                'trade_date': date,
                'ts_code': ts_code,
                'factor_value': top_stocks[ts_code],
                'rank': list(top_stocks.index).index(ts_code) + 1
            })
    
    return pd.DataFrame(selections)


def backtest_monthly_rebalance(
    selection_data: pd.DataFrame,
    price_data: pd.DataFrame,
    top_n: int = 10,
    start_date: str = '20200101'
) -> dict:
    """
    月度调仓回测
    
    Args:
        selection_data: 选股数据
        price_data: 价格数据
        top_n: 持仓股票数
        start_date: 开始日期
        
    Returns:
        回测结果字典
    """
    # 按月度分组
    selection_data['month'] = selection_data['trade_date'].str[:6]
    
    # 获取唯一月份
    months = selection_data['month'].unique()
    months = sorted(months)
    
    # 回测结果
    portfolio_values = []
    portfolio_dates = []
    monthly_returns = []
    
    initial_capital = 1000000  # 100 万初始资金
    capital = initial_capital
    
    prev_month = None
    current_holdings = {}  # {ts_code: weight}
    
    for month in months:
        # 月度调仓
        month_data = selection_data[selection_data['month'] == month]
        
        # 获取月初日期
        month_start = month_data['trade_date'].min()
        
        # 获取当月持仓股票（等权）
        stocks = month_data['ts_code'].unique()[:top_n]
        weight = 1.0 / len(stocks) if len(stocks) > 0 else 0
        
        # 计算当月收益
        # 简化：使用月末价格计算
        month_end = month_data['trade_date'].max()
        
        # 获取价格
        month_start_price = price_data.loc[month_start] if month_start in price_data.index else None
        month_end_price = price_data.loc[month_end] if month_end in price_data.index else None
        
        if month_start_price is None or month_end_price is None:
            continue
        
        # 计算持仓收益
        portfolio_ret = 0
        n_valid = 0
        for ts_code in stocks:
            if ts_code in month_start_price.index and ts_code in month_end_price.index:
                start_p = month_start_price[ts_code]
                end_p = month_end_price[ts_code]
                if start_p > 0 and end_p > 0 and not np.isnan(start_p) and not np.isnan(end_p):
                    stock_ret = (end_p - start_p) / start_p
                    portfolio_ret += weight * stock_ret
                    n_valid += 1
        
        # 如果没有有效收益，跳过
        if n_valid == 0:
            continue
        
        monthly_returns.append({
            'month': month,
            'return': portfolio_ret,
            'n_stocks': len(stocks)
        })
        
        # 更新资产
        capital = capital * (1 + portfolio_ret)
        portfolio_values.append(capital)
        portfolio_dates.append(month_end)
    
    # 计算统计指标
    returns_series = pd.Series([m['return'] for m in monthly_returns])
    
    # 年化收益
    ann_return = returns_series.mean() * 12
    
    # 年化波动率
    ann_vol = returns_series.std() * np.sqrt(12)
    
    # 夏普比率
    sharpe = ann_return / ann_vol if ann_vol > 1e-10 else 0
    
    # 最大回撤
    cumulative = pd.Series(portfolio_values) / initial_capital
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()
    
    # 胜率
    win_rate = (returns_series > 0).sum() / len(returns_series)
    
    # 总收益
    total_return = (portfolio_values[-1] / initial_capital - 1) if portfolio_values else 0
    
    return {
        'strategy': f'Top_{top_n}',
        'initial_capital': initial_capital,
        'final_capital': portfolio_values[-1] if portfolio_values else initial_capital,
        'total_return': total_return,
        'annual_return': ann_return,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'win_rate': win_rate,
        'n_months': len(monthly_returns),
        'equity_curve': pd.Series(portfolio_values, index=portfolio_dates),
        'monthly_returns': pd.DataFrame(monthly_returns)
    }


def save_backtest_results(results: dict, output_dir: Path):
    """保存回测结果"""
    
    # 1. 权益曲线
    equity_df = pd.DataFrame({
        'date': results['equity_curve'].index,
        'portfolio_value': results['equity_curve'].values
    })
    equity_df.to_csv(output_dir / 'backtest_equity_curve.csv', index=False)
    
    # 2. 月度收益
    results['monthly_returns'].to_csv(output_dir / 'monthly_returns.csv', index=False)
    
    # 3. 绩效报告
    report = f"""# 量化选股回测报告

## 策略信息
- 策略名称：{results['strategy']}
- 初始资金：{results['initial_capital']:,.0f}
- 回测月份：{results['n_months']} 个月

## 绩效指标
| 指标 | 数值 |
|------|------|
| 总收益 | {results['total_return']*100:.2f}% |
| 年化收益 | {results['annual_return']*100:.2f}% |
| 年化波动率 | {results.get('ann_vol', 0)*100:.2f}% |
| 夏普比率 | {results['sharpe']:.4f} |
| 最大回撤 | {results['max_drawdown']*100:.2f}% |
| 胜率 | {results['win_rate']*100:.2f}% |

## 资金变化
- 初始资金：{results['initial_capital']:,.0f}
- 最终资金：{results['final_capital']:,.0f}
- 盈亏金额：{results['final_capital'] - results['initial_capital']:,.0f}

## 说明
- 调仓周期：月度调仓
- 持仓股票：Top 10
- 权重方式：等权
- 回测期间：{results['equity_curve'].index[0]} 至 {results['equity_curve'].index[-1]}
"""
    
    with open(output_dir / 'performance_report.md', 'w') as f:
        f.write(report)
    
    print(f"回测结果已保存：{output_dir}")


def main():
    print("="*70)
    print("量化选股回测系统")
    print("="*70)
    
    # 参数
    FACTOR_NAME = 'momentum_20'
    TOP_N = 10
    START_DATE = '20200101'
    
    print(f"因子：{FACTOR_NAME}")
    print(f"持仓：Top {TOP_N}")
    print(f"开始日期：{START_DATE}")
    print("="*70)
    
    # 1. 加载选股数据
    print("\n[1/3] 加载选股数据...")
    selection_data = load_selection_data(
        factor_name=FACTOR_NAME,
        start_date=START_DATE,
        top_n=TOP_N
    )
    print(f"  选股记录：{len(selection_data)} 条")
    
    # 2. 加载价格数据
    print("\n[2/3] 加载价格数据...")
    with get_db_connection(DATABASE_PATH) as conn:
        query = f"""
            SELECT ts_code, trade_date, close
            FROM daily_prices
            WHERE trade_date >= '{START_DATE}'
            ORDER BY trade_date, ts_code
        """
        price_df = pd.read_sql_query(query, conn)
    
    price_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='close')
    print(f"  价格数据：{price_pivot.shape[0]} 交易日 x {price_pivot.shape[1]} 股票")
    
    # 3. 回测
    print("\n[3/3] 回测...")
    results = backtest_monthly_rebalance(
        selection_data,
        price_pivot,
        top_n=TOP_N,
        start_date=START_DATE
    )
    
    # 4. 输出结果
    print("\n" + "="*70)
    print("回测结果")
    print("="*70)
    
    print(f"\n资金变化:")
    print(f"  初始资金：{results['initial_capital']:,.0f}")
    print(f"  最终资金：{results['final_capital']:,.0f}")
    print(f"  总收益：{results['total_return']*100:.2f}%")
    
    print(f"\n绩效指标:")
    print(f"  年化收益：{results['annual_return']*100:.2f}%")
    print(f"  夏普比率：{results['sharpe']:.4f}")
    print(f"  最大回撤：{results['max_drawdown']*100:.2f}%")
    print(f"  胜率：{results['win_rate']*100:.2f}%")
    print(f"  回测月份：{results['n_months']} 个月")
    
    # 5. 保存结果
    print("\n" + "="*70)
    print("保存结果...")
    print("="*70)
    save_backtest_results(results, OUTPUT_DIR)
    
    print("\n" + "="*70)
    print("回测完成！")
    print("="*70)
    print(f"\n查看结果:")
    print(f"  1. 绩效报告：{OUTPUT_DIR}/performance_report.md")
    print(f"  2. 权益曲线：{OUTPUT_DIR}/backtest_equity_curve.csv")
    print(f"  3. 月度收益：{OUTPUT_DIR}/monthly_returns.csv")


if __name__ == "__main__":
    main()
