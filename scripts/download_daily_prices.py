#!/usr/bin/env python3
"""
A 股日线数据下载脚本（优化版）

功能：
- 断点续传：自动跳过已下载的股票
- 分批下载：每批 100 只股票，降低接口压力
- 自动重试：失败股票自动重试 2 次
- 进度显示：实时显示下载进度

使用方法:
    python3 scripts/download_daily_prices.py
    
    # 指定日期范围
    python3 scripts/download_daily_prices.py --start_date 20200101 --end_date 20231231
"""
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import akshare as ak
import pandas as pd
from config.settings import DATABASE_PATH, DATA_START_DATE
from src.utils import get_db_connection, setup_logger, init_database

logger = setup_logger("download_daily")

# 下载配置
BATCH_SIZE = 100  # 每批下载股票数量
BATCH_SLEEP = 2   # 批次间暂停秒数
MAX_RETRIES = 2   # 最大重试次数


def fetch_single_stock_daily_prices(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取单只股票的日线行情数据
    
    Args:
        ts_code: 股票代码（格式：000001.SZ 或 600000.SH）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        
    Returns:
        pd.DataFrame: 日线行情数据
    """
    try:
        # 提取股票代码
        symbol = ts_code.split('.')[0]
        
        # 使用 akshare 获取日线数据
        df = ak.stock_zh_a_hist(
            symbol=symbol, 
            period="daily", 
            start_date=start_date, 
            end_date=end_date, 
            adjust="qfq"
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # 数据清洗和格式化
        df = _process_daily_prices(df, ts_code)
        return df
        
    except Exception as e:
        logger.error(f"获取 {ts_code} 日线数据失败：{e}")
        return pd.DataFrame()


def _process_daily_prices(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    """
    处理日线行情数据，统一字段格式
    """
    # 重命名字段
    column_mapping = {
        "日期": "trade_date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "turnover",
    }
    
    # 只保留需要的列
    keep_cols = ["日期", "开盘", "最高", "最低", "收盘", "成交量", "成交额"]
    available_cols = [col for col in keep_cols if col in df.columns]
    df = df[available_cols].copy()
    
    # 重命名
    for col in available_cols:
        if col in column_mapping:
            df[column_mapping[col]] = df[col]
    
    # 添加股票代码
    df["ts_code"] = ts_code
    
    # 格式化日期
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
    
    # 选择最终需要的列
    final_cols = ["ts_code", "trade_date", "open", "high", "low", "close", "volume", "turnover"]
    final_cols = [col for col in final_cols if col in df.columns]
    df = df[final_cols]
    
    # 添加复权因子（暂时用 1 填充）
    df["adj_factor"] = 1.0
    
    return df


def check_stock_exists(ts_code: str, db_path: Path) -> bool:
    """
    检查股票数据是否已存在
    
    Returns:
        bool: True 表示已存在，False 表示需要下载
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM daily_prices WHERE ts_code = ?",
            (ts_code,)
        )
        count = cursor.fetchone()[0]
        return count > 0


def save_to_database(df: pd.DataFrame, db_path: Path) -> int:
    """
    将数据保存到数据库
    
    Returns:
        int: 保存的记录数
    """
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


def download_all_daily_prices(start_date: str = DATA_START_DATE, 
                               end_date: str = None,
                               db_path: Path = DATABASE_PATH) -> dict:
    """
    下载所有 A 股的日线行情数据（分批 + 断点续传）
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        db_path: 数据库路径
        
    Returns:
        dict: 下载统计信息
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    # 初始化数据库
    init_database(db_path)
    
    # 获取股票列表
    from src.data_fetch.stock_list import fetch_stock_list
    stock_list = fetch_stock_list(db_path)
    
    if stock_list.empty:
        logger.error("无法获取股票列表")
        return {"success": 0, "skipped": 0, "failed": 0}
    
    all_stocks = stock_list["ts_code"].tolist()
    total_stocks = len(all_stocks)
    
    logger.info("=" * 70)
    logger.info("开始下载 A 股日线行情数据")
    logger.info("=" * 70)
    logger.info(f"股票总数：{total_stocks}")
    logger.info(f"日期范围：{start_date} 至 {end_date}")
    logger.info(f"批次大小：{BATCH_SIZE} 只股票/批")
    logger.info("=" * 70)
    
    # 统计信息
    stats = {
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "total_rows": 0
    }
    
    # 分批处理
    batches = [all_stocks[i:i+BATCH_SIZE] for i in range(0, total_stocks, BATCH_SIZE)]
    total_batches = len(batches)
    
    for batch_idx, batch in enumerate(batches, 1):
        logger.info(f"\n批次 {batch_idx}/{total_batches}")
        logger.info("-" * 70)
        
        for stock_idx, ts_code in enumerate(batch):
            global_stock_idx = (batch_idx - 1) * BATCH_SIZE + stock_idx + 1
            progress_pct = (global_stock_idx / total_stocks) * 100
            
            # 检查是否已存在
            if check_stock_exists(ts_code, db_path):
                stats["skipped"] += 1
                print(f"Skipping: {global_stock_idx} / {total_stocks} ({progress_pct:.1f}%) - {ts_code} (已存在)")
                continue
            
            # 下载数据（带重试）
            df = None
            for retry in range(MAX_RETRIES + 1):
                df = fetch_single_stock_daily_prices(ts_code, start_date, end_date)
                if not df.empty:
                    break
                if retry < MAX_RETRIES:
                    print(f"  Retry {retry + 1}/{MAX_RETRIES} for {ts_code}")
                    time.sleep(1)
            
            # 保存数据
            if not df.empty:
                rows = save_to_database(df, db_path)
                stats["success"] += 1
                stats["total_rows"] += rows
                print(f"Downloading: {global_stock_idx} / {total_stocks} ({progress_pct:.1f}%) - {ts_code} - Rows: {rows}")
            else:
                stats["failed"] += 1
                print(f"Failed: {global_stock_idx} / {total_stocks} ({progress_pct:.1f}%) - {ts_code}")
        
        # 批次间暂停（最后一批除外）
        if batch_idx < total_batches:
            logger.info(f"批次完成，暂停 {BATCH_SLEEP} 秒...")
            time.sleep(BATCH_SLEEP)
    
    # 打印统计
    logger.info("\n" + "=" * 70)
    logger.info("下载完成统计")
    logger.info("=" * 70)
    logger.info(f"成功：{stats['success']} 只股票")
    logger.info(f"跳过：{stats['skipped']} 只股票 (已存在)")
    logger.info(f"失败：{stats['failed']} 只股票")
    logger.info(f"总记录数：{stats['total_rows']:,} 条")
    logger.info(f"完成率：{stats['success']/total_stocks*100:.1f}%")
    logger.info("=" * 70)
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="A 股日线数据下载工具（优化版）")
    parser.add_argument(
        "--start_date",
        type=str,
        default=DATA_START_DATE,
        help=f"开始日期，格式 YYYYMMDD，默认：{DATA_START_DATE}"
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="结束日期，格式 YYYYMMDD，默认：今天"
    )
    
    args = parser.parse_args()
    
    download_all_daily_prices(args.start_date, args.end_date)


if __name__ == "__main__":
    main()
