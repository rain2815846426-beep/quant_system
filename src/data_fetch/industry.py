"""
行业分类数据抓取

获取 A 股股票的申万行业分类信息
"""
import akshare as ak
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger

logger = setup_logger("data_fetch")


def fetch_industry_classification(ts_code: str = None, db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """
    获取股票的行业分类信息
    
    Args:
        ts_code: 股票代码（可选，不传则获取全部）
        db_path: 数据库路径
        
    Returns:
        pd.DataFrame: 行业分类数据
    """
    try:
        # 使用 akshare 获取申万行业分类
        df = ak.stock_board_industry_name_em()
        
        if df.empty:
            logger.warning("行业分类数据为空")
            return pd.DataFrame()
        
        # 数据清洗
        df = _process_industry_data(df)
        
        # 如果指定了股票代码，只返回该股票的分类
        if ts_code:
            df = df[df["ts_code"] == ts_code]
        
        # 保存到数据库
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO industry_classification 
                    (ts_code, industry_name, industry_code, classification_date)
                    VALUES (?, ?, ?, ?)
                """, (
                    row["ts_code"],
                    row["industry_name"],
                    row.get("industry_code", ""),
                    row.get("classification_date", datetime.now().strftime("%Y%m%d"))
                ))
            
            conn.commit()
        
        logger.info(f"成功获取行业分类数据，共 {len(df)} 条")
        return df
        
    except Exception as e:
        logger.error(f"获取行业分类数据失败：{e}")
        return pd.DataFrame()


def _process_industry_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    处理行业分类数据
    
    Args:
        df: 原始数据
        
    Returns:
        pd.DataFrame: 处理后的数据
    """
    # akshare 返回的字段可能包括：
    # 股票代码、股票名称、行业名称、行业代码等
    
    # 字段映射
    column_mapping = {
        "代码": "symbol",
        "名称": "name",
        "行业": "industry_name",
        "行业代码": "industry_code",
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
    
    # 添加分类日期
    df["classification_date"] = datetime.now().strftime("%Y%m%d")
    
    # 选择需要的列
    final_cols = ["ts_code", "industry_name", "industry_code", "classification_date"]
    final_cols = [col for col in final_cols if col in df.columns]
    
    return df[final_cols]


def fetch_all_industry_classification(db_path: Path = DATABASE_PATH) -> int:
    """
    获取全部股票的行业分类信息
    
    Args:
        db_path: 数据库路径
        
    Returns:
        int: 成功获取的记录数量
    """
    df = fetch_industry_classification(None, db_path)
    
    if df.empty:
        logger.error("获取行业分类数据失败")
        return 0
    
    logger.info(f"行业分类数据获取完成，共 {len(df)} 条记录")
    return len(df)
