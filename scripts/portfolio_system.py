#!/usr/bin/env python3
"""
Phase 6: 组合构建与风险控制系统

整合：
- 因子稳定性分析
- 换手率分析
- 组合构建
- 风险控制
- 交易成本
- Walk Forward 回测

使用方法:
    python3 scripts/portfolio_system.py
"""
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection
from src.research.factor_stability import factor_stability_analysis, save_stability_report
from src.research.turnover_analysis import calculate_portfolio_turnover, calculate_turnover_statistics
from src.portfolio.portfolio_builder import build_long_short_portfolio, calculate_portfolio_returns
from src.portfolio.transaction_cost import TransactionCostModel, apply_transaction_costs
from src.portfolio.walk_forward import WalkForwardBacktester, calculate_portfolio_statistics

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "research_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_factor_data(
    db_path=DATABASE_PATH,
    factor_name: str = 'momentum_20',
    start_date: str = '20180101'
) -> pd.DataFrame:
    """加载因子数据"""
    with get_db_connection(db_path) as conn:
        query = """
            SELECT ts_code, trade_date, factor_value
            FROM factor_values
            WHERE factor_name = ? AND trade_date >= ?
            ORDER BY trade_date, ts_code
        """
        df = pd.read_sql_query(query, conn, params=(factor_name, start_date))
    
    # Pivot
    df = df.pivot(index='trade_date', columns='ts_code', values='factor_value')
    
    return df


def load_price_data(
    db_path=DATABASE_PATH,
    start_date: str = '20180101'
) -> pd.DataFrame:
    """加载价格数据"""
    with get_db_connection(db_path) as conn:
        query = """
            SELECT ts_code, trade_date, close
            FROM daily_prices
            WHERE trade_date >= ?
            ORDER BY trade_date, ts_code
        """
        df = pd.read_sql_query(query, conn, params=(start_date,))
    
    df = df.pivot(index='trade_date', columns='ts_code', values='close')
    
    return df


