"""
指数成分股数据抓取

获取沪深 300、中证 500、中证 1000 等指数的成分股信息
"""
import akshare as ak
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_PATH, INDEX_CODES
from src.utils import get_db_connection, setup_logger

logger = setup_logger("data_fetch")


def fetch_index_components(index_code: str, db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """
    获取单个指数的成分股信息
    
    Args:
        index_code: 指数代码（如 000300）
        db_path: 数据库路径
        
    Returns:
        pd.DataFrame: 成分股信息
    """
    try:
        # 使用 akshare 获取指数成分股
        df = ak.index_stock_cons(symbol=index_code)
        
        if df.empty:
            logger.warning(f"指数 {index_code} 成分股数据为空")
            return pd.DataFrame()
        
        # 数据清洗
        df = _process_components_data(df, index_code)
        
        # 保存到数据库
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO index_components 
                    (index_code, ts_code, entry_date, exit_date)
                    VALUES (?, ?, ?, ?)
                """, (
                    row["index_code"],
                    row["ts_code"],
                    row.get("entry_date"),
                    row.get("exit_date", "")
                ))
            
            conn.commit()
        
        logger.info(f"成功获取指数 {index_code} 成分股，共 {len(df)} 只")
        return df
        
    except Exception as e:
        logger.error(f"获取指数 {index_code} 成分股失败：{e}")
        return pd.DataFrame()


def _process_components_data(df: pd.DataFrame, index_code: str) -> pd.DataFrame:
    """
    处理成分股数据
    
    Args:
        df: 原始数据
        index_code: 指数代码
        
    Returns:
        pd.DataFrame: 处理后的数据
    """
    # akshare 返回的字段可能包括：
    # 品种代码、品种名称、入选日期、剔除日期等
    
    # 字段映射（根据实际返回调整）
    column_mapping = {
        "品种代码": "symbol",
        "品种名称": "name",
        "入选日期": "entry_date",
        "剔除日期": "exit_date",
    }
    
    # 重命名列
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
    
    # 生成 ts_code
    def generate_ts_code(code):
        code = str(code)
        if code.startswith("6"):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"
    
    if "symbol" in df.columns:
        df["ts_code"] = df["symbol"].apply(generate_ts_code)
    
    # 添加指数代码
    df["index_code"] = index_code
    
    # 格式化日期
    for date_col in ["entry_date", "exit_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col]).dt.strftime("%Y%m%d")
    
    # 选择需要的列
    final_cols = ["index_code", "ts_code", "entry_date", "exit_date"]
    final_cols = [col for col in final_cols if col in df.columns]
    
    return df[final_cols]


def fetch_all_index_components(db_path: Path = DATABASE_PATH) -> int:
    """
    获取所有配置指数的成分股信息
    
    Args:
        db_path: 数据库路径
        
    Returns:
        int: 成功获取的指数数量
    """
    success_count = 0
    
    logger.info(f"开始获取指数成分股数据")
    
    for index_name, index_code in INDEX_CODES.items():
        df = fetch_index_components(index_code, db_path)
        if not df.empty:
            success_count += 1
    
    logger.info(f"指数成分股数据获取完成，成功：{success_count}/{len(INDEX_CODES)}")
    return success_count
