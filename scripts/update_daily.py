#!/usr/bin/env python3
"""
每日数据更新脚本

用于每日收盘后更新最新数据（只获取新增数据）

功能：
- 自动识别每个股票的最新日期
- 只下载新增数据
- 批量更新，降低接口压力

使用方法:
    python3 scripts/update_daily.py
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH, DATA_START_DATE
from src.utils import init_database, setup_logger, get_db_connection
from src.data_fetch.stock_list import fetch_stock_list

logger = setup_logger("daily_update")

# 更新配置
BATCH_SIZE = 50     # 每批更新股票数量
BATCH_SLEEP = 2     # 批次间暂停秒数


def get_latest_date_for_stock(ts_code: str) -> str:
    """
    获取某只股票的最新日期
    
    Returns:
        str: 最新日期，无数据则返回 None
    """
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(trade_date) FROM daily_prices WHERE ts_code = ?",
            (ts_code,)
        )
        result = cursor.fetchone()[0]
        return result


def fetch_single_stock_daily_prices(ts_code: str, start_date: str, end_date: str):
    """
    获取单只股票的日线行情数据
    """
    import akshare as ak
    import pandas as pd
    
    try:
        symbol = ts_code.split('.')[0]
        
        df = ak.stock_zh_a_hist(
            symbol=symbol, 
            period="daily", 
            start_date=start_date, 
            end_date=end_date, 
            adjust="qfq"
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # 数据清洗
        column_mapping = {
            "日期": "trade_date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "turnover",
        }
        
        keep_cols = ["日期", "开盘", "最高", "最低", "收盘", "成交量", "成交额"]
        available_cols = [col for col in keep_cols if col in df.columns]
        df = df[available_cols].copy()
        
        for col in available_cols:
            if col in column_mapping:
                df[column_mapping[col]] = df[col]
        
        df["ts_code"] = ts_code
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
        
        final_cols = ["ts_code", "trade_date", "open", "high", "low", "close", "volume", "turnover"]
        final_cols = [col for col in final_cols if col in df.columns]
        df = df[final_cols]
        df["adj_factor"] = 1.0
        
        return df
        
    except Exception as e:
        logger.error(f"获取 {ts_code} 数据失败：{e}")
        return pd.DataFrame()


def save_to_database(df, db_path=DATABASE_PATH):
    """保存数据到数据库"""
    if df.empty:
        return 0
    
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO daily_prices 
                (ts_code, trade_date, open, high, low, close, volume, turnover, adj_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["ts_code"],
                row["trade_date"],
                row.get("open"),
                row.get("high"),
                row.get("low"),
                row.get("close"),
                row.get("volume"),
                row.get("turnover"),
                row.get("adj_factor", 1.0)
            ))
        
        conn.commit()
    
    return len(df)


def update_all_stocks():
    """更新所有股票数据"""
    # 初始化数据库
    init_database(DATABASE_PATH)
    
    # 获取股票列表
    stock_list = fetch_stock_list(DATABASE_PATH)
    
    if stock_list.empty:
        logger.error("无法获取股票列表")
        return
    
    all_stocks = stock_list["ts_code"].tolist()
    total_stocks = len(all_stocks)
    
    today = datetime.now().strftime("%Y%m%d")
    
    logger.info("=" * 70)
    logger.info("开始每日数据更新")
    logger.info("=" * 70)
    logger.info(f"股票总数：{total_stocks}")
    logger.info(f"目标日期：{today}")
    logger.info("=" * 70)
    
    # 统计
    stats = {
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "new_rows": 0
    }
    
    # 分批处理
    batches = [all_stocks[i:i+BATCH_SIZE] for i in range(0, total_stocks, BATCH_SIZE)]
    total_batches = len(batches)
    
    for batch_idx, batch in enumerate(batches, 1):
        logger.info(f"\n批次 {batch_idx}/{total_batches}")
        logger.info("-" * 70)
        
        for stock_idx, ts_code in enumerate(batch):
            global_idx = (batch_idx - 1) * BATCH_SIZE + stock_idx + 1
            progress_pct = (global_idx / total_stocks) * 100
            
            # 获取该股票的最新日期
            latest_date = get_latest_date_for_stock(ts_code)
            
            if not latest_date:
                # 没有数据，需要下载全部
                start_date = DATA_START_DATE
            elif latest_date >= today:
                # 已经是最新数据，跳过
                stats["skipped"] += 1
                print(f"Skipping: {global_idx}/{total_stocks} ({progress_pct:.1f}%) - {ts_code} (最新：{latest_date})")
                continue
            else:
                # 从最新日期的下一天开始
                start_date = latest_date
            
            # 下载数据
            df = fetch_single_stock_daily_prices(ts_code, start_date, today)
            
            if not df.empty:
                rows = save_to_database(df)
                stats["updated"] += 1
                stats["new_rows"] += rows
                print(f"Updating: {global_idx}/{total_stocks} ({progress_pct:.1f}%) - {ts_code} - 新增：{rows}条")
            else:
                stats["failed"] += 1
                print(f"Failed: {global_idx}/{total_stocks} ({progress_pct:.1f}%) - {ts_code}")
        
        # 批次间暂停
        if batch_idx < total_batches:
            logger.info(f"批次完成，暂停 {BATCH_SLEEP} 秒...")
            time.sleep(BATCH_SLEEP)
    
    # 打印统计
    logger.info("\n" + "=" * 70)
    logger.info("更新完成统计")
    logger.info("=" * 70)
    logger.info(f"更新：{stats['updated']} 只股票")
    logger.info(f"跳过：{stats['skipped']} 只股票 (已最新)")
    logger.info(f"失败：{stats['failed']} 只股票")
    logger.info(f"新增记录：{stats['new_rows']:,} 条")
    logger.info("=" * 70)
    
    # 显示数据库状态
    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM daily_prices")
    total_rows = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    latest = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"\n数据库状态:")
    logger.info(f"  总记录数：{total_rows:,} 条")
    logger.info(f"  最新日期：{latest}")
    logger.info("=" * 70)


def main():
    logger.info("=" * 70)
    logger.info("A 股数据每日更新工具")
    logger.info("=" * 70)
    
    update_all_stocks()
    
    logger.info("\n✅ 数据更新完成！")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
