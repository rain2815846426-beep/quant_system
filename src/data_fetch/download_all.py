"""
数据下载统一入口脚本

用于一次性下载所有需要的数据
"""
import argparse
from pathlib import Path

from config.settings import DATABASE_PATH, DATA_START_DATE
from src.utils import init_database, setup_logger

logger = setup_logger("data_download")


def download_all_data(start_date: str = DATA_START_DATE, end_date: str = None):
    """
    下载所有数据
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    """
    from src.data_fetch import (
        fetch_stock_list,
        fetch_all_daily_prices,
        fetch_all_index_prices,
        fetch_all_financial_data,
        fetch_all_index_components,
        fetch_all_industry_classification,
    )
    
    logger.info("=" * 60)
    logger.info("开始下载所有数据")
    logger.info("=" * 60)
    
    # 初始化数据库
    logger.info("步骤 1/6: 初始化数据库")
    init_database(DATABASE_PATH)
    
    # 获取股票列表
    logger.info("步骤 2/6: 获取股票列表")
    stock_list = fetch_stock_list(DATABASE_PATH)
    if stock_list.empty:
        logger.error("获取股票列表失败，终止下载")
        return
    
    # 获取日线行情
    logger.info("步骤 3/6: 获取日线行情数据（可能需要较长时间）")
    fetch_all_daily_prices(start_date, end_date, DATABASE_PATH)
    
    # 获取指数数据
    logger.info("步骤 4/6: 获取指数行情数据")
    fetch_all_index_prices(start_date, end_date, DATABASE_PATH)
    
    # 获取指数成分股
    logger.info("步骤 5/6: 获取指数成分股")
    fetch_all_index_components(DATABASE_PATH)
    
    # 获取财务数据
    logger.info("步骤 6/6: 获取财务数据（可能需要较长时间）")
    fetch_all_financial_data(DATABASE_PATH)
    
    # 获取行业分类
    logger.info("获取行业分类数据")
    fetch_all_industry_classification(DATABASE_PATH)
    
    logger.info("=" * 60)
    logger.info("所有数据下载完成！")
    logger.info(f"数据库路径：{DATABASE_PATH}")
    logger.info("=" * 60)


def update_data():
    """
    更新数据（只获取新增数据）
    """
    from src.data_fetch import (
        fetch_stock_list,
        update_daily_prices,
        fetch_all_index_prices,
        fetch_all_financial_data,
    )
    
    logger.info("=" * 60)
    logger.info("开始更新数据")
    logger.info("=" * 60)
    
    # 初始化数据库
    init_database(DATABASE_PATH)
    
    # 更新股票列表
    logger.info("步骤 1/4: 更新股票列表")
    fetch_stock_list(DATABASE_PATH)
    
    # 更新日线行情
    logger.info("步骤 2/4: 更新日线行情数据")
    update_daily_prices(DATABASE_PATH)
    
    # 更新指数数据
    logger.info("步骤 3/4: 更新指数数据")
    fetch_all_index_prices(db_path=DATABASE_PATH)
    
    # 更新财务数据
    logger.info("步骤 4/4: 更新财务数据")
    fetch_all_financial_data(DATABASE_PATH)
    
    logger.info("=" * 60)
    logger.info("数据更新完成！")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="量化系统数据下载工具")
    parser.add_argument(
        "--action",
        type=str,
        choices=["download", "update"],
        default="download",
        help="操作类型：download(下载全部) 或 update(更新数据)"
    )
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
    
    if args.action == "download":
        download_all_data(args.start_date, args.end_date)
    elif args.action == "update":
        update_data()


if __name__ == "__main__":
    main()