def run_portfolio_system(
    factor_name: str = 'momentum_20',
    start_date: str = '20180101',
    db_path=DATABASE_PATH
):
    """
    完整的组合构建与风险分析流程
    """
    print("="*70)
    print("Phase 6: 组合构建与风险控制系统")
    print("="*70)
    print(f"因子：{factor_name}")
    print(f"开始日期：{start_date}")
    print(f"时间：{datetime.now()}")
    print("="*70)
    
    # ========== 1. 加载数据 ==========
    print("\n[1/6] 加载数据...")
    
    factor_df = load_factor_data(db_path, factor_name, start_date)
    price_df = load_price_data(db_path, start_date)
    
    print(f"  因子数据：{factor_df.shape[0]} 交易日 x {factor_df.shape[1]} 股票")
    print(f"  价格数据：{price_df.shape[0]} 交易日 x {price_df.shape[1]} 股票")
    
    # ========== 2. 计算未来收益 ==========
    print("\n[2/6] 计算未来收益...")
    
    forward_returns = price_df.shift(-20) / price_df - 1
    forward_returns = forward_returns.loc[factor_df.index]
    
    print(f"  未来收益：{forward_returns.shape}")
    
    # ========== 3. 因子稳定性分析 ==========
    print("\n[3/6] 因子稳定性分析...")
    
    # 计算 IC 时间序列
    ic_series = []
    ic_dates = []
    
    for date in factor_df.index:
        if date not in forward_returns.index:
            continue
        
        factor_date = factor_df.loc[date].dropna()
        ret_date = forward_returns.loc[date].dropna()
        
        common = factor_date.index.intersection(ret_date.index)
        
        if len(common) < 30:
            continue
        
        ic = factor_date.loc[common].corr(ret_date.loc[common], method='pearson')
        if not np.isnan(ic):
            ic_series.append(ic)
            ic_dates.append(date)
    
    ic_ts = pd.Series(ic_series, index=ic_dates)
    
    # 转换为日期格式
    ic_ts.index = pd.to_datetime(ic_ts.index)
    
    # 稳定性分析
    stability_results = factor_stability_analysis(ic_ts)
    
    print(f"  IC Mean: {stability_results['stability_metrics']['ic_mean']:.6f}")
    print(f"  IC IR:   {stability_results['stability_metrics']['ic_cv']:.4f} (CV)")
    print(f"  胜率：   {stability_results['stability_metrics']['win_rate']:.4f}")
    
    # 保存稳定性报告
    save_stability_report(
        stability_results,
        str(OUTPUT_DIR / f"{factor_name}_stability.csv")
    )
    
    # ========== 4. 构建组合 ==========
    print("\n[4/6] 构建多空组合...")
    
    # 每日构建组合
    weights_history = []
    weights_dates = []
    
    for date in factor_df.index:
        factor_date = factor_df.loc[date].dropna()
        
        if len(factor_date) < 10:
            continue
        
        weights = build_long_short_portfolio(factor_date, top_pct=0.1, bottom_pct=0.1)
        weights_history.append(weights)
        weights_dates.append(date)
    
    weights_df = pd.DataFrame(weights_history, index=weights_dates)
    
    print(f"  权重历史：{weights_df.shape}")
    
    # ========== 5. 计算组合收益 ==========
    print("\n[5/6] 计算组合收益...")
    
    # 个股收益
    stock_returns = price_df.pct_change()
    
    # 组合收益
    portfolio_returns = calculate_portfolio_returns(weights_df, stock_returns)
    
    print(f"  组合收益：{len(portfolio_returns)} 交易日")
    
    # ========== 6. 换手率和交易成本 ==========
    print("\n[6/6] 换手率分析和交易成本...")
    
    # 换手率
    turnover = calculate_portfolio_turnover(weights_df, stock_returns)
    turnover_stats = calculate_turnover_statistics(turnover)
    
    print(f"  日均换手：{turnover_stats['daily_mean']:.4f}")
    print(f"  年化换手：{turnover_stats['annual_turnover']:.2f}")
    
    # 交易成本
    cost_model = TransactionCostModel(commission_rate=0.001, slippage_rate=0.0005)
    net_returns = apply_transaction_costs(portfolio_returns, turnover, cost_model)
    
    # ========== 统计指标 ==========
    print("\n" + "="*70)
    print("组合表现统计")
    print("="*70)
    
    # 毛收益统计
    gross_stats = calculate_portfolio_statistics(portfolio_returns)
    
    # 净收益统计
    net_stats = calculate_portfolio_statistics(net_returns)
    
    print(f"\n毛收益:")
    print(f"  年化收益：{gross_stats.get('annual_return', 0):.4f}")
    print(f"  波动率：  {gross_stats.get('annual_vol', 0):.4f}")
    print(f"  夏普比率：{gross_stats.get('sharpe', 0):.4f}")
    print(f"  最大回撤：{gross_stats.get('max_drawdown', 0):.4f}")
    
    print(f"\n净收益（扣除交易成本后）:")
    print(f"  年化收益：{net_stats.get('annual_return', 0):.4f}")
    print(f"  波动率：  {net_stats.get('annual_vol', 0):.4f}")
    print(f"  夏普比率：{net_stats.get('sharpe', 0):.4f}")
    print(f"  最大回撤：{net_stats.get('max_drawdown', 0):.4f}")
    
    # ========== 保存结果 ==========
    print("\n" + "="*70)
    print("保存结果...")
    print("="*70)
    
    # 组合表现汇总
    portfolio_summary = {
        'factor_name': factor_name,
        'gross_annual_return': gross_stats.get('annual_return', np.nan),
        'gross_sharpe': gross_stats.get('sharpe', np.nan),
        'gross_max_drawdown': gross_stats.get('max_drawdown', np.nan),
        'net_annual_return': net_stats.get('annual_return', np.nan),
        'net_sharpe': net_stats.get('sharpe', np.nan),
        'net_max_drawdown': net_stats.get('max_drawdown', np.nan),
        'annual_turnover': turnover_stats['annual_turnover'],
        'total_cost': (portfolio_returns - net_returns).sum(),
        'n_periods': len(portfolio_returns)
    }
    
    pd.DataFrame([portfolio_summary]).to_csv(
        OUTPUT_DIR / 'portfolio_performance.csv',
        index=False
    )
    
    # 收益时间序列
    returns_df = pd.DataFrame({
        'gross_return': portfolio_returns,
        'net_return': net_returns,
        'turnover': turnover
    })
    returns_df.to_csv(OUTPUT_DIR / f"{factor_name}_portfolio_returns.csv")
    
    # 累计收益
    cumulative_gross = (1 + portfolio_returns).cumprod() - 1
    cumulative_net = (1 + net_returns).cumprod() - 1
    
    cumulative_df = pd.DataFrame({
        'cumulative_gross': cumulative_gross,
        'cumulative_net': cumulative_net
    })
    cumulative_df.to_csv(OUTPUT_DIR / f"{factor_name}_cumulative.csv")
    
    print(f"  结果已保存到：{OUTPUT_DIR}")
    
    # ========== 总结 ==========
    print("\n" + "="*70)
    print("Phase 6 完成！")
    print("="*70)
    
    if net_stats.get('sharpe', 0) > 1:
        print(f"\n✅ {factor_name} 构建的组合表现优秀！(Net Sharpe = {net_stats.get('sharpe', 0):.2f})")
    elif net_stats.get('sharpe', 0) > 0.5:
        print(f"\n⚠️  {factor_name} 构建的组合表现良好 (Net Sharpe = {net_stats.get('sharpe', 0):.2f})")
    else:
        print(f"\n❌ {factor_name} 构建的组合表现一般 (Net Sharpe = {net_stats.get('sharpe', 0):.2f})")
    
    print("\n输出文件:")
    print(f"  - portfolio_performance.csv")
    print(f"  - {factor_name}_portfolio_returns.csv")
    print(f"  - {factor_name}_cumulative.csv")
    print(f"  - {factor_name}_stability.csv")
    
    return portfolio_summary


def main():
    parser = argparse.ArgumentParser(description="Phase 6: 组合构建与风险控制系统")
    parser.add_argument(
        "--factor",
        type=str,
        default="momentum_20",
        help="因子名称"
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default="20180101",
        help="开始日期"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DATABASE_PATH),
        help="数据库路径"
    )
    
    args = parser.parse_args()
    
    run_portfolio_system(
        factor_name=args.factor,
        start_date=args.start_date,
        db_path=args.db
    )


if __name__ == "__main__":
    main()
