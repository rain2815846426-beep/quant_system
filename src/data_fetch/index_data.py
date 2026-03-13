"""
指数行情数据抓取

获取沪深 300、中证 500、中证 1000 等指数行情数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import DATA_START_DATE, DATABASE_PATH, INDEX_CODES
from src.utils import get_db_connection, setup_logger, format_date

logger = setup_logger("data_fetch")


def fetch_index_prices(index_code: str, start_date: str = DATA_START_DATE, 
                       end_date: str = None, db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """
    获取单个指数的行情数据
    
    Args:
        index_code: 指数代码（如 000300）
        start_date: 开始日期
        end_date: 结束日期
        db_path: 数据库路径
        
    Returns:
        pd.DataFrame: 指数行情数据
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    start_date = format_date(start_date)
    end_date = format_date(end_date)
    
    try:
        # 使用 akshare 获取指数历史数据
        df = ak.index_zh_a_hist(symbol=index_code, period="daily", start_date=start_date, end_date=end_date)
        
        if df.empty:
            logger.warning(f"指数 {index_code} 无数据返回")
            return pd.DataFrame()
        
        # 数据清洗
        df = _process_index_data(df, index_code)
        
        # 保存到数据库
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO index_prices 
                    (index_code, trade_date, open, high, low, close, volume, turnover)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["index_code"],
                    row["trade_date"],
                    row.get("open"),
                    row.get("high"),
                    row.get("low"),
                    row.get("close"),
                    row.get("volume"),
                    row.get("turnover")
                ))
            
            conn.commit()
        
        logger.info(f"成功获取指数 {index_code} 行情数据，共 {len(df)} 条")
        return df
        
    except Exception as e:
        logger.error(f"获取指数 {index_code} 行情数据失败：{e}")
        return pd.DataFrame()


def _process_index_data(df: pd.DataFrame, index_code: str) -> pd.DataFrame:
    """
    处理指数行情数据
    
    Args:
        df: 原始数据
        index_code: 指数代码
        
    Returns:
        pd.DataFrame: 处理后的数据
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
    
    # 重命名列
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
    
    # 添加指数代码
    df["index_code"] = index_code
    
    # 格式化日期
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
    
    # 选择需要的列
    final_cols = ["index_code", "trade_date", "open", "high", "low", "close", "volume", "turnover"]
    final_cols = [col for col in final_cols if col in df.columns]
    
    return df[final_cols]


def fetch_all_index_prices(start_date: str = DATA_START_DATE, end_date: str = None,
                           db_path: Path = DATABASE_PATH) -> int:
    """
    获取所有配置指数的行情数据
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        db_path: 数据库路径
        
    Returns:
        int: 成功获取的指数数量
    """
    success_count = 0
    
    logger.info(f"开始获取指数行情数据")
    
    for index_name, index_code in INDEX_CODES.items():
        df = fetch_index_prices(index_code, start_date, end_date, db_path)
        if not df.empty:
            success_count += 1
    
    logger.info(f"指数行情数据获取完成，成功：{success_count}/{len(INDEX_CODES)}")
    return success_count
