#!/usr/bin/env python3
"""
因子有效性分析脚本

功能：
- 遍历所有因子
- 计算 IC、RankIC
- 因子分层回测
- 保存结果到 CSV

使用方法:
    python3 scripts/analyze_factors.py
    
    # 指定因子
    python3 scripts/analyze_factors.py --factor momentum_20
    
    # 指定预测周期
    python3 scripts/analyze_factors.py --forward_period 10
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

import sqlite3
from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger
from src.research import calculate_ic, calculate_rank_ic, factor_group_backtest

logger = setup_logger("analyze_factors")

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "research_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def get_factor_list(db_path=DATABASE_PATH) -> list:
    """获取因子列表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT factor_name FROM factor_values ORDER BY factor_name")
    factors = [row[0] for row in cursor.fetchall()]
    conn.close()
    return factors


def get_trade_dates(start_date: str = '20180101', db_path=DATABASE_PATH) -> list:
    """获取交易日列表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT trade_date FROM factor_values
        WHERE trade_date >= ?
        ORDER BY trade_date
    """, (start_date,))
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates


def calculate_factor_returns(
    factor_name: str,
    forward_period: int = 20,
    start_date: str = '20180101',
    db_path=DATABASE_PATH
) -> pd.DataFrame:
    """
    计算因子和未来收益（批量加载，避免内存溢出）
    """
    conn = sqlite3.connect(db_path)
    
    # 直接加载因子值和价格数据
    query = """
        SELECT f.ts_code, f.trade_date, f.factor_value, p.close
        FROM factor_values f
        JOIN daily_prices p ON f.ts_code = p.ts_code AND f.trade_date = p.trade_date
        WHERE f.factor_name = ? AND f.trade_date >= ?
        ORDER BY f.trade_date, f.ts_code
    """
    
    df = pd.read_sql_query(query, conn, params=(factor_name, start_date))
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    print(f"  加载数据：{len(df):,} 条")
    
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 计算未来 N 日收益
    df[f'return_{forward_period}'] = df.groupby('ts_code')['close'].transform(
        lambda x: x.shift(-forward_period) / x - 1
    ) * 100
    
    df = df.dropna(subset=[f'return_{forward_period}'])
    
    return df


def quick_ic_analysis(
    factor_name: str,
    forward_period: int = 20,
    start_date: str = '20180101',
    db_path=DATABASE_PATH
) -> dict:
    """
    快速 IC 分析（简化版本）
    """
    print(f"\n分析因子：{factor_name}")
    
    # 加载数据
    df = calculate_factor_returns(factor_name, forward_period, start_date, db_path)
    
    if df.empty:
        print(f"  无数据")
        return None
    
    # 计算 IC（按交易日）
    ic_by_date = df.groupby('trade_date').apply(
        lambda x: x['factor_value'].corr(x[f'return_{forward_period}'], method='pearson')
        if len(x.dropna()) > 30 else np.nan
    )
    
    # 计算 RankIC
    rank_ic_by_date = df.groupby('trade_date').apply(
        lambda x: x['factor_value'].corr(x[f'return_{forward_period}'], method='spearman')
        if len(x.dropna()) > 30 else np.nan
    )
    
    # 统计指标
    ic_clean = ic_by_date.dropna()
    rank_ic_clean = rank_ic_by_date.dropna()
    
    results = {
        'factor_name': factor_name,
        'forward_period': forward_period,
        'ic_mean': ic_clean.mean() if len(ic_clean) > 0 else np.nan,
        'ic_std': ic_clean.std() if len(ic_clean) > 0 else np.nan,
        'ic_ir': ic_clean.mean() / ic_clean.std() if len(ic_clean) > 0 and ic_clean.std() > 0 else np.nan,
        'rank_ic_mean': rank_ic_clean.mean() if len(rank_ic_clean) > 0 else np.nan,
        'rank_ic_std': rank_ic_clean.std() if len(rank_ic_clean) > 0 else np.nan,
        'rank_ic_ir': rank_ic_clean.mean() / rank_ic_clean.std() if len(rank_ic_clean) > 0 and rank_ic_clean.std() > 0 else np.nan,
        'n_periods': len(ic_clean)
    }
    
    print(f"  IC Mean: {results['ic_mean']:.4f}")
    print(f"  IC IR:   {results['ic_ir']:.4f}")
    print(f"  RankIC Mean: {results['rank_ic_mean']:.4f}")
    print(f"  RankIC IR:   {results['rank_ic_ir']:.4f}")
    
    return results


