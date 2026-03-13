#!/usr/bin/env python3
"""
下载进度检查脚本

用于随时查看数据下载进度

使用方法:
    python3 scripts/check_download_progress.py
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
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_download_progress():
    """检查下载进度"""
    print_header("数据下载进度检查")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 1. 股票数量统计
    cursor.execute("SELECT COUNT(*) FROM stock_list")
    total_stocks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM daily_prices")
    downloaded_stocks = cursor.fetchone()[0]
    
    # 2. 数据量统计
    cursor.execute("SELECT COUNT(*) FROM daily_prices")
    total_rows = cursor.fetchone()[0]
    
    # 3. 日期范围
    cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM daily_prices")
    row = cursor.fetchone()
    min_date = row[0] if row[0] else "无数据"
    max_date = row[1] if row[1] else "无数据"
    
    # 4. 交易日期数
    cursor.execute("SELECT COUNT(DISTINCT trade_date) FROM daily_prices")
    trade_days = cursor.fetchone()[0]
    
    # 5. 计算进度
    progress_pct = (downloaded_stocks / total_stocks * 100) if total_stocks > 0 else 0
    remaining_stocks = total_stocks - downloaded_stocks
    
    # 6. 估算总量
    # 假设每只股票平均约 2400 个交易日（2010-2026 年）
    estimated_rows_per_stock = 2400
    estimated_total_rows = total_stocks * estimated_rows_per_stock
    estimated_pct = (total_rows / estimated_total_rows * 100) if estimated_total_rows > 0 else 0
    
    conn.close()
    
    # 打印结果
    print(f"\n📊 股票统计")
    print(f"  总股票数：     {total_stocks:,} 只")
    print(f"  已下载：       {downloaded_stocks:,} 只")
    print(f"  剩余：         {remaining_stocks:,} 只")
    print(f"  下载进度：     {progress_pct:.2f}%")
    
    print(f"\n📈 数据量统计")
    print(f"  总记录数：     {total_rows:,} 条")
    print(f"  估算总量：     {estimated_total_rows:,} 条")
    print(f"  数据进度：     {estimated_pct:.2f}%")
    
    print(f"\n📅 日期范围")
    print(f"  最早日期：     {min_date}")
    print(f"  最新日期：     {max_date}")
    print(f"  交易天数：     {trade_days:,} 天")
    
    print(f"\n💾 数据库文件")
    import os
    if DATABASE_PATH.exists():
        db_size_mb = DATABASE_PATH.stat().st_size / (1024 * 1024)
        print(f"  数据库路径：   {DATABASE_PATH}")
        print(f"  文件大小：     {db_size_mb:.2f} MB")
    else:
        print(f"  数据库文件不存在")
    
    # 进度条
    print(f"\n📊 下载进度条")
    bar_length = 50
    filled_length = int(bar_length * progress_pct / 100)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    print(f"  [{bar}] {progress_pct:.1f}%")
    
    # 完成状态
    print(f"\n{'✅ 下载完成！' if progress_pct >= 100 else '⏳ 下载进行中...'}")
    
    if progress_pct < 100:
        print(f"\n💡 提示：继续下载命令")
        print(f"   python3 scripts/download_daily_prices.py")
    
    print()


def check_top_stocks():
    """查看下载数据最多的前 10 只股票"""
    print_header("下载数据最多的前 10 只股票")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ts_code, COUNT(*) as row_count
        FROM daily_prices
        GROUP BY ts_code
        ORDER BY row_count DESC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    print(f"\n{'排名':<6} {'股票代码':<12} {'记录数':>10} {'估算年份':>10}")
    print("-" * 45)
    
    for idx, row in enumerate(rows, 1):
        ts_code, row_count = row
        years = row_count / 250  # 每年约 250 个交易日
        print(f"{idx:<6} {ts_code:<12} {row_count:>10,} {years:>8.1f}年")
    
    conn.close()
    print()


def check_recent_data():
    """查看最新日期的数据"""
    print_header("最新交易日数据")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取最新日期
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    latest_date = cursor.fetchone()[0]
    
    if latest_date:
        cursor.execute("""
            SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?
        """, (latest_date,))
        count = cursor.fetchone()[0]
        
        print(f"\n  最新日期：{latest_date}")
        print(f"  股票数量：{count:,} 只")
        
        # 显示前 5 条
        cursor.execute("""
            SELECT ts_code, open, high, low, close, volume 
            FROM daily_prices 
            WHERE trade_date = ?
            LIMIT 5
        """, (latest_date,))
        
        print(f"\n  示例数据（前 5 条）:")
        print(f"  {'股票代码':<12} {'开盘':>8} {'最高':>8} {'最低':>8} {'收盘':>8} {'成交量':>12}")
        print(f"  {'-'*60}")
        for row in cursor.fetchall():
            print(f"  {row[0]:<12} {row[1]:>8.2f} {row[2]:>8.2f} {row[3]:>8.2f} {row[4]:>8.2f} {int(row[5]):>12,}")
    else:
        print("\n  暂无数据")
    
    conn.close()
    print()


def main():
    print("\n" + "=" * 70)
    print("  A 股数据下载进度检查工具")
    print("=" * 70)
    
    # 检查进度
    check_download_progress()
    
    # 查看 Top 股票
    check_top_stocks()
    
    # 查看最新数据
    check_recent_data()
    
    print("=" * 70)
    print("  检查完成")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
