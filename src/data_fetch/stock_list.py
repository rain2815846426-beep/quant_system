"""
股票列表抓取

获取 A 股股票列表信息
"""
import akshare as ak
import pandas as pd
from pathlib import Path

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger

logger = setup_logger("data_fetch")


def fetch_stock_list(db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """
    获取 A 股股票列表并保存到数据库
    
    Args:
        db_path: 数据库路径
        
    Returns:
        pd.DataFrame: 股票列表数据
    """
    try:
        # 使用 akshare 获取 A 股股票列表
        df = ak.stock_info_a_code_name()
        
        if df.empty:
            logger.warning("股票列表数据为空")
            return pd.DataFrame()
        
        # 数据清洗
        # akshare 返回的字段可能是：code, name
        column_mapping = {
            "code": "symbol",
            "名称": "name",
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # 生成 ts_code（需要根据交易所）
        def generate_ts_code(row):
            code = str(row.get("symbol", row.get("code", "")))
            if code.startswith("6"):
                return f"{code}.SH"
            elif code.startswith("0") or code.startswith("3"):
                return f"{code}.SZ"
            else:
                return f"{code}.SH"  # 默认
        
        df["ts_code"] = df.apply(generate_ts_code, axis=1)
        
        # 添加其他字段（暂时用空值填充）
        df["area"] = ""
        df["industry"] = ""
        df["list_date"] = ""
        df["list_status"] = "L"  # 上市
        
        # 保存到数据库
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO stock_list 
                    (ts_code, symbol, name, area, industry, list_date, list_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["ts_code"],
                    row.get("symbol"),
                    row.get("name"),
                    row.get("area", ""),
                    row.get("industry", ""),
                    row.get("list_date", ""),
                    row.get("list_status", "L")
                ))
            
            conn.commit()
        
        logger.info(f"成功获取股票列表，共 {len(df)} 只股票")
        return df[["ts_code", "symbol", "name", "area", "industry", "list_date", "list_status"]]
        
    except Exception as e:
        logger.error(f"获取股票列表失败：{e}")
        return pd.DataFrame()
