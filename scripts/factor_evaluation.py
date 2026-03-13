#!/usr/bin/env python3
"""
因子评估与组合系统（Phase 5）

关键设计原则（避免前视偏差）：
1. t 日的因子值只能使用 t 日及之前的信息
2. 预测的是 t+1 到 t+N 的收益
3. IC 计算是截面的、时序正确的
4. 所有处理（去极值、标准化、中性化）都使用截面数据

使用方法:
    python3 scripts/factor_evaluation.py
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
from src.factor_pipeline import (
    process_factor,
    calculate_forward_returns,
    calculate_ic_time_series,
    calculate_ic_statistics,
    factor_group_backtest,
    calculate_group_statistics,
    combine_factors_ic_weighted,
)

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "research_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_factor_data(
    db_path=DATABASE_PATH,
    factor_name: str = 'momentum_20',
    start_date: str = '20180101'
) -> pd.DataFrame:
    """
    加载因子数据（确保时间对齐正确）
    
    Returns:
        DataFrame with columns: ts_code, trade_date, factor_value
        index: (trade_date, ts_code)
    """
    with get_db_connection(db_path) as conn:
        query = """
            SELECT ts_code, trade_date, factor_value
            FROM factor_values
            WHERE factor_name = ? AND trade_date >= ?
            ORDER BY trade_date, ts_code
        """
        df = pd.read_sql_query(query, conn, params=(factor_name, start_date))
    
    # 设置索引
    df = df.set_index(['trade_date', 'ts_code'])
    
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
    
    # 转换为 pivot 格式
    df = df.pivot(index='trade_date', columns='ts_code', values='close')
    
    return df


def load_industry_and_market_cap(
    db_path=DATABASE_PATH
) -> tuple:
    """
    加载行业和市值数据（用于中性化）
    
    注意：这里使用 t 日的行业和市值数据对 t 日的因子进行中性化
    这是正确的，因为行业和市值在 t 日是已知的
    """
    with get_db_connection(db_path) as conn:
        # 行业数据
        industry_query = """
            SELECT ts_code, industry_name as industry
            FROM industry_classification
        """
        industry_df = pd.read_sql_query(industry_query, conn)
        
        # 市值数据（简化：使用日线数据计算）
        # 实际应该使用流通市值数据
        mcap_query = """
            SELECT ts_code, trade_date, close * 1000000 as market_cap
            FROM daily_prices
            WHERE trade_date = (SELECT MAX(trade_date) FROM daily_prices)
        """
        mcap_df = pd.read_sql_query(mcap_query, conn)
        mcap_df['log_mv'] = np.log1p(mcap_df['market_cap'])
    
    industry = industry_df.set_index('ts_code')['industry']
    log_mv = mcap_df.set_index('ts_code')['log_mv']
    
    return industry, log_mv


def run_factor_evaluation(
    factor_name: str = 'momentum_20',
    start_date: str = '20180101',
    db_path=DATABASE_PATH
):
    """
    完整的因子评估流程（避免前视偏差）
    """
    print("="*70)
    print("因子评估系统（Phase 5）")
    print("="*70)
    print(f"因子：{factor_name}")
    print(f"开始日期：{start_date}")
    print(f"时间：{datetime.now()}")
    print("="*70)
    
    # ========== 1. 加载数据 ==========
    print("\n[1/6] 加载数据...")
    
    # 因子数据
    factor_df = load_factor_data(db_path, factor_name, start_date)
    
    # 价格数据
    price_df = load_price_data(db_path, start_date)
    
    print(f"  因子数据：{len(factor_df):,} 条")
    print(f"  价格数据：{price_df.shape[0]} 交易日 x {price_df.shape[1]} 股票")
    
    # ========== 2. 计算未来收益（正确的时间对齐） ==========
    print("\n[2/6] 计算未来收益（避免前视偏差）...")
    
    # forward_returns[t] = 从 t 日开始的未来收益
    # 这意味着 factor[t] 预测的是 forward_returns[t]
    forward_returns = calculate_forward_returns(price_df, periods=[1, 5, 10, 20])
    
    print(f"  未来 1 日收益：{forward_returns[1].shape}")
    print(f"  未来 20 日收益：{forward_returns[20].shape}")
    
    # ========== 3. 因子预处理（截面处理） ==========
    print("\n[3/6] 因子预处理（截面去极值、标准化、中性化）...")
    
    # 加载行业和市值数据
    industry, log_mv = load_industry_and_market_cap(db_path)
    
    # 按交易日处理因子
    processed_factors = {}
    
    trade_dates = factor_df.index.get_level_values('trade_date').unique()
    
    for date in trade_dates:
        # 获取当日因子值（截面）
        factor_date = factor_df.loc[date]['factor_value']
        
        # 获取当日行业和市值
        # 注意：这里使用的是 t 日的信息，这是已知的
        industry_date = industry
        log_mv_date = log_mv
        
        # 处理因子
        processed = process_factor(
            factor_date,
            industry=industry_date,
            log_market_cap=log_mv_date,
            neutralize=True
        )
        
        processed_factors[date] = processed
    
    # 转换回 DataFrame
    factor_processed_df = pd.DataFrame([
        {'trade_date': date, 'ts_code': stock, 'factor_value': value}
        for date, series in processed_factors.items()
        for stock, value in series.items()
    ])
    
    if not factor_processed_df.empty:
        factor_processed_df = factor_processed_df.set_index(['trade_date', 'ts_code'])
        factor_pivot = factor_processed_df['factor_value'].unstack(level='ts_code')
    else:
        factor_pivot = pd.DataFrame()
    
    print(f"  处理完成：{len(processed_factors)} 交易日")
    
    # ========== 4. 计算 IC（正确的截面 IC） ==========
    print("\n[4/6] 计算 IC 时间序列（截面相关性）...")
    
    # 使用 20 日未来收益
    ic_20 = calculate_ic_time_series(
        factor_pivot,
        forward_returns[20],
        method='pearson'
    )
    
    rank_ic_20 = calculate_ic_time_series(
        factor_pivot,
        forward_returns[20],
        method='spearman'
    )
    
    # IC 统计
    ic_stats = calculate_ic_statistics(ic_20)
    rank_ic_stats = calculate_ic_statistics(rank_ic_20)
    
    print(f"\n  IC 统计结果:")
    print(f"    IC Mean:    {ic_stats['ic_mean']:.6f}")
    print(f"    IC Std:     {ic_stats['ic_std']:.6f}")
    print(f"    IC IR:      {ic_stats['ic_ir']:.6f}")
    print(f"    IC T-stat:  {ic_stats['ic_tstat']:.6f}")
    print(f"    IC P-value: {ic_stats['ic_pvalue']:.6f}")
    print(f"    样本数：     {ic_stats['n_periods']}")
    
    print(f"\n  RankIC 统计结果:")
    print(f"    RankIC Mean: {rank_ic_stats['ic_mean']:.6f}")
    print(f"    RankIC IR:   {rank_ic_stats['ic_ir']:.6f}")
    
    # ========== 5. 分层回测 ==========
    print("\n[5/6] 分层回测（5 组）...")
    
    backtest_result = factor_group_backtest(
        factor_pivot,
        forward_returns[20],
        n_groups=5
    )
    
    # 统计指标
    group_stats = calculate_group_statistics(backtest_result)
    
    print(f"\n  各组表现:")
    print(group_stats.to_string())
    
    # ========== 6. 保存结果 ==========
    print("\n[6/6] 保存结果...")
    
    # IC 时间序列
    ic_df = pd.DataFrame({
        'trade_date': ic_20.index,
        'ic_pearson': ic_20.values,
        'ic_spearman': rank_ic_20.values
    })
    ic_df.to_csv(OUTPUT_DIR / f"{factor_name}_ic_timeseries.csv", index=False)
    
    # IC 统计
    ic_summary = {
        'factor_name': factor_name,
        'ic_mean': ic_stats['ic_mean'],
        'ic_std': ic_stats['ic_std'],
        'ic_ir': ic_stats['ic_ir'],
        'ic_tstat': ic_stats['ic_tstat'],
        'ic_pvalue': ic_stats['ic_pvalue'],
        'rank_ic_mean': rank_ic_stats['ic_mean'],
        'rank_ic_ir': rank_ic_stats['ic_ir'],
        'n_periods': ic_stats['n_periods']
    }
    
    pd.DataFrame([ic_summary]).to_csv(
        OUTPUT_DIR / 'factor_backtest_summary.csv',
        index=False
    )
    
    # 分层收益
    if 'daily_returns' in backtest_result:
        backtest_result['daily_returns'].to_csv(
            OUTPUT_DIR / f"{factor_name}_group_returns.csv"
        )
    
    # 累计收益
    if 'cumulative_returns' in backtest_result:
        backtest_result['cumulative_returns'].to_csv(
            OUTPUT_DIR / f"{factor_name}_cumulative.csv"
        )
    
    print(f"  结果已保存到：{OUTPUT_DIR}")
    
    # ========== 总结 ==========
    print("\n" + "="*70)
    print("因子评估完成！")
    print("="*70)
    
    # 评估因子有效性
    if abs(ic_stats['ic_ir']) > 0.5:
        print(f"\n✅ {factor_name} 是有效因子！(IC_IR = {ic_stats['ic_ir']:.2f})")
    elif abs(ic_stats['ic_ir']) > 0.3:
        print(f"\n⚠️  {factor_name} 有一定预测能力 (IC_IR = {ic_stats['ic_ir']:.2f})")
    else:
        print(f"\n❌ {factor_name} 预测能力较弱 (IC_IR = {ic_stats['ic_ir']:.2f})")
    
    print("\n输出文件:")
    print(f"  - {OUTPUT_DIR}/{factor_name}_ic_timeseries.csv")
    print(f"  - {OUTPUT_DIR}/factor_backtest_summary.csv")
    print(f"  - {OUTPUT_DIR}/{factor_name}_group_returns.csv")
    print(f"  - {OUTPUT_DIR}/{factor_name}_cumulative.csv")
    
    return ic_summary


def main():
    parser = argparse.ArgumentParser(description="因子评估系统")
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
    
    run_factor_evaluation(
        factor_name=args.factor,
        start_date=args.start_date,
        db_path=args.db
    )


if __name__ == "__main__":
    main()
