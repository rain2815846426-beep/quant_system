#!/usr/bin/env python3
"""
数据层模块测试脚本

验证数据下载功能是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils import init_database, get_db_connection, setup_logger
from config.settings import DATABASE_PATH

logger = setup_logger("test_data_layer")


def test_database_init():
    """测试数据库初始化"""
    logger.info("测试：数据库初始化")
    init_database(DATABASE_PATH)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 检查所有表是否创建
        tables = [
            "daily_prices",
            "financial_data",
            "factor_values",
            "predictions",
            "index_prices",
            "index_components",
            "industry_classification",
            "stock_list",
        ]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"  表 {table}: {count} 条记录")
    
    logger.info("数据库初始化测试通过 ✓\n")


def test_stock_list():
    """测试股票列表获取"""
    logger.info("测试：获取股票列表")
    from src.data_fetch import fetch_stock_list
    
    df = fetch_stock_list(DATABASE_PATH)
    
    if not df.empty:
        logger.info(f"  获取到 {len(df)} 只股票")
        logger.info(f"  示例：{df.iloc[0].to_dict()}")
        logger.info("股票列表获取测试通过 ✓\n")
    else:
        logger.warning("  股票列表为空，可能网络问题 ✗\n")


def test_daily_prices():
    """测试日线数据获取（仅测试 1 只股票）"""
    logger.info("测试：获取日线行情数据（测试 1 只股票）")
    from src.data_fetch import fetch_single_stock_daily_prices
    
    # 测试贵州茅台
    ts_code = "600519.SH"
    df = fetch_single_stock_daily_prices(ts_code, start_date="20230101", end_date="20231231")
    
    if not df.empty:
        logger.info(f"  获取到 {len(df)} 条日线数据")
        logger.info(f"  字段：{list(df.columns)}")
        logger.info("日线数据获取测试通过 ✓\n")
    else:
        logger.warning("  日线数据为空，可能网络问题 ✗\n")


def test_index_data():
    """测试指数数据获取"""
    logger.info("测试：获取指数行情数据")
    from src.data_fetch import fetch_index_prices
    
    # 测试沪深 300
    index_code = "000300"
    df = fetch_index_prices(index_code, start_date="20230101", end_date="20231231", db_path=DATABASE_PATH)
    
    if not df.empty:
        logger.info(f"  获取到 {len(df)} 条指数数据")
        logger.info("指数数据获取测试通过 ✓\n")
    else:
        logger.warning("  指数数据为空，可能网络问题 ✗\n")


def main():
    logger.info("=" * 60)
    logger.info("数据层模块测试")
    logger.info("=" * 60 + "\n")
    
    # 测试数据库初始化
    test_database_init()
    
    # 测试股票列表
    test_stock_list()
    
    # 测试日线数据
    test_daily_prices()
    
    # 测试指数数据
    test_index_data()
    
    logger.info("=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)
    logger.info("\n提示：")
    logger.info("1. 如果测试通过，可以运行以下命令下载全部数据：")
    logger.info("   python scripts/download_data.py")
    logger.info("\n2. 如果测试失败，请检查网络连接或 Akshare 是否正常工作")


if __name__ == "__main__":
    main()
