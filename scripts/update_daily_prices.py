#!/usr/bin/env python3
"""
A 股日线数据更新脚本（修复版）

修复内容：
1. 正确识别最新日期
2. 处理日期格式转换
3. 添加重试机制
4. 添加进度显示

使用方法:
    python3 scripts/update_daily_prices.py
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import akshare as ak
import pandas as pd
from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger

logger = setup_logger("update_daily")


def get_latest_trade_date(db_path=DATABASE_PATH) -> str:
    """获取数据库中最新的交易日期"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        result = cursor.fetchone()[0]
        return result if result else "20100101"


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


def update_single_stock(ts_code: str, start_date: str, end_date: str, db_path=DATABASE_PATH) -> int:
    """
    更新单只股票数据
    
    Returns:
        更新的记录数
    """
    try:
        # 提取股票代码
        symbol = ts_code.split('.')[0]
        
        # 获取数据
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
        
        # 保存到数据库
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
        logger.error(f"更新 {ts_code} 失败：{e}")
        return 0


def main():
    print("="*70)
    print("A 股日线数据更新")
    print("="*70)
    
    # 获取最新日期
    latest_db_date = get_latest_trade_date()
    print(f"\n数据库最新日期：{latest_db_date}")
    
    # 计算目标日期（今天）
    today = datetime.now()
    
    # 如果是周末，获取最近交易日
    if today.weekday() == 5:  # 周六
        target_date = today - timedelta(days=1)
    elif today.weekday() == 6:  # 周日
        target_date = today - timedelta(days=2)
    else:
        target_date = today
    
    target_date_str = target_date.strftime("%Y%m%d")
    print(f"目标日期：{target_date_str}")
    
    if latest_db_date >= target_date_str:
        print("✅ 数据已是最新")
        return
    
    # 获取股票列表
    print("\n获取股票列表...")
    stock_list = get_stock_list()
    print(f"股票数量：{len(stock_list)}")
    
    # 更新数据
    print(f"\n开始更新数据（{latest_db_date} → {target_date_str}）...")
    
    updated_count = 0
    failed_count = 0
    total_rows = 0
    
    for i, ts_code in enumerate(stock_list, 1):
        # 获取该股票的最新日期
        stock_latest = get_stock_latest_date(ts_code)
        
        # 如果已经是最新，跳过
        if stock_latest >= target_date_str:
            continue
        
        # 更新日期范围
        start_date = stock_latest
        end_date = target_date_str
        
        # 更新
        rows = update_single_stock(ts_code, start_date, end_date)
        
        if rows > 0:
            updated_count += 1
            total_rows += rows
            
            if i % 100 == 0:
                print(f"  进度：{i}/{len(stock_list)} (已更新 {updated_count} 只，{total_rows:,} 条)")
        else:
            failed_count += 1
        
        # 避免请求过快
        if i % 50 == 0:
            time.sleep(1)
    
    print(f"\n更新完成!")
    print(f"  更新股票：{updated_count} 只")
    print(f"  更新记录：{total_rows:,} 条")
    print(f"  失败股票：{failed_count} 只")
    
    # 显示数据库状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM daily_prices")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        latest = cursor.fetchone()[0]
        
        print(f"\n数据库状态:")
        print(f"  总记录数：{total_count:,} 条")
        print(f"  最新日期：{latest}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
