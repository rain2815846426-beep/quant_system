#!/usr/bin/env python3
"""
每日数据更新脚本（修复版）

用于每日收盘后更新最新数据（只获取新增数据）

功能：
- 自动识别每个股票的最新日期
- 只下载新增数据
- 批量更新，降低接口压力
- 周末自动处理

使用方法:
    python3 scripts/update_daily.py
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import init_database, setup_logger, get_db_connection
from src.data_fetch import (
    fetch_stock_list,
    update_daily_prices,
    fetch_all_index_prices,
)

logger = setup_logger("daily_update")


def get_latest_trade_date(db_path=DATABASE_PATH) -> str:
    """获取数据库中最新的交易日期"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        result = cursor.fetchone()[0]
        return result if result else "20100101"


def main():
    logger.info("=" * 70)
    logger.info("开始每日数据更新")
    logger.info("=" * 70)
    
    # 初始化数据库
    init_database(DATABASE_PATH)
    
    # 获取最新日期
    latest_date = get_latest_trade_date()
    logger.info(f"数据库最新日期：{latest_date}")
    
    # 计算目标日期（今天或最近交易日）
    today = datetime.now()
    
    # 如果是周末，获取最近的工作日
    if today.weekday() >= 5:  # 周六=5, 周日=6
        days_back = 2 if today.weekday() == 6 else 1
        target_date = today - timedelta(days=days_back)
    else:
        target_date = today
    
    target_date_str = target_date.strftime("%Y%m%d")
    logger.info(f"目标日期：{target_date_str}")
    
    if latest_date >= target_date_str:
        logger.info("✅ 数据已是最新，无需更新")
        return
    
    # 1. 更新股票列表
    logger.info("步骤 1/3: 更新股票列表")
    fetch_stock_list(DATABASE_PATH)
    
    # 2. 更新日线行情
    logger.info("步骤 2/3: 更新日线行情数据")
    updated_count = update_daily_prices(DATABASE_PATH)
    logger.info(f"更新股票数量：{updated_count}")
    
    # 3. 更新指数数据
    logger.info("步骤 3/3: 更新指数数据")
    fetch_all_index_prices(db_path=DATABASE_PATH)
    
    logger.info("=" * 70)
    logger.info("数据更新完成！")
    logger.info("=" * 70)
    
    # 显示数据库状态
    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM stock_list")
    stock_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_prices")
    price_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
    latest = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"数据库状态:")
    logger.info(f"  股票数量：{stock_count:,}")
    logger.info(f"  日线记录：{price_count:,}")
    logger.info(f"  最新日期：{latest}")


if __name__ == "__main__":
    main()
