#!/usr/bin/env python3
"""
A 股日线数据分批更新脚本

功能：
1. 将股票分成多个批次
2. 每批更新后暂停，避免网络错误
3. 支持断点续传
4. 显示详细进度

使用方法:
    # 更新第 1 批（前 100 只）
    python3 scripts/update_batch.py --batch 1 --size 100
    
    # 更新所有批次（自动暂停）
    python3 scripts/update_batch.py --all --size 50 --delay 5
"""
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import akshare as ak
import pandas as pd
from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger

logger = setup_logger("update_batch")


def get_stock_list(db_path=DATABASE_PATH) -> list:
    """获取股票列表"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ts_code FROM stock_list ORDER BY ts_code")
        return [row[0] for row in cursor.fetchall()]


def get_stock_latest_date(ts_code: str, db_path=DATABASE_PATH) -> str:
    """获取单只股票的最新日期"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(trade_date) FROM daily_prices WHERE ts_code = ?",
            (ts_code,)
        )
        result = cursor.fetchone()[0]
        return result if result else "20100101"


def get_target_date() -> str:
    """获取目标日期（考虑周末）"""
    today = datetime.now()
    
    if today.weekday() == 5:  # 周六
        target = today - timedelta(days=1)
    elif today.weekday() == 6:  # 周日
        target = today - timedelta(days=2)
    else:
        target = today
    
    return target.strftime("%Y%m%d")


def update_single_stock(ts_code: str, start_date: str, end_date: str, db_path=DATABASE_PATH, max_retries: int = 3) -> int:
    """
    更新单只股票数据（带重试）
    
    Returns:
        更新的记录数
    """
    for attempt in range(max_retries):
        try:
            symbol = ts_code.split('.')[0]
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"
            )
            
            if df.empty:
                return 0
            
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
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df[new_col] = df[old_col]
            
            df["ts_code"] = ts_code
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
            df["adj_factor"] = 1.0
            
            # 保存
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
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.debug(f"{ts_code} 失败，{wait_time}秒后重试 ({attempt+1}/{max_retries}): {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"{ts_code} 更新失败：{e}")
                return 0
    
    return 0


def update_batch(
    batch_num: int,
    batch_size: int,
    db_path=DATABASE_PATH,
    delay_seconds: int = 0
):
    """
    更新指定批次的股票
    
    Args:
        batch_num: 批次号（从 1 开始）
        batch_size: 每批股票数量
        db_path: 数据库路径
        delay_seconds: 每只股票间延迟（秒）
    """
    print("="*70)
    print(f"第 {batch_num} 批数据更新")
    print("="*70)
    
    # 获取股票列表
    print("\n获取股票列表...")
    stock_list = get_stock_list(db_path)
    total_stocks = len(stock_list)
    print(f"股票总数：{total_stocks}")
    
    # 计算批次范围
    start_idx = (batch_num - 1) * batch_size
    end_idx = min(batch_num * batch_size, total_stocks)
    
    if start_idx >= total_stocks:
        print(f"❌ 批次号过大，最大批次号：{(total_stocks + batch_size - 1) // batch_size}")
        return
    
    batch_stocks = stock_list[start_idx:end_idx]
    print(f"本批次股票：{len(batch_stocks)} 只 ({start_idx+1} - {end_idx})")
    
    # 获取目标日期
    target_date = get_target_date()
    print(f"目标日期：{target_date}")
    
    # 更新数据
    print(f"\n开始更新...")
    
    updated_count = 0
    failed_count = 0
    total_rows = 0
    skipped_count = 0
    
    for i, ts_code in enumerate(batch_stocks, 1):
        # 获取该股票的最新日期
        stock_latest = get_stock_latest_date(ts_code, db_path)
        
        # 如果已经是最新，跳过
        if stock_latest >= target_date:
            skipped_count += 1
            if i % 10 == 0:
                print(f"  [{i}/{len(batch_stocks)}] {ts_code} - 已最新，跳过")
            continue
        
        # 更新
        rows = update_single_stock(ts_code, stock_latest, target_date, db_path)
        
        if rows > 0:
            updated_count += 1
            total_rows += rows
            print(f"  [{i}/{len(batch_stocks)}] {ts_code} - 更新 {rows} 条")
        else:
            failed_count += 1
            print(f"  [{i}/{len(batch_stocks)}] {ts_code} - ❌ 失败")
        
        # 延迟
        if delay_seconds > 0 and i < len(batch_stocks):
            time.sleep(delay_seconds)
    
    # 统计
    print(f"\n更新完成!")
    print(f"  更新股票：{updated_count} 只")
    print(f"  跳过股票：{skipped_count} 只")
    print(f"  失败股票：{failed_count} 只")
    print(f"  更新记录：{total_rows:,} 条")
    
    # 显示数据库状态
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        latest = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?", (latest,))
        count = cursor.fetchone()[0]
        
        print(f"\n数据库状态:")
        print(f"  最新日期：{latest}")
        print(f"  {latest} 的股票数量：{count} 只")
    
    print("\n" + "="*70)


def update_all_batches(
    batch_size: int = 50,
    delay_between_stocks: int = 0,
    delay_between_batches: int = 30,
    db_path=DATABASE_PATH
):
    """
    更新所有批次
    
    Args:
        batch_size: 每批股票数量
        delay_between_stocks: 股票间延迟（秒）
        delay_between_batches: 批次间延迟（秒）
        db_path: 数据库路径
    """
    stock_list = get_stock_list(db_path)
    total_batches = (len(stock_list) + batch_size - 1) // batch_size
    
    print("="*70)
    print(f"全量更新（共 {total_batches} 批）")
    print("="*70)
    print(f"每批数量：{batch_size}")
    print(f"股票间延迟：{delay_between_stocks}秒")
    print(f"批次间延迟：{delay_between_batches}秒")
    print("="*70)
    
    for batch_num in range(1, total_batches + 1):
        print(f"\n{'='*70}")
        print(f"第 {batch_num}/{total_batches} 批")
        print(f"{'='*70}")
        
        update_batch(batch_num, batch_size, db_path, delay_between_stocks)
        
        # 批次间延迟（最后一批除外）
        if batch_num < total_batches and delay_between_batches > 0:
            print(f"\n等待 {delay_between_batches} 秒后继续下一批...")
            time.sleep(delay_between_batches)


def main():
    parser = argparse.ArgumentParser(description="A 股日线数据分批更新")
    parser.add_argument('--batch', type=int, default=0, help='批次号（从 1 开始）')
    parser.add_argument('--size', type=int, default=100, help='每批股票数量')
    parser.add_argument('--all', action='store_true', help='更新所有批次')
    parser.add_argument('--delay', type=int, default=0, help='股票间延迟（秒）')
    parser.add_argument('--batch-delay', type=int, default=30, help='批次间延迟（秒）')
    
    args = parser.parse_args()
    
    if args.all:
        # 更新所有批次
        update_all_batches(
            batch_size=args.size,
            delay_between_stocks=args.delay,
            delay_between_batches=args.batch_delay
        )
    elif args.batch > 0:
        # 更新指定批次
        update_batch(args.batch, args.size, delay_seconds=args.delay)
    else:
        print("请指定 --batch 或 --all 参数")
        print("\n示例:")
        print("  # 更新第 1 批（前 100 只）")
        print("  python3 scripts/update_batch.py --batch 1 --size 100")
        print()
        print("  # 更新所有批次（每批 50 只，股票间延迟 1 秒，批次间延迟 30 秒）")
        print("  python3 scripts/update_batch.py --all --size 50 --delay 1 --batch-delay 30")


if __name__ == "__main__":
    main()