def analyze_all_factors(
    forward_period: int = 20,
    start_date: str = '20180101',
    db_path=DATABASE_PATH
) -> pd.DataFrame:
    """
    分析所有因子
    """
    # 获取因子列表
    factors = get_factor_list(db_path)
    print(f"因子总数：{len(factors)}")
    print(f"预测周期：{forward_period}日")
    print(f"开始日期：{start_date}")
    print("=" * 70)
    
    all_results = []
    
    for factor in factors:
        result = quick_ic_analysis(factor, forward_period, start_date, db_path)
        if result:
            all_results.append(result)
    
    # 转换为 DataFrame
    results_df = pd.DataFrame(all_results)
    
    # 排序
    if 'rank_ic_ir' in results_df.columns:
        results_df = results_df.sort_values('rank_ic_ir', ascending=False)
    
    return results_df


def run_group_backtest_for_all_factors(
    factors: list = None,
    forward_period: int = 20,
    start_date: str = '20180101',
    db_path=DATABASE_PATH
) -> pd.DataFrame:
    """
    对所有因子进行分层回测
    """
    if factors is None:
        factors = get_factor_list(db_path)
    
    print(f"\n因子分层回测")
    print(f"因子数量：{len(factors)}")
    print("=" * 70)
    
    all_group_returns = []
    
    for factor in factors:
        print(f"\n因子：{factor}")
        
        results = factor_group_backtest(
            db_path=db_path,
            factor_name=factor,
            n_groups=5,
            forward_period=forward_period,
            start_date=start_date
        )
        
        if results and results['group_returns'] is not None:
            group_ret = results['group_returns'].reset_index()
            group_ret['factor_name'] = factor
            
            # 多空收益
            if not results['long_short_returns'].empty:
                ls_mean = results['long_short_returns']['long_short_return'].mean()
            else:
                ls_mean = np.nan
            
            group_ret['long_short_mean'] = ls_mean
            all_group_returns.append(group_ret)
    
    if all_group_returns:
        return pd.concat(all_group_returns, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="因子有效性分析")
    parser.add_argument(
        "--factor",
        type=str,
        default=None,
        help="指定因子名称（默认分析所有因子）"
    )
    parser.add_argument(
        "--forward_period",
        type=int,
        default=20,
        help="预测周期（默认 20 日）"
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default='20180101',
        help="开始日期（默认 20180101）"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DATABASE_PATH),
        help="数据库路径"
    )
    
    args = parser.parse_args()
    
    db_path = Path(args.db)
    
    print("=" * 70)
    print("因子有效性分析")
    print("=" * 70)
    
    # 1. IC 分析
    if args.factor:
        # 单个因子
        result = quick_ic_analysis(
            args.factor,
            args.forward_period,
            args.start_date,
            db_path
        )
        results_df = pd.DataFrame([result]) if result else pd.DataFrame()
    else:
        # 所有因子
        results_df = analyze_all_factors(
            args.forward_period,
            args.start_date,
            db_path
        )
    
    # 保存 IC 结果
    if not results_df.empty:
        ic_file = OUTPUT_DIR / "factor_ic_summary.csv"
        results_df.to_csv(ic_file, index=False)
        print(f"\nIC 结果已保存：{ic_file}")
    
    # 2. 分层回测
    if not args.factor:
        print("\n" + "=" * 70)
        print("开始分层回测...")
        group_returns_df = run_group_backtest_for_all_factors(
            forward_period=args.forward_period,
            start_date=args.start_date,
            db_path=db_path
        )
        
        if not group_returns_df.empty:
            group_file = OUTPUT_DIR / "factor_group_returns.csv"
            group_returns_df.to_csv(group_file, index=False)
            print(f"\n分层回测结果已保存：{group_file}")
    
    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
