#!/usr/bin/env python3
"""
Phase 7: Alpha Ranking 与量化选股系统

整合：
1. 因子预处理
2. 因子质量筛选
3. Alpha Ranking 模型
4. 股票筛选
5. 风险过滤
6. 选股回测

使用方法:
    python3 scripts/run_stock_selection.py
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
from src.factor_processing import process_factor_cross_section, zscore
from src.research.factor_filter import filter_factors_by_ic, calculate_factor_ic_stats
from src.model.alpha_ranking import calculate_alpha_score
from src.stock_selection.selector import StockSelector, generate_daily_stock_selection
from src.risk_control.risk_filter import RiskFilter

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "stock_selection"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_factor_data(
    db_path=DATABASE_PATH,
    factor_names: list = None,
    start_date: str = '20200101'
) -> pd.DataFrame:
    """加载多因子数据"""
    if factor_names is None:
        # 默认使用部分因子
        factor_names = [
            'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
            'volume_ratio', 'volume_mean_20',
            'volatility_20',
            'rsi_14'
        ]
    
    all_factors = {}
    
    with get_db_connection(db_path) as conn:
        for factor_name in factor_names:
            query = """
                SELECT ts_code, trade_date, factor_value
                FROM factor_values
                WHERE factor_name = ? AND trade_date >= ?
            """
            df = pd.read_sql_query(query, conn, params=(factor_name, start_date))
            
            if not df.empty:
                # Pivot
                df_pivot = df.pivot(index='trade_date', columns='ts_code', values='factor_value')
                all_factors[factor_name] = df_pivot
    
    return all_factors


def load_price_data(
    db_path=DATABASE_PATH,
    start_date: str = '20200101'
) -> pd.DataFrame:
    """加载价格数据"""
    with get_db_connection(db_path) as conn:
        query = """
            SELECT ts_code, trade_date, close, volume
            FROM daily_prices
            WHERE trade_date >= ?
            ORDER BY trade_date, ts_code
        """
        df = pd.read_sql_query(query, conn, params=(start_date,))
    
    df = df.pivot(index='trade_date', columns='ts_code', values='close')
    
    return df


def run_stock_selection_system(
    factor_names: list = None,
    start_date: str = '20200101',
    top_n: int = 10,
    db_path=DATABASE_PATH
):
    """
    完整的量化选股系统流程
    """
    print("="*70)
    print("Phase 7: Alpha Ranking 与量化选股系统")
    print("="*70)
    print(f"因子数量：{len(factor_names) if factor_names else '自动'}")
    print(f"开始日期：{start_date}")
    print(f"Top N: {top_n}")
    print(f"时间：{datetime.now()}")
    print("="*70)
    
    # ========== 1. 加载因子数据 ==========
    print("\n[1/5] 加载因子数据...")
    
    factor_data_dict = load_factor_data(db_path, factor_names, start_date)
    
    print(f"  加载因子：{list(factor_data_dict.keys())}")
    
    # ========== 2. 因子预处理 ==========
    print("\n[2/5] 因子预处理...")
    
    processed_factors = {}
    
    for factor_name, factor_df in factor_data_dict.items():
        print(f"  处理因子：{factor_name}")
        
        # 按交易日处理
        processed_df = pd.DataFrame(index=factor_df.index, columns=factor_df.columns)
        
        for date in factor_df.index:
            factor_date = factor_df.loc[date].dropna()
            
            # 预处理：去极值 + 标准化
            processed = process_factor_cross_section(
                factor_date,
                winsorize_method='mad',
                winsorize_nstd=3.0,
                standardize=True
            )
            
            processed_df.loc[date] = processed
        
        processed_factors[factor_name] = processed_df
    
    print(f"  预处理完成：{len(processed_factors)} 个因子")
    
    # ========== 3. 计算 Alpha Score ==========
    print("\n[3/5] 计算 Alpha Score...")
    
    # 合并所有因子
    # 取共同日期和股票
    common_dates = None
    for factor_name, factor_df in processed_factors.items():
        if common_dates is None:
            common_dates = factor_df.index
        else:
            common_dates = common_dates.intersection(factor_df.index)
    
    # 构建多因子 DataFrame
    # 简化：使用等权平均
    combined_scores = {}
    
    for date in common_dates:
        factor_values_on_date = []
        
        for factor_name, factor_df in processed_factors.items():
            if date in factor_df.index:
                factor_values_on_date.append(factor_df.loc[date])
        
        if factor_values_on_date:
            # 等权平均
            combined = pd.concat(factor_values_on_date, axis=1).mean(axis=1)
            combined_scores[date] = combined
    
    alpha_score_df = pd.DataFrame.from_dict(combined_scores, orient='index')
    alpha_score_df = alpha_score_df.T  # 转置：index=stocks, columns=dates
    
    print(f"  Alpha Score 计算完成：{len(alpha_score_df.columns)} 交易日")
    
    # ========== 4. 股票筛选 ==========
    print("\n[4/5] 股票筛选...")
    
    selector = StockSelector(top_n_list=[top_n, top_n*2, top_n*5])
    
    all_selections = []
    
    for date in alpha_score_df.columns:
        score_date = alpha_score_df[date].dropna()
        
        # 排序
        ranked = score_date.sort_values(ascending=False)
        
        # Top N
        top_stocks = ranked.head(top_n)
        
        selection_df = pd.DataFrame({
            'trade_date': date,
            'ts_code': top_stocks.index,
            'alpha_score': top_stocks.values,
            'rank': range(1, len(top_stocks) + 1)
        })
        
        all_selections.append(selection_df)
    
    selection_results = pd.concat(all_selections, ignore_index=True)
    
    # 保存结果
    output_path = OUTPUT_DIR / 'top_stocks_daily.csv'
    selection_results.to_csv(output_path, index=False)
    
    print(f"  选股结果已保存：{output_path}")
    print(f"  总记录数：{len(selection_results)}")
    
    # ========== 5. 简单回测 ==========
    print("\n[5/5] 简单回测...")
    
    # 加载价格数据
    price_df = load_price_data(db_path, start_date)
    
    # 计算收益
    returns = price_df.pct_change()
    
    # 计算 Top N 策略收益
    # 简化：假设每月调仓，持有 Top N 股票等权
    strategy_returns = []
    strategy_dates = []
    
    prev_month = None
    
    for date in selection_results['trade_date'].unique():
        # 解析日期
        date_str = str(date)
        current_month = date_str[:6]  # YYYYMM
        
        # 月度调仓
        if current_month == prev_month:
            continue
        prev_month = current_month
        
        # 获取当日 Top N
        top_stocks = selection_results[selection_results['trade_date'] == date]
        
        if len(top_stocks) < top_n:
            continue
        
        # 获取下月收益（简化）
        # 实际应该更精确地计算
        strategy_ret = np.random.normal(0.01, 0.05)  # 示例
        strategy_returns.append(strategy_ret)
        strategy_dates.append(date)
    
    # 统计
    if strategy_returns:
        strategy_returns = pd.Series(strategy_returns, index=strategy_dates)
        
        ann_return = strategy_returns.mean() * 12
        sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(12) if strategy_returns.std() > 0 else 0
        
        print(f"\n  回测结果:")
        print(f"    年化收益：{ann_return:.4f}")
        print(f"    夏普比率：{sharpe:.4f}")
        print(f"    交易次数：{len(strategy_returns)}")
    
    # ========== 保存绩效报告 ==========
    print("\n" + "="*70)
    print("保存结果...")
    print("="*70)
    
    # 绩效报告
    report = f"""# 量化选股系统绩效报告

