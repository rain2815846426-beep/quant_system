#!/usr/bin/env python3
"""
因子计算脚本

功能：
- 读取 daily_prices 数据
- 计算各类因子（动量、波动率、成交量、RSI）
- 写入 factor_values 表
- 支持批量处理，避免内存溢出
- 显示计算进度

使用方法:
    python3 scripts/calculate_factors.py
    
    # 指定股票数量限制（测试用）
    python3 scripts/calculate_factors.py --limit 100
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger, init_database
from src.factors import (
    calculate_momentum_factors,
    calculate_volatility_factors,
    calculate_volume_factors,
    calculate_rsi_factors,
)

logger = setup_logger("calculate_factors")

# 因子名称列表
FACTOR_NAMES = [
    'momentum_5', 'momentum_20', 'momentum_60',
    'volatility_20',
    'volume_mean_20', 'volume_ratio',
    'rsi_14'
]

# 批量处理配置
BATCH_SIZE = 100       # 每批处理股票数量
INSERT_BATCH = 50000   # 每批写入数据库的记录数


def init_factor_table(db_path=DATABASE_PATH):
    """
    初始化 factor_values 表并创建索引
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factor_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                factor_name TEXT NOT NULL,
                factor_value REAL,
                UNIQUE(ts_code, trade_date, factor_name)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_factors_code_date 
            ON factor_values(ts_code, trade_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_factors_name 
            ON factor_values(factor_name)
        """)
        
        conn.commit()
    
    logger.info("factor_values 表初始化完成")


def get_stock_list(db_path=DATABASE_PATH) -> list:
    """
    获取有数据的股票列表
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT ts_code FROM daily_prices 
            ORDER BY ts_code
        """)
        stocks = [row[0] for row in cursor.fetchall()]
    return stocks


def load_stock_data(ts_code: str, db_path=DATABASE_PATH) -> pd.DataFrame:
    """
    加载单只股票的历史数据
    """
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query("""
            SELECT ts_code, trade_date, open, high, low, close, volume, turnover
            FROM daily_prices
            WHERE ts_code = ?
            ORDER BY trade_date
        """, conn, params=(ts_code,))
    
    # 转换日期格式
    df['trade_date'] = df['trade_date'].astype(str)
    
    # 确保数值类型
    for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def calculate_all_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有因子
    """
    # 依次计算各类因子
    df = calculate_momentum_factors(df)
    df = calculate_volatility_factors(df)
    df = calculate_volume_factors(df)
    df = calculate_rsi_factors(df, period=14)
    
    return df


def save_factors_to_database(df: pd.DataFrame, db_path=DATABASE_PATH):
    """
    将因子值保存到数据库
    """
    # 转换为长格式
    factor_cols = FACTOR_NAMES
    df_factors = df[['ts_code', 'trade_date'] + factor_cols].copy()
    
    # 熔解为长格式
    df_long = df_factors.melt(
        id_vars=['ts_code', 'trade_date'],
        value_vars=factor_cols,
        var_name='factor_name',
        value_name='factor_value'
    )
    
    # 删除空值
    df_long = df_long.dropna(subset=['factor_value'])
    
    # 批量插入
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        for i in range(0, len(df_long), INSERT_BATCH):
            batch = df_long[i:i+INSERT_BATCH]
            for _, row in batch.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO factor_values 
                    (ts_code, trade_date, factor_name, factor_value)
                    VALUES (?, ?, ?, ?)
                """, (
                    row['ts_code'],
                    row['trade_date'],
                    row['factor_name'],
                    float(row['factor_value'])
                ))
            
            conn.commit()
    
    return len(df_long)


def calculate_factors_for_all_stocks(limit: int = None, db_path=DATABASE_PATH):
    """
    计算所有股票的因子
    
    Args:
        limit: 限制处理的股票数量（None 表示全部）
        db_path: 数据库路径
    """
    # 初始化数据库表
    init_factor_table(db_path)
    
    # 获取股票列表
    all_stocks = get_stock_list(db_path)
    
    if limit:
        all_stocks = all_stocks[:limit]
    
    total_stocks = len(all_stocks)
    
    logger.info("=" * 70)
    logger.info("开始计算因子")
    logger.info("=" * 70)
    logger.info(f"股票总数：{total_stocks}")
    logger.info(f"因子数量：{len(FACTOR_NAMES)}")
    logger.info(f"因子列表：{FACTOR_NAMES}")
    logger.info("=" * 70)
    
    # 统计信息
    stats = {
        "processed": 0,
        "total_rows": 0,
        "failed": 0
    }
    
    # 分批处理
    batches = [all_stocks[i:i+BATCH_SIZE] for i in range(0, total_stocks, BATCH_SIZE)]
    total_batches = len(batches)
    
    for batch_idx, batch in enumerate(batches, 1):
        logger.info(f"\n批次 {batch_idx}/{total_batches}")
        logger.info("-" * 70)
        
        batch_dfs = []
        
        for stock_idx, ts_code in enumerate(batch):
            global_idx = (batch_idx - 1) * BATCH_SIZE + stock_idx + 1
            progress_pct = (global_idx / total_stocks) * 100
            
            try:
                # 加载数据
                df = load_stock_data(ts_code, db_path)
                
                if df.empty or len(df) < 60:
                    # 数据不足，跳过
                    continue
                
                # 计算因子
                df = calculate_all_factors(df)
                
                batch_dfs.append(df)
                stats["processed"] += 1
                
                print(f"Calculating factors: {global_idx} / {total_stocks} ({progress_pct:.1f}%)")
                print(f"  Stock: {ts_code}")
                
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"处理 {ts_code} 失败：{e}")
        
        # 批量保存
        if batch_dfs:
            batch_df = pd.concat(batch_dfs, ignore_index=True)
            rows = save_factors_to_database(batch_df, db_path)
            stats["total_rows"] += rows
            
            print(f"  Inserted rows: {rows}")
            logger.info(f"批次完成，写入 {rows} 条因子记录")
    
    # 打印统计
    logger.info("\n" + "=" * 70)
    logger.info("因子计算完成统计")
    logger.info("=" * 70)
    logger.info(f"处理股票：{stats['processed']} 只")
    logger.info(f"失败股票：{stats['failed']} 只")
    logger.info(f"因子记录：{stats['total_rows']:,} 条")
    logger.info("=" * 70)
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="因子计算脚本")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制处理的股票数量（测试用）"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DATABASE_PATH),
        help="数据库路径"
    )
    
    args = parser.parse_args()
    
    db_path = Path(args.db)
    
    calculate_factors_for_all_stocks(limit=args.limit, db_path=db_path)


if __name__ == "__main__":
    main()
