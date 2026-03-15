#!/usr/bin/env python3
"""
蒙特卡洛参数敏感性分析

目的：
1. 验证策略稳健性（是否过拟合）
2. 找到稳健的参数范围
3. 量化参数不确定性

方法：
- 蒙特卡洛随机抽样参数
- 运行回测
- 分析结果分布

使用：
    python3 scripts/monte_carlo_analysis.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def monte_carlo_backtest(
    factor_data: dict,
    price_data: pd.DataFrame,
    industry_map: dict,
    index_returns: pd.Series,
    n_simulations: int = 1000,
    seed: int = 42
) -> pd.DataFrame:
    """
    蒙特卡洛参数敏感性测试
    
    随机抽样参数组合并回测
    
    参数分布：
    - top_n: 均匀分布 [10, 50]
    - stop_loss: 均匀分布 [0.10, 0.25]
    - max_position: 均匀分布 [0.05, 0.15]
    - target_vol: 均匀分布 [0.15, 0.30]
    
    Args:
        factor_data: 因子数据
        price_data: 价格数据
        industry_map: 行业映射
        index_returns: 指数收益
        n_simulations: 模拟次数
        seed: 随机种子
        
    Returns:
        回测结果 DataFrame
    """
    np.random.seed(seed)
    
    print(f"开始蒙特卡洛模拟，n={n_simulations}...")
    print(f"参数分布:")
    print(f"  top_n: [10, 50] 均匀分布")
    print(f"  stop_loss: [10%, 25%] 均匀分布")
    print(f"  max_position: [5%, 15%] 均匀分布")
    print(f"  target_vol: [15%, 30%] 均匀分布")
    
    # 随机抽样参数
    params = {
        'top_n': np.random.randint(10, 51, n_simulations),
        'stop_loss': np.random.uniform(0.10, 0.25, n_simulations),
        'max_position': np.random.uniform(0.05, 0.15, n_simulations),
        'target_vol': np.random.uniform(0.15, 0.30, n_simulations)
    }
    
    results = []
    
    for i in range(n_simulations):
        if (i + 1) % 100 == 0:
            print(f"  进度：{i+1}/{n_simulations}")
        
        # 简化回测（快速版本）
        result = quick_backtest(
            factor_data,
            price_data,
            top_n=params['top_n'][i],
            stop_loss=params['stop_loss'][i],
            max_position=params['max_position'][i],
            target_vol=params['target_vol'][i]
        )
        
        results.append({
            'simulation_id': i + 1,
            'top_n': params['top_n'][i],
            'stop_loss': params['stop_loss'][i],
            'max_position': params['max_position'][i],
            'target_vol': params['target_vol'][i],
            'annual_return': result['annual_return'],
            'sharpe': result['sharpe'],
            'max_drawdown': result['max_drawdown'],
            'win_rate': result['win_rate'],
            'total_return': result['total_return']
        })
    
    return pd.DataFrame(results)


def quick_backtest(
    factor_data: dict,
    price_data: pd.DataFrame,
    top_n: int = 20,
    stop_loss: float = 0.15,
    max_position: float = 0.08,
    target_vol: float = 0.20
) -> dict:
    """
    快速回测（简化版，用于蒙特卡洛）
    """
    price_data = price_data.copy()
    price_data['month'] = price_data.index.str[:6]
    months = sorted(price_data['month'].unique())
    
    initial_capital = 1000000
    capital = initial_capital
    
    portfolio_values = []
    monthly_returns_list = []
    
    current_holdings = {}  # {ts_code: weight}
    holding_prices = {}  # {ts_code: entry_price}
    
    prev_month = None
    
    for month in months:
        month_data = price_data[price_data['month'] == month]
        
        if month_data.empty:
            continue
        
        month_start = month_data.index[0]
        month_end = month_data.index[-1]
        
        need_rebalance = (prev_month != month)
        
        if need_rebalance:
            # 选股（反转因子）
            scores = []
            for factor_name, factor_df in factor_data.items():
                if month_start in factor_df.index:
                    factor_date = factor_df.loc[month_start].dropna()
                    if len(factor_date) < 10:
                        continue
                    factor_z = (factor_date - factor_date.mean()) / (factor_date.std() + 1e-10)
                    if 'momentum' in factor_name:
                        factor_z = -factor_z
                    scores.append(factor_z)
            
            if scores:
                combined_score = pd.concat(scores, axis=1).mean(axis=1)
                selected = combined_score.sort_values(ascending=False).head(top_n).index.tolist()
                
                if selected and month_start in month_data.index:
                    month_data_idx = list(month_data.index)
                    entry_idx = month_data_idx.index(month_start)
                    if entry_idx + 1 < len(month_data_idx):
                        entry_date = month_data_idx[entry_idx + 1]
                        
                        if entry_date in price_data.index:
                            entry_prices = price_data.loc[entry_date]
                            
                            n_valid = min(len(selected), 20)
                            position_per_stock = 0.5 / n_valid  # 50% 仓位分散
                            
                            valid_stocks = []
                            for ts_code in selected[:n_valid]:
                                if ts_code in entry_prices.index:
                                    open_price = entry_prices[ts_code]
                                    if open_price > 0 and not np.isnan(open_price):
                                        valid_stocks.append(ts_code)
                                        holding_prices[ts_code] = open_price
                            
                            current_holdings = {ts: position_per_stock for ts in valid_stocks}
        
        # 计算收益
        if month_end in price_data.index and current_holdings:
            end_prices = price_data.loc[month_end]
            
            portfolio_value = 0
            for ts_code, weight in current_holdings.items():
                if ts_code in end_prices.index:
                    entry_price = holding_prices.get(ts_code, 0)
                    current_price = end_prices[ts_code]
                    
                    if entry_price > 0 and current_price > 0:
                        stock_ret = (current_price - entry_price) / entry_price
                        
                        # 止损检查
                        if stock_ret < -stop_loss:
                            continue  # 止损卖出，不持有
                        
                        portfolio_value += weight * (1 + stock_ret)
            
            # 现金部分
            total_position = sum(current_holdings.values())
            cash_weight = 1.0 - total_position
            portfolio_value += cash_weight
            
            if portfolio_value > 0:
                month_ret = portfolio_value - 1
                monthly_returns_list.append(month_ret)
                capital = capital * portfolio_value
                portfolio_values.append(capital)
        
        prev_month = month
    
    if monthly_returns_list:
        returns_series = pd.Series(monthly_returns_list)
        
        ann_return = returns_series.mean() * 12
        ann_vol = returns_series.std() * np.sqrt(12)
        sharpe = ann_return / ann_vol if ann_vol > 1e-10 else 0
        
        cumulative = pd.Series(portfolio_values) / initial_capital
        if len(cumulative) > 0:
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            max_dd = drawdown.min()
        else:
            max_dd = 0
        
        win_rate = (returns_series > 0).sum() / len(returns_series)
        total_return = (portfolio_values[-1] / initial_capital - 1) if portfolio_values else 0
        
        return {
            'annual_return': ann_return,
            'sharpe': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'total_return': total_return
        }
    
    return {
        'annual_return': 0,
        'sharpe': 0,
        'max_drawdown': 0,
        'win_rate': 0.5,
        'total_return': 0
    }


def analyze_results(results_df: pd.DataFrame, output_dir: Path):
    """
    分析蒙特卡洛结果
    """
    print("\n" + "="*70)
    print("蒙特卡洛分析结果")
    print("="*70)
    
    # 统计摘要
    print("\n参数敏感性统计:")
    print(f"\n{'指标':<15} {'中位数':>12} {'95% CI 下限':>12} {'95% CI 上限':>12}")
    print("-" * 55)
    
    metrics = ['annual_return', 'sharpe', 'max_drawdown', 'win_rate', 'total_return']
    metric_names = ['年化收益', '夏普比率', '最大回撤', '胜率', '总收益']
    
    for metric, name in zip(metrics, metric_names):
        median = results_df[metric].median()
        ci_low = results_df[metric].quantile(0.025)
        ci_high = results_df[metric].quantile(0.975)
        
        if metric in ['annual_return', 'max_drawdown', 'total_return']:
            print(f"{name:<15} {median*100:>11.2f}% {ci_low*100:>11.2f}% {ci_high*100:>11.2f}%")
        else:
            print(f"{name:<15} {median:>12.4f} {ci_low:>12.4f} {ci_high:>12.4f}")
    
    # 参数影响分析
    print("\n参数影响（相关系数）:")
    print(f"\n{'参数':<15} {'年化收益':>12} {'夏普比率':>12} {'最大回撤':>12}")
    print("-" * 55)
    
    params = ['top_n', 'stop_loss', 'max_position', 'target_vol']
    param_names = ['Top N', '止损', '单只仓位', '目标波动']
    
    for param, name in zip(params, param_names):
        corr_ret = results_df[param].corr(results_df['annual_return'])
        corr_sharpe = results_df[param].corr(results_df['sharpe'])
        corr_dd = results_df[param].corr(results_df['max_drawdown'])
        
        print(f"{name:<15} {corr_ret:>12.4f} {corr_sharpe:>12.4f} {corr_dd:>12.4f}")
    
    # 找到最佳参数范围
    print("\n最佳参数范围（Sharpe 前 10%）:")
    top_10_pct = results_df.nlargest(int(len(results_df) * 0.1), 'sharpe')
    
    print(f"\n{'参数':<15} {'中位数':>12} {'范围':>20}")
    print("-" * 55)
    
    for param, name in zip(params, param_names):
        median = top_10_pct[param].median()
        p5 = top_10_pct[param].quantile(0.05)
        p95 = top_10_pct[param].quantile(0.95)
        
        if param == 'top_n':
            print(f"{name:<15} {median:>12.0f} {p5:.0f} - {p95:.0f}")
        elif param == 'stop_loss' or param == 'max_position' or param == 'target_vol':
            print(f"{name:<15} {median*100:>11.1f}% {p5*100:.1f}% - {p95*100:.1f}%")
    
    # 可视化
    print("\n生成图表...")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. Sharpe 分布
    ax = axes[0, 0]
    ax.hist(results_df['sharpe'], bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(results_df['sharpe'].median(), color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Sharpe Ratio')
    ax.set_ylabel('Frequency')
    ax.set_title('Sharpe Ratio Distribution')
    ax.grid(True, alpha=0.3)
    
    # 2. 年化收益分布
    ax = axes[0, 1]
    ax.hist(results_df['annual_return'] * 100, bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(results_df['annual_return'].median() * 100, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Annual Return (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Annual Return Distribution')
    ax.grid(True, alpha=0.3)
    
    # 3. 最大回撤分布
    ax = axes[0, 2]
    ax.hist(results_df['max_drawdown'] * 100, bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(results_df['max_drawdown'].median() * 100, color='red', linestyle='--', linewidth=2)
    ax.set_xlabel('Max Drawdown (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Max Drawdown Distribution')
    ax.grid(True, alpha=0.3)
    
    # 4. Top N vs Sharpe
    ax = axes[1, 0]
    ax.scatter(results_df['top_n'], results_df['sharpe'], alpha=0.3, s=10)
    ax.set_xlabel('Top N Stocks')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('Top N vs Sharpe Ratio')
    ax.grid(True, alpha=0.3)
    
    # 5. 止损 vs Sharpe
    ax = axes[1, 1]
    ax.scatter(results_df['stop_loss'] * 100, results_df['sharpe'], alpha=0.3, s=10)
    ax.set_xlabel('Stop Loss (%)')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('Stop Loss vs Sharpe Ratio')
    ax.grid(True, alpha=0.3)
    
    # 6. 仓位 vs Sharpe
    ax = axes[1, 2]
    ax.scatter(results_df['max_position'] * 100, results_df['sharpe'], alpha=0.3, s=10)
    ax.set_xlabel('Max Position per Stock (%)')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('Max Position vs Sharpe Ratio')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'monte_carlo_results.png', dpi=150, bbox_inches='tight')
    print(f"  图表已保存：{output_dir / 'monte_carlo_results.png'}")
    
    # 保存结果
    results_df.to_csv(output_dir / 'monte_carlo_results.csv', index=False)
    print(f"  数据已保存：{output_dir / 'monte_carlo_results.csv'}")


def main():
    print("="*70)
    print("蒙特卡洛参数敏感性分析")
    print("="*70)
    
    START_DATE = '20200101'
    N_SIMULATIONS = 500  # 500 次模拟
    SEED = 42
    
    print(f"开始日期：{START_DATE}")
    print(f"模拟次数：{N_SIMULATIONS}")
    print("="*70)
    
    # 1. 加载因子数据
    print("\n[1/4] 加载因子数据...")
    
    factor_names = [
        'momentum_5', 'momentum_20', 'momentum_60',
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
    
    # 2. 加载价格数据
    print("\n[2/4] 加载价格数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        query = f"""
            SELECT ts_code, trade_date, open, close
            FROM daily_prices
            WHERE trade_date >= '{START_DATE}'
            ORDER BY trade_date, ts_code
        """
        price_df = pd.read_sql_query(query, conn)
    
    close_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='close')
    print(f"  价格数据：{close_pivot.shape[0]} 交易日")
    
    # 3. 加载行业数据
    print("\n[3/4] 加载行业数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        df = pd.read_sql_query("""
            SELECT DISTINCT ts_code, industry_name
            FROM industry_classification
        """, conn)
    
    industry_map = dict(zip(df['ts_code'], df['industry_name'])) if not df.empty else {}
    print(f"  行业数据：{len(industry_map)} 只股票")
    
    # 4. 加载指数数据
    print("\n[4/4] 加载指数数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        query = f"""
            SELECT trade_date, close
            FROM index_prices
            WHERE index_code = '000300' AND trade_date >= '{START_DATE}'
            ORDER BY trade_date
        """
        index_df = pd.read_sql_query(query, conn)
    
    if not index_df.empty:
        index_df['return'] = index_df['close'].pct_change()
        index_returns = index_df.set_index('trade_date')['return']
    else:
        index_returns = close_pivot.mean(axis=1).pct_change()
    
    print(f"  指数数据：{len(index_returns)} 交易日")
    
    # 5. 蒙特卡洛模拟
    print("\n" + "="*70)
    print("开始蒙特卡洛模拟...")
    print("="*70)
    
    results_df = monte_carlo_backtest(
        factor_data,
        close_pivot,
        industry_map,
        index_returns,
        n_simulations=N_SIMULATIONS,
        seed=SEED
    )
    
    # 6. 分析结果
    print("\n" + "="*70)
    print("分析结果...")
    print("="*70)
    
    OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "monte_carlo"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    analyze_results(results_df, OUTPUT_DIR)
    
    print("\n" + "="*70)
    print("蒙特卡洛分析完成！")
    print("="*70)
    
    # 结论
    print("\n结论:")
    median_sharpe = results_df['sharpe'].median()
    ci_low = results_df['sharpe'].quantile(0.025)
    ci_high = results_df['sharpe'].quantile(0.975)
    
    if median_sharpe > 0.3:
        print(f"  ✅ 策略稳健！Sharpe 中位数 {median_sharpe:.2f} (95% CI: [{ci_low:.2f}, {ci_high:.2f}])")
    elif median_sharpe > 0:
        print(f"  ⚠️  策略一般！Sharpe 中位数 {median_sharpe:.2f} (95% CI: [{ci_low:.2f}, {ci_high:.2f}])")
    else:
        print(f"  ❌ 策略可能过拟合！Sharpe 中位数 {median_sharpe:.2f}")


if __name__ == "__main__":
    main()
