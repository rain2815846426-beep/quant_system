"""
因子分层回测模块

将股票按因子值排序分组，计算各组收益，评估因子区分度。

功能：
- 因子分组（5 组/10 组）
- 各组平均收益计算
- 多空组合收益（Top - Bottom）
- 累计收益曲线
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sqlite3
from pathlib import Path

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def factor_group_backtest(
    db_path: Path = DATABASE_PATH,
    factor_name: str = 'momentum_20',
    n_groups: int = 5,
    forward_period: int = 20,
    start_date: str = '20180101',
    end_date: str = None
) -> Dict:
    """
    因子分层回测
    
    Args:
        db_path: 数据库路径
        factor_name: 因子名称
        n_groups: 分组数量（5 或 10）
        forward_period: 预测周期
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        Dict: 回测结果
    """
    conn = sqlite3.connect(db_path)
    
    # 获取日期范围
    if end_date is None:
        end_date = pd.Timestamp.now().strftime('%Y%m%d')
    
    print(f"因子分层回测：{factor_name}")
    print(f"分组数量：{n_groups}")
    print(f"预测周期：{forward_period}日")
    print(f"日期范围：{start_date} - {end_date}")
    
    # 1. 获取因子值和价格数据
    query = """
        WITH factor_data AS (
            SELECT ts_code, trade_date, factor_value
            FROM factor_values
            WHERE factor_name = ?
            AND trade_date >= ?
            AND trade_date <= ?
        ),
        price_data AS (
            SELECT ts_code, trade_date, close
            FROM daily_prices
            WHERE trade_date >= ?
            AND trade_date <= ?
        )
        SELECT f.ts_code, f.trade_date, f.factor_value, p.close
        FROM factor_data f
        JOIN price_data p ON f.ts_code = p.ts_code AND f.trade_date = p.trade_date
        ORDER BY f.trade_date, f.ts_code
    """
    
    df = pd.read_sql_query(query, conn, params=(factor_name, start_date, end_date, 
                                                 start_date, end_date))
    conn.close()
    
    if df.empty:
        print("无数据")
        return None
    
    print(f"加载数据：{len(df):,} 条记录")
    
    # 2. 计算未来收益
    df = df.pivot(index=['ts_code', 'trade_date'], columns='close').reset_index()
    df = df.sort_values(['ts_code', 'trade_date'])
    
    # 计算未来 N 日收益
    df['future_return'] = df.groupby('ts_code')['close'].transform(
        lambda x: x.shift(-forward_period) / x - 1
    ) * 100
    
    # 移除最后一期（无法计算未来收益）
    df = df.dropna(subset=['future_return'])
    
    print(f"计算收益后：{len(df):,} 条记录")
    
    # 3. 按交易日分组，计算分组收益
    group_returns = []
    
    for trade_date in df['trade_date'].unique():
        date_df = df[df['trade_date'] == trade_date].copy()
        
        if len(date_df) < n_groups:
            continue
        
        # 按因子值排序并分组
        date_df['factor_rank'] = pd.qcut(
            date_df['factor_value'].rank(method='first'),
            q=n_groups,
            labels=False,
            duplicates='drop'
        )
        
        # 计算各组平均收益
        group_mean = date_df.groupby('factor_rank')['future_return'].mean()
        
        for group, ret in group_mean.items():
            group_returns.append({
                'trade_date': trade_date,
                'group': group,
                'return': ret,
                'n_stocks': len(date_df[date_df['factor_rank'] == group])
            })
    
    group_returns_df = pd.DataFrame(group_returns)
    
    if group_returns_df.empty:
        print("分组结果为空")
        return None
    
    # 4. 计算统计指标
    # 各组平均收益
    group_avg_returns = group_returns_df.groupby('group')['return'].agg(['mean', 'std'])
    group_avg_returns.columns = ['mean_return', 'std_return']
    
    # 多空组合收益（Top - Bottom）
    long_short_returns = []
    for trade_date in group_returns_df['trade_date'].unique():
        date_df = group_returns_df[group_returns_df['trade_date'] == trade_date]
        if len(date_df) == n_groups:
            top_return = date_df[date_df['group'] == n_groups - 1]['return'].values[0]
            bottom_return = date_df[date_df['group'] == 0]['return'].values[0]
            long_short_returns.append({
                'trade_date': trade_date,
                'long_short_return': top_return - bottom_return
            })
    
    long_short_df = pd.DataFrame(long_short_returns)
    
    # 5. 计算累计收益
    cumulative_returns = []
    for group in range(n_groups):
        group_df = group_returns_df[group_returns_df['group'] == group].copy()
        group_df = group_df.sort_values('trade_date')
        group_df['cumulative'] = (1 + group_df['return'] / 100).cumprod() - 1
        cumulative_returns.append({
            'group': group,
            'cumulative_return': group_df['cumulative'].iloc[-1] if len(group_df) > 0 else np.nan
        })
    
    cumulative_df = pd.DataFrame(cumulative_returns)
    
    # 6. 结果汇总
    results = {
        'factor_name': factor_name,
        'n_groups': n_groups,
        'forward_period': forward_period,
        'group_returns': group_avg_returns,
        'long_short_returns': long_short_df,
        'cumulative_returns': cumulative_df,
        'daily_group_returns': group_returns_df
    }
    
    # 打印结果
    print("\n" + "=" * 60)
    print(f"因子：{factor_name}")
    print("=" * 60)
    print("\n各组平均收益:")
    print(group_avg_returns.round(4))
    
    if not long_short_df.empty:
        ls_mean = long_short_df['long_short_return'].mean()
        ls_std = long_short_df['long_short_return'].std()
        ls_ir = ls_mean / ls_std if ls_std > 0 else np.nan
        print(f"\n多空组合收益:")
        print(f"  均值：{ls_mean:.4f}%")
        print(f"  标准差：{ls_std:.4f}%")
        print(f"  IR: {ls_ir:.4f}")
    
    print("\n累计收益:")
    print(cumulative_df.round(4))
    
    return results


def plot_group_returns(results: Dict, save_path: str = None):
    """
    绘制分组收益图
    
    Args:
        results: 回测结果
        save_path: 保存路径
    """
    import matplotlib.pyplot as plt
    
    if results is None:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. 各组平均收益柱状图
    ax1 = axes[0, 0]
    group_returns = results['group_returns']
    ax1.bar(range(len(group_returns)), group_returns['mean_return'])
    ax1.set_xlabel('Group (Quintile)')
    ax1.set_ylabel('Average Return (%)')
    ax1.set_title('Average Return by Group')
    ax1.set_xticks(range(len(group_returns)))
    ax1.set_xticklabels([f'Q{i+1}' for i in range(len(group_returns))])
    
    # 2. 多空组合收益
    ax2 = axes[0, 1]
    long_short = results['long_short_returns']
    if not long_short.empty:
        ax2.plot(long_short['trade_date'], long_short['long_short_return'], alpha=0.7)
        ax2.axhline(y=long_short['long_short_return'].mean(), color='r', linestyle='--')
        ax2.set_xlabel('Trade Date')
        ax2.set_ylabel('Long-Short Return (%)')
        ax2.set_title('Long-Short Return Over Time')
    
    # 3. 累计收益曲线
    ax3 = axes[1, 0]
    cumulative = results['cumulative_returns']
    ax3.bar(range(len(cumulative)), cumulative['cumulative_return'])
    ax3.set_xlabel('Group')
    ax3.set_ylabel('Cumulative Return')
    ax3.set_title('Cumulative Return by Group')
    
    # 4. 收益分布箱线图
    ax4 = axes[1, 1]
    daily_returns = results['daily_group_returns']
    if not daily_returns.empty:
        data = [daily_returns[daily_returns['group'] == g]['return'].values 
                for g in sorted(daily_returns['group'].unique())]
        ax4.boxplot(data, labels=[f'Q{i+1}' for i in range(len(data))])
        ax4.set_ylabel('Return (%)')
        ax4.set_title('Return Distribution by Group')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存：{save_path}")
    
    plt.show()
