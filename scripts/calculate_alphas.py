#!/usr/bin/env python3
"""
WorldQuant Alpha 因子计算脚本

功能：
- 计算 Top 10 Alpha 因子
- 批量处理，避免内存溢出
- 保存到数据库

使用方法:
    python3 scripts/calculate_alphas.py
    
    # 指定股票数量限制（测试用）
    python3 scripts/calculate_alphas.py --limit 100
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
from src.alphas import (
    alpha_1, alpha_2, alpha_3, alpha_4, alpha_5,
    alpha_6, alpha_7, alpha_8, alpha_9, alpha_10,
    get_alpha_names
)

logger = setup_logger("calculate_alphas")

# Alpha 因子函数映射
ALPHA_FUNCS = {
    'alpha_1': alpha_1,
    'alpha_2': alpha_2,
    'alpha_3': alpha_3,
    'alpha_4': alpha_4,
    'alpha_5': alpha_5,
    'alpha_6': alpha_6,
    'alpha_7': alpha_7,
    'alpha_8': alpha_8,
    'alpha_9': alpha_9,
    'alpha_10': alpha_10,
}

# 批量处理配置
BATCH_SIZE = 100  # 每批处理股票数量


def init_alpha_table(db_path=DATABASE_PATH):
    """
    初始化 alpha_factors 表
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alpha_factors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                alpha_1 REAL,
                alpha_2 REAL,
                alpha_3 REAL,
                alpha_4 REAL,
                alpha_5 REAL,
                alpha_6 REAL,
                alpha_7 REAL,
                alpha_8 REAL,
                alpha_9 REAL,
                alpha_10 REAL,
                UNIQUE(ts_code, trade_date)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alpha_code_date 
            ON alpha_factors(ts_code, trade_date)
        """)
        
        conn.commit()
    
    logger.info("alpha_factors 表初始化完成")


def get_stock_list(db_path=DATABASE_PATH) -> list:
    """获取有数据的股票列表"""
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
    
    返回：open, high, low, close, volume 等字段
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
    
    # 处理停牌数据（用前值填充）
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].ffill()
    
    # 成交量对数化（避免极端值）
    df['volume'] = np.log1p(df['volume'])
    
    return df


def calculate_all_alphas(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有 Alpha 因子
    """
    open_p = df['open']
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']
    
    # 依次计算所有 Alpha
    for alpha_name, alpha_func in ALPHA_FUNCS.items():
        try:
            if alpha_name == 'alpha_1':
                df[alpha_name] = alpha_func(open_p, high, low, close)
            elif alpha_name in ['alpha_2', 'alpha_5', 'alpha_6', 'alpha_7', 'alpha_8', 'alpha_9', 'alpha_10']:
                df[alpha_name] = alpha_func(open_p, high, low, close, volume)
            elif alpha_name in ['alpha_3', 'alpha_4']:
                df[alpha_name] = alpha_func(open_p, high, low, close)
            else:
                df[alpha_name] = alpha_func(open_p, high, low, close, volume)
        except Exception as e:
            logger.error(f"计算 {alpha_name} 失败：{e}")
            df[alpha_name] = np.nan
    
    return df


def save_alphas_to_database(df: pd.DataFrame, db_path=DATABASE_PATH):
    """
    将 Alpha 因子保存到数据库
    """
    alpha_cols = get_alpha_names()
    
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            values = [
                row['ts_code'],
                row['trade_date'],
                row.get('alpha_1'),
                row.get('alpha_2'),
                row.get('alpha_3'),
                row.get('alpha_4'),
                row.get('alpha_5'),
                row.get('alpha_6'),
                row.get('alpha_7'),
                row.get('alpha_8'),
                row.get('alpha_9'),
                row.get('alpha_10'),
            ]
            
            cursor.execute("""
                INSERT OR REPLACE INTO alpha_factors 
                (ts_code, trade_date, alpha_1, alpha_2, alpha_3, alpha_4, 
                 alpha_5, alpha_6, alpha_7, alpha_8, alpha_9, alpha_10)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
        
        conn.commit()
    
    return len(df)


def calculate_alphas_for_all_stocks(limit: int = None, db_path=DATABASE_PATH):
    """
    计算所有股票的 Alpha 因子
    """
    # 初始化数据库表
    init_alpha_table(db_path)
    
    # 获取股票列表
    all_stocks = get_stock_list(db_path)
    
    if limit:
        all_stocks = all_stocks[:limit]
    
    total_stocks = len(all_stocks)
    
    logger.info("=" * 70)
    logger.info("开始计算 Alpha 因子")
    logger.info("=" * 70)
    logger.info(f"股票总数：{total_stocks}")
    logger.info(f"Alpha 数量：{len(ALPHA_FUNCS)}")
    logger.info(f"Alpha 列表：{get_alpha_names()}")
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
                
                # 计算 Alpha
                df = calculate_all_alphas(df)
                
                batch_dfs.append(df)
                stats["processed"] += 1
                
                print(f"Calculating alphas: {global_idx} / {total_stocks} ({progress_pct:.1f}%)")
                print(f"  Stock: {ts_code}")
                
            except Exception as e:
                stats["failed"] += 1
                logger.error(f"处理 {ts_code} 失败：{e}")
        
        # 批量保存
        if batch_dfs:
            batch_df = pd.concat(batch_dfs, ignore_index=True)
            rows = save_alphas_to_database(batch_df, db_path)
            stats["total_rows"] += rows
            
            print(f"  Inserted rows: {rows}")
            logger.info(f"批次完成，写入 {rows} 条 Alpha 记录")
    
    # 打印统计
    logger.info("\n" + "=" * 70)
    logger.info("Alpha 计算完成统计")
    logger.info("=" * 70)
    logger.info(f"处理股票：{stats['processed']} 只")
    logger.info(f"失败股票：{stats['failed']} 只")
    logger.info(f"Alpha 记录：{stats['total_rows']:,} 条")
    logger.info("=" * 70)
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="WorldQuant Alpha 因子计算脚本")
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
    
    calculate_alphas_for_all_stocks(limit=args.limit, db_path=db_path)


if __name__ == "__main__":
    main()
