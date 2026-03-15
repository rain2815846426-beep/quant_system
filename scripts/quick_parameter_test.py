#!/usr/bin/env python3
"""
快速参数敏感性测试

使用完整回测函数，运行 100 次测试
预计时间：10-15 分钟
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection
from scripts.low_drawdown_backtest import (
    low_drawdown_backtest,
    get_industry_data
)

print("="*70)
print("快速参数敏感性测试（100 次）")
print("="*70)

# 加载数据
print("\n[1/3] 加载数据...")

factor_data = {}
with get_db_connection(DATABASE_PATH) as conn:
    for fn in ['momentum_5', 'momentum_20', 'volume_ratio']:
        df = pd.read_sql_query(
            'SELECT ts_code, trade_date, factor_value FROM factor_values WHERE factor_name=? AND trade_date>=?',
            conn,
            params=(fn, '20200101')
        )
        if not df.empty:
            factor_data[fn] = df.pivot(index='trade_date', columns='ts_code', values='factor_value')

with get_db_connection(DATABASE_PATH) as conn:
    price_df = pd.read_sql_query(
        'SELECT ts_code, trade_date, close FROM daily_prices WHERE trade_date>=? ORDER BY trade_date',
        conn,
        params=('20200101',)
    )
close_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='close')

industry_map = get_industry_data()

with get_db_connection(DATABASE_PATH) as conn:
    index_df = pd.read_sql_query(
        'SELECT trade_date, close FROM index_prices WHERE index_code="000300" AND trade_date>=?',
        conn,
        params=('20200101',)
    )
    if not index_df.empty:
        index_df['return'] = index_df['close'].pct_change()
        index_returns = index_df.set_index('trade_date')['return']
    else:
        index_returns = close_pivot.mean(axis=1).pct_change()

print(f"  因子：{list(factor_data.keys())}")
print(f"  价格：{close_pivot.shape}")
print(f"  行业：{len(industry_map)} 只股票")
print(f"  指数：{len(index_returns)} 交易日")

# 参数测试
print("\n[2/3] 运行参数测试...")

N_TESTS = 50  # 50 次测试
results = []

# 参数组合
test_configs = [
    {'top_n': 10, 'stop_loss': 0.10, 'max_position': 0.05},
    {'top_n': 10, 'stop_loss': 0.15, 'max_position': 0.08},
    {'top_n': 10, 'stop_loss': 0.20, 'max_position': 0.10},
    {'top_n': 20, 'stop_loss': 0.10, 'max_position': 0.05},
    {'top_n': 20, 'stop_loss': 0.15, 'max_position': 0.08},
    {'top_n': 20, 'stop_loss': 0.20, 'max_position': 0.10},
    {'top_n': 30, 'stop_loss': 0.10, 'max_position': 0.05},
    {'top_n': 30, 'stop_loss': 0.15, 'max_position': 0.08},
    {'top_n': 30, 'stop_loss': 0.20, 'max_position': 0.10},
]

print(f"\n  测试配置：{len(test_configs)} 组")
print(f"  每组重复：{N_TESTS // len(test_configs)} 次")

for i, config in enumerate(test_configs):
    print(f"\n  配置 {i+1}/{len(test_configs)}: Top{config['top_n']}, 止损{config['stop_loss']*100:.0f}%, 仓位{config['max_position']*100:.0f}%")
    
    for j in range(N_TESTS // len(test_configs)):
        result = low_drawdown_backtest(
            factor_data,
            close_pivot,
            industry_map,
            index_returns,
            top_n=config['top_n'],
            start_date='20200101',
            stop_loss_pct=config['stop_loss'],
            max_position_per_stock=config['max_position'],
            target_volatility=0.20
        )
        
        results.append({
            'test_id': i * (N_TESTS // len(test_configs)) + j + 1,
            'top_n': config['top_n'],
            'stop_loss': config['stop_loss'],
            'max_position': config['max_position'],
            'annual_return': result['annual_return'],
            'sharpe': result['sharpe'],
            'max_drawdown': result['max_drawdown'],
            'win_rate': result['win_rate'],
            'total_return': result['total_return']
        })
        
        if (i * (N_TESTS // len(test_configs)) + j + 1) % 10 == 0:
            print(f"    进度：{i * (N_TESTS // len(test_configs)) + j + 1}/{N_TESTS}")

# 分析结果
print("\n[3/3] 分析结果...")

results_df = pd.DataFrame(results)

print("\n" + "="*70)
print("参数敏感性分析结果")
print("="*70)

print(f"\n测试次数：{len(results_df)}")
print(f"\n整体统计:")
print(f"  Sharpe 中位数：{results_df['sharpe'].median():.4f}")
print(f"  Sharpe 范围：[{results_df['sharpe'].quantile(0.025):.4f}, {results_df['sharpe'].quantile(0.975):.4f}]")
print(f"  年化收益中位数：{results_df['annual_return'].median()*100:.2f}%")
print(f"  最大回撤中位数：{results_df['max_drawdown'].median()*100:.2f}%")

print(f"\n按配置分组:")
grouped = results_df.groupby(['top_n', 'stop_loss', 'max_position']).agg({
    'sharpe': ['mean', 'std'],
    'annual_return': 'mean',
    'max_drawdown': 'mean'
}).round(4)

print(grouped)

# 保存结果
OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "parameter_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

results_df.to_csv(OUTPUT_DIR / 'parameter_sensitivity.csv', index=False)
print(f"\n结果已保存：{OUTPUT_DIR / 'parameter_sensitivity.csv'}")

# 最佳配置
best_idx = results_df['sharpe'].idxmax()
best_config = results_df.loc[best_idx]
print(f"\n最佳配置:")
print(f"  Top N: {int(best_config['top_n'])}")
print(f"  止损：{best_config['stop_loss']*100:.1f}%")
print(f"  仓位：{best_config['max_position']*100:.1f}%")
print(f"  Sharpe: {best_config['sharpe']:.4f}")
print(f"  年化：{best_config['annual_return']*100:.2f}%")
print(f"  回撤：{best_config['max_drawdown']*100:.2f}%")

print("\n" + "="*70)
print("参数敏感性测试完成！")
print("="*70)
