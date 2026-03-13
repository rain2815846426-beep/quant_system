#!/usr/bin/env python3
"""
数据查询工具

提供常用的数据库查询示例

使用方法:
    python scripts/query_data.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
from config.settings import DATABASE_PATH


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def query_daily_prices_top10():
    """查询日线数据前 10 行"""
    print_header("日线数据表 (daily_prices) - 前 10 行")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ts_code, trade_date, open, high, low, close, volume, turnover
        FROM daily_prices
        ORDER BY ts_code, trade_date
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    print(f"\n{'ts_code':<12} {'trade_date':<10} {'open':>8} {'high':>8} {'low':>8} {'close':>8} {'volume':>12} {'turnover':>15}")
    print("-" * 90)
    
    for row in rows:
        ts_code, trade_date, open_p, high, low, close, volume, turnover = row
        print(f"{ts_code:<12} {trade_date:<10} {open_p:>8.2f} {high:>8.2f} {low:>8.2f} {close:>8.2f} {int(volume) if volume else 0:>12,} {int(turnover) if turnover else 0:>15,.0f}")
    
    conn.close()


def query_database_status():
    """查询数据库状态"""
    print_header("数据库状态")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 表记录数
    tables = [
        "stock_list",
        "daily_prices",
        "financial_data",
        "index_prices",
        "index_components",
    ]
    
    print("\n表记录统计:")
    print("-" * 40)
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table:<25} {count:>10,} 条")
        except Exception as e:
            print(f"  {table:<25} 查询失败：{e}")
    
    # 最新日期
    print("\n最新数据日期:")
    print("-" * 40)
    
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    latest = cursor.fetchone()[0]
    print(f"  日线数据：{latest if latest else '无数据'}")
    
    cursor.execute("SELECT MAX(trade_date) FROM index_prices")
    latest = cursor.fetchone()[0]
    print(f"  指数数据：{latest if latest else '无数据'}")
    
    # 股票数量
    cursor.execute("SELECT COUNT(*) FROM stock_list")
    stock_count = cursor.fetchone()[0]
    print(f"\n  股票总数：{stock_count:,} 只")
    
    conn.close()


def query_sample_stock():
    """查询示例股票数据"""
    print_header("示例股票：贵州茅台 (600519.SH) - 最近 10 个交易日")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ts_code, trade_date, open, high, low, close, volume, turnover
        FROM daily_prices
        WHERE ts_code = '600519.SH'
        ORDER BY trade_date DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("\n暂无数据，请先运行数据下载")
    else:
        print(f"\n{'ts_code':<12} {'trade_date':<10} {'open':>8} {'high':>8} {'low':>8} {'close':>8} {'volume':>12} {'turnover':>15}")
        print("-" * 90)
        
        for row in rows:
            ts_code, trade_date, open_p, high, low, close, volume, turnover = row
            print(f"{ts_code:<12} {trade_date:<10} {open_p:>8.2f} {high:>8.2f} {low:>8.2f} {close:>8.2f} {int(volume) if volume else 0:>12,} {int(turnover) if turnover else 0:>15,.0f}")
    
    conn.close()


def main():
    print("\n" + "=" * 60)
    print("  量化系统数据查询工具")
    print("=" * 60)
    
    # 数据库状态
    query_database_status()
    
    # 日线数据前 10 行
    query_daily_prices_top10()
    
    # 示例股票
    query_sample_stock()
    
    print("\n" + "=" * 60)
    print("  查询完成")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
