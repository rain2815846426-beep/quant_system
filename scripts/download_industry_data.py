#!/usr/bin/env python3
"""
行业数据下载脚本

从多个数据源下载行业分类数据
确保数据质量和完整性

使用:
    python3 scripts/download_industry_data.py
"""
import sys
from pathlib import Path
import pandas as pd
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger

logger = setup_logger("download_industry")


def download_from_akshare(max_retries: int = 3) -> pd.DataFrame:
    """
    从 Akshare 下载行业分类数据
    
    Args:
        max_retries: 最大重试次数
        
    Returns:
        行业数据 DataFrame
    """
    import akshare as ak
    
    for attempt in range(max_retries):
        try:
            logger.info(f"尝试下载行业数据 (尝试 {attempt+1}/{max_retries})...")
            
            # 下载申万行业分类
            df = ak.stock_board_industry_name_em()
            
            if len(df) > 0:
                logger.info(f"成功下载 {len(df)} 条行业数据")
                return df
            
            logger.warning("下载的数据为空")
            
        except Exception as e:
            logger.error(f"下载失败：{e}")
            
            if attempt < max_retries - 1:
                logger.info("等待 5 秒后重试...")
                time.sleep(5)
    
    return pd.DataFrame()


def process_industry_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    处理行业数据
    
    Args:
        df: 原始行业数据
        
    Returns:
        处理后的数据
    """
    if df.empty:
        return df
    
    # 标准化列名
    column_mapping = {
        '代码': 'symbol',
        '名称': 'name',
        '行业': 'industry',
        '板块': 'board',
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
    
    # 生成 ts_code
    def generate_ts_code(code):
        code = str(code).zfill(6)
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        else:
            return f"{code}.SH"
    
    if 'symbol' in df.columns:
        df['ts_code'] = df['symbol'].apply(generate_ts_code)
    
    return df


def save_to_database(df: pd.DataFrame, db_path=DATABASE_PATH):
    """
    保存行业数据到数据库
    
    Args:
        df: 行业数据 DataFrame
        db_path: 数据库路径
    """
    if df.empty:
        logger.warning("数据为空，跳过保存")
        return
    
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        saved_count = 0
        
        for _, row in df.iterrows():
            ts_code = row.get('ts_code', '')
            industry = row.get('industry', row.get('行业', ''))
            
            if ts_code and industry:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO industry_classification 
                        (ts_code, industry_name, industry_code, classification_date)
                        VALUES (?, ?, ?, ?)
                    """, (
                        ts_code,
                        industry,
                        row.get('board', ''),
                        '20260313'
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.debug(f"保存失败 {ts_code}: {e}")
        
        conn.commit()
    
    logger.info(f"成功保存 {saved_count} 条行业数据")


def verify_data(db_path=DATABASE_PATH) -> dict:
    """
    验证数据库中的行业数据
    
    Args:
        db_path: 数据库路径
        
    Returns:
        统计信息字典
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM industry_classification")
        total_count = cursor.fetchone()[0]
        
        # 不同行业数量
        cursor.execute("SELECT COUNT(DISTINCT industry_name) FROM industry_classification")
        industry_count = cursor.fetchone()[0]
        
        # 有行业数据的股票数
        cursor.execute("""
            SELECT COUNT(DISTINCT ts_code) 
            FROM industry_classification 
            WHERE industry_name IS NOT NULL AND industry_name != ''
        """)
        valid_count = cursor.fetchone()[0]
        
        # 前 10 大行业
        cursor.execute("""
            SELECT industry_name, COUNT(*) as stock_count
            FROM industry_classification
            WHERE industry_name IS NOT NULL AND industry_name != ''
            GROUP BY industry_name
            ORDER BY stock_count DESC
            LIMIT 10
        """)
        top_industries = cursor.fetchall()
    
    return {
        'total_records': total_count,
        'industry_count': industry_count,
        'valid_stocks': valid_count,
        'top_industries': top_industries
    }


def main():
    print("="*70)
    print("行业数据下载")
    print("="*70)
    
    # 1. 下载数据
    print("\n[1/4] 下载行业数据...")
    industry_df = download_from_akshare(max_retries=3)
    
    if industry_df.empty:
        print("  ❌ 下载失败，使用备用方案")
        # 备用方案：使用简化行业数据
        from src.factor_processing.simple_industry import get_simple_industry_map
        
        simple_map = get_simple_industry_map()
        industry_df = pd.DataFrame([
            {'ts_code': ts_code, 'industry': industry}
            for ts_code, industry in simple_map.items()
        ])
        print(f"  使用简化行业数据：{len(industry_df)} 只股票")
    
    # 2. 处理数据
    print("\n[2/4] 处理行业数据...")
    processed_df = process_industry_data(industry_df)
    print(f"  处理后数据：{len(processed_df)} 条")
    
    # 3. 保存数据
    print("\n[3/4] 保存到数据库...")
    save_to_database(processed_df)
    
    # 4. 验证数据
    print("\n[4/4] 验证数据...")
    stats = verify_data()
    
    print(f"\n  总记录数：{stats['total_records']}")
    print(f"  行业数量：{stats['industry_count']}")
    print(f"  有效股票：{stats['valid_stocks']}")
    
    print(f"\n  前 10 大行业:")
    for industry, count in stats['top_industries']:
        print(f"    {industry}: {count} 只股票")
    
    print("\n" + "="*70)
    print("行业数据下载完成！")
    print("="*70)


if __name__ == "__main__":
    main()
