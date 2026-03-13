"""
财务数据抓取

获取 A 股股票的财务指标数据（PE、PB、ROE 等）
"""
import akshare as ak
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger

logger = setup_logger("data_fetch")


def fetch_financial_data(ts_code: str, db_path: Path = DATABASE_PATH) -> pd.DataFrame:
    """
    获取单只股票的财务数据
    
    Args:
        ts_code: 股票代码
        db_path: 数据库路径
        
    Returns:
        pd.DataFrame: 财务数据
    """
    try:
        # 提取股票代码（去掉交易所后缀）
        symbol = ts_code.split('.')[0]
        
        # 使用 akshare 获取财务指标
        # 获取主要财务指标
        df = ak.stock_financial_analysis_indicator(symbol=symbol)
        
        if df.empty:
            logger.warning(f"股票 {ts_code} 财务数据为空")
            return pd.DataFrame()
        
        # 数据清洗和处理
        df = _process_financial_data(df, ts_code)
        
        # 保存到数据库
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO financial_data 
                    (ts_code, report_date, pe, pb, roe, roa, revenue, profit, debt_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["ts_code"],
                    row["report_date"],
                    row.get("pe"),
                    row.get("pb"),
                    row.get("roe"),
                    row.get("roa"),
                    row.get("revenue"),
                    row.get("profit"),
                    row.get("debt_ratio")
                ))
            
            conn.commit()
        
        logger.info(f"成功获取 {ts_code} 财务数据，共 {len(df)} 条")
        return df
        
    except Exception as e:
        logger.error(f"获取 {ts_code} 财务数据失败：{e}")
        return pd.DataFrame()


def _process_financial_data(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    """
    处理财务数据
    
    Args:
        df: 原始数据
        ts_code: 股票代码
        
    Returns:
        pd.DataFrame: 处理后的数据
    """
    # akshare 返回的字段可能包括：
    # 日期、ROE、ROA、销售净利率、资产负债率、净利润、营业收入等
    
    # 字段映射
    column_mapping = {
        "日期": "report_date",
        "净资产收益率 (%)": "roe",
        "总资产报酬率 (%)": "roa",
        "销售净利率 (%)": "net_profit_margin",
        "资产负债率 (%)": "debt_ratio",
        "净利润 (元)": "profit",
        "营业收入 (元)": "revenue",
        "每股净资产": "bvps",
        "每股收益": "eps",
    }
    
    # 重命名列
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
    
    # 添加股票代码
    df["ts_code"] = ts_code
    
    # 格式化日期
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"]).dt.strftime("%Y%m%d")
    
    # 计算 PE 和 PB（如果数据中存在每股收益和每股净资产）
    if "eps" in df.columns and "close_price" in df.columns:
        df["pe"] = df["close_price"] / df["eps"]
    if "bvps" in df.columns and "close_price" in df.columns:
        df["pb"] = df["close_price"] / df["bvps"]
    
    # 选择需要的列
    final_cols = ["ts_code", "report_date", "pe", "pb", "roe", "roa", "revenue", "profit", "debt_ratio"]
    final_cols = [col for col in final_cols if col in df.columns]
    
    return df[final_cols]


def fetch_all_financial_data(db_path: Path = DATABASE_PATH) -> int:
    """
    获取所有股票的财务数据
    
    Args:
        db_path: 数据库路径
        
    Returns:
        int: 成功获取的股票数量
    """
    from src.data_fetch.stock_list import fetch_stock_list
    
    # 获取股票列表
    stock_list = fetch_stock_list()
    
    if stock_list.empty:
        logger.error("无法获取股票列表")
        return 0
    
    logger.info(f"开始获取财务数据，共 {len(stock_list)} 只股票")
    
    success_count = 0
    total_count = len(stock_list)
    
    for idx, row in stock_list.iterrows():
        ts_code = row["ts_code"]
        
        # 获取财务数据
        df = fetch_financial_data(ts_code, db_path)
        
        if not df.empty:
            success_count += 1
        
        if success_count % 50 == 0:
            logger.info(f"进度：{success_count}/{total_count}")
    
    logger.info(f"财务数据获取完成，成功：{success_count}/{total_count}")
    return success_count
