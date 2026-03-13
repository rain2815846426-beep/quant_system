"""
A 股日线行情数据抓取

使用 Akshare 获取 A 股日线行情数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import DATA_START_DATE, DATABASE_PATH
from src.utils import get_db_connection, setup_logger, format_date, validate_date_format

logger = setup_logger("data_fetch")


def fetch_single_stock_daily_prices(ts_code: str, start_date: str = DATA_START_DATE, end_date: str = None) -> pd.DataFrame:
    """
    获取单只股票的日线行情数据
    
    Args:
        ts_code: 股票代码（格式：000001.SZ 或 600000.SH）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD），默认为 None（使用当前日期）
        
    Returns:
        pd.DataFrame: 日线行情数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    start_date = format_date(start_date)
    end_date = format_date(end_date)
    
    try:
        # 使用 akshare 获取日线数据
        # 注意：akshare 的股票代码格式可能需要转换
        symbol = ts_code.split('.')[0]
        exchange = ts_code.split('.')[1]
        
        # 根据交易所选择接口
        if exchange == "SH":
            # 上交所股票
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        else:
            # 深交所股票
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df.empty:
            logger.warning(f"股票 {ts_code} 无数据返回")
            return pd.DataFrame()
        
        # 数据清洗和格式化
        df = _process_daily_prices(df, ts_code)
        
        logger.info(f"成功获取 {ts_code} 日线数据，共 {len(df)} 条")
        return df
        
    except Exception as e:
        logger.error(f"获取 {ts_code} 日线数据失败：{e}")
        return pd.DataFrame()


def _process_daily_prices(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    """
    处理日线行情数据，统一字段格式
    
    Args:
        df: 原始数据
        ts_code: 股票代码
        
    Returns:
        pd.DataFrame: 处理后的数据
    """
    # 重命名字段（根据 akshare 实际返回字段调整）
    column_mapping = {
        "日期": "trade_date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "turnover",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover_rate",
    }
    
    # 只保留需要的列
    keep_cols = ["日期", "开盘", "最高", "最低", "收盘", "成交量", "成交额", "换手率"]
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
    
    # 检查哪些列存在
    final_cols = [col for col in final_cols if col in df.columns]
    df = df[final_cols]
    
    # 添加复权因子（暂时用 1 填充，后续可以完善）
    df["adj_factor"] = 1.0
    
    return df


def fetch_all_daily_prices(start_date: str = DATA_START_DATE, end_date: str = None, 
                           db_path: Path = DATABASE_PATH) -> int:
    """
    获取所有 A 股的日线行情数据并保存到数据库
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        db_path: 数据库路径
        
    Returns:
        int: 成功保存的股票数量
    """
    from src.data_fetch.stock_list import fetch_stock_list
    
    # 初始化数据库
    from src.utils import init_database
    init_database(db_path)
    
    # 获取股票列表
    stock_list = fetch_stock_list()
    
    if stock_list.empty:
        logger.error("无法获取股票列表")
        return 0
    
    logger.info(f"开始获取日线行情数据，共 {len(stock_list)} 只股票")
    
    success_count = 0
    total_count = len(stock_list)
    
    for idx, row in stock_list.iterrows():
        ts_code = row["ts_code"]
        
        # 检查是否已存在该股票的数据
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM daily_prices WHERE ts_code = ?",
                (ts_code,)
            )
            existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            logger.info(f"跳过已存在数据的股票：{ts_code}")
            success_count += 1
            continue
        
        # 获取日线数据
        df = fetch_single_stock_daily_prices(ts_code, start_date, end_date)
        
        if df.empty:
            continue
        
        # 保存到数据库
        try:
            with get_db_connection(db_path) as conn:
                cursor = conn.cursor()
                
                for _, row_data in df.iterrows():
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_prices 
                        (ts_code, trade_date, open, high, low, close, volume, turnover, adj_factor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row_data["ts_code"],
                        row_data["trade_date"],
                        row_data.get("open"),
                        row_data.get("high"),
                        row_data.get("low"),
                        row_data.get("close"),
                        row_data.get("volume"),
                        row_data.get("turnover"),
                        row_data.get("adj_factor", 1.0)
                    ))
                
                conn.commit()
            
            success_count += 1
            
            if success_count % 100 == 0:
                logger.info(f"进度：{success_count}/{total_count}")
                
        except Exception as e:
            logger.error(f"保存 {ts_code} 数据失败：{e}")
    
    logger.info(f"日线行情数据获取完成，成功：{success_count}/{total_count}")
    return success_count


def update_daily_prices(db_path: Path = DATABASE_PATH) -> int:
    """
    更新日线行情数据（只获取最新数据）
    
    Args:
        db_path: 数据库路径
        
    Returns:
        int: 更新的股票数量
    """
    from src.data_fetch.stock_list import fetch_stock_list
    
    # 获取股票列表
    stock_list = fetch_stock_list()
    
    if stock_list.empty:
        logger.error("无法获取股票列表")
        return 0
    
    # 获取当前日期
    today = datetime.now().strftime("%Y%m%d")
    
    # 获取数据库中每个股票的最新日期
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        update_count = 0
        
        for idx, row in stock_list.iterrows():
            ts_code = row["ts_code"]
            
            # 查询该股票的最新日期
            cursor.execute(
                "SELECT MAX(trade_date) FROM daily_prices WHERE ts_code = ?",
                (ts_code,)
            )
            result = cursor.fetchone()[0]
            
            if result is None:
                # 没有数据，获取全部历史数据
                start = DATA_START_DATE
            else:
                start = result
                # 如果已经是最新日期，跳过
                if start >= today:
                    continue
            
            # 获取从最新日期到今天的数据
            df = fetch_single_stock_daily_prices(ts_code, start, today)
            
            if df.empty:
                continue
            
            # 保存到数据库
            for _, row_data in df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_prices 
                    (ts_code, trade_date, open, high, low, close, volume, turnover, adj_factor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_data["ts_code"],
                    row_data["trade_date"],
                    row_data.get("open"),
                    row_data.get("high"),
                    row_data.get("low"),
                    row_data.get("close"),
                    row_data.get("volume"),
                    row_data.get("turnover"),
                    row_data.get("adj_factor", 1.0)
                ))
            
            update_count += 1
        
        conn.commit()
    
    logger.info(f"日线行情数据更新完成，更新：{update_count} 只股票")
    return update_count
