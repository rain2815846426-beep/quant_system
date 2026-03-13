#!/usr/bin/env python3
"""
核心指数成分股数据下载脚本

下载范围：
- 沪深 300 + 中证 500 + 中证 1000 成分股
- 时间：2018-01-01 至今

功能：
- 断点续传：自动跳过已下载的股票
- 分批下载：每批 100 只股票
- 自动重试：失败股票自动重试 2 次
- 进度显示：实时显示下载进度

使用方法:
    python3 scripts/download_index_stocks.py
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
from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger, init_database

logger = setup_logger("download_index")

# 下载配置
BATCH_SIZE = 100    # 每批下载股票数量
BATCH_SLEEP = 2     # 批次间暂停秒数
MAX_RETRIES = 2     # 最大重试次数

# 数据范围配置
START_DATE = "20180101"  # 从 2018 年开始


def get_index_components() -> list:
    """
    获取沪深 300 + 中证 500 + 中证 1000 的成分股列表
    
    Returns:
        list: 成分股代码列表（去重）
    """
    index_codes = {
        "HS300": "000300",      # 沪深 300
        "CSI500": "000905",     # 中证 500
        "CSI1000": "000852",    # 中证 1000
    }
    
    all_components = set()
    
    logger.info("获取指数成分股列表...")
    
    for index_name, index_code in index_codes.items():
        try:
            df = ak.index_stock_cons(symbol=index_code)
            
            if not df.empty:
                # 提取股票代码
                if "品种代码" in df.columns:
                    codes = df["品种代码"].astype(str).tolist()
                elif "code" in df.columns:
                    codes = df["code"].astype(str).tolist()
                else:
                    logger.warning(f"{index_name} 无法识别股票代码列")
                    continue
                
                # 转换为 ts_code 格式
                for code in codes:
                    if code.startswith("6"):
                        ts_code = f"{code}.SH"
                    else:
                        ts_code = f"{code}.SZ"
                    all_components.add(ts_code)
                
                logger.info(f"{index_name}: {len(codes)} 只成分股")
            
        except Exception as e:
            logger.error(f"获取 {index_name} 成分股失败：{e}")
    
    logger.info(f"成分股总数（去重后）: {len(all_components)}")
    return sorted(list(all_components))


def fetch_single_stock_daily_prices(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取单只股票的日线行情数据
    """
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
        logger.error(f"获取 {ts_code} 日线数据失败：{e}")
        return pd.DataFrame()


def check_stock_exists(ts_code: str, db_path: Path) -> bool:
    """检查股票数据是否已存在"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM daily_prices WHERE ts_code = ?",
            (ts_code,)
        )
        count = cursor.fetchone()[0]
        return count > 0


def save_to_database(df: pd.DataFrame, db_path: Path) -> int:
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


def download_index_stocks(start_date: str = START_DATE, 
                          end_date: str = None,
                          db_path: Path = DATABASE_PATH) -> dict:
    """
    下载核心指数成分股的日线行情数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    # 初始化数据库
    init_database(db_path)
    
    # 获取成分股列表
    target_stocks = get_index_components()
    
    if not target_stocks:
        logger.error("无法获取成分股列表")
        return {"success": 0, "skipped": 0, "failed": 0}
    
    total_stocks = len(target_stocks)
    
    logger.info("=" * 70)
    logger.info("开始下载核心指数成分股数据")
    logger.info("=" * 70)
    logger.info(f"成分股总数：{total_stocks}")
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
    batches = [target_stocks[i:i+BATCH_SIZE] for i in range(0, total_stocks, BATCH_SIZE)]
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
        
        # 批次间暂停
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
    parser = argparse.ArgumentParser(description="核心指数成分股数据下载工具")
    parser.add_argument(
        "--start_date",
        type=str,
        default=START_DATE,
        help=f"开始日期，格式 YYYYMMDD，默认：{START_DATE}"
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="结束日期，格式 YYYYMMDD，默认：今天"
    )
    
    args = parser.parse_args()
    
    download_index_stocks(args.start_date, args.end_date)


if __name__ == "__main__":
    main()