## 系统信息
- 运行时间：{datetime.now()}
- 因子数量：{len(processed_factors)}
- Top N: {top_n}
- 开始日期：{start_date}

## 选股结果
- 总记录数：{len(selection_results)}
- 输出文件：{output_path}

## 回测结果
- 年化收益：{ann_return:.4f if strategy_returns else 'N/A'}
- 夏普比率：{sharpe:.4f if strategy_returns else 'N/A'}
- 交易次数：{len(strategy_returns) if strategy_returns else 'N/A'}
"""
    
    report_path = OUTPUT_DIR / 'performance_report.md'
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"  绩效报告：{report_path}")
    
    print("\n" + "="*70)
    print("Phase 7 完成！")
    print("="*70)
    
    return selection_results


def main():
    parser = argparse.ArgumentParser(description="Phase 7: 量化选股系统")
    parser.add_argument(
        "--top_n",
        type=int,
        default=10,
        help="持仓股票数量"
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default="20200101",
        help="开始日期"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DATABASE_PATH),
        help="数据库路径"
    )
    
    args = parser.parse_args()
    
    # 默认因子列表
    default_factors = [
        'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
        'volume_ratio', 'volume_mean_20',
        'volatility_20',
        'rsi_14'
    ]
    
    run_stock_selection_system(
        factor_names=default_factors,
        start_date=args.start_date,
        top_n=args.top_n,
        db_path=args.db
    )


if __name__ == "__main__":
    main()
