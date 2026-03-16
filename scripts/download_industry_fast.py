#!/usr/bin/env python3
"""
行业数据快速下载脚本

批量下载，减少网络请求次数
预计时间：5-10 分钟
"""
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection
import akshare as ak
import pandas as pd

print("="*70)
print("行业数据快速下载")
print("="*70)

# 获取成分股列表
print("\n[1/3] 获取成分股...")
with get_db_connection(DATABASE_PATH) as conn:
    component_df = pd.read_sql_query('''
        SELECT DISTINCT ts_code FROM index_components
        WHERE index_code IN ('000300', '000905', '000852')
    ''', conn)

print(f"  成分股数量：{len(component_df)}")

# 批量下载行业数据
print("\n[2/3] 下载行业数据...")

# 尝试使用行业板块数据
try:
    print("  尝试下载申万行业成分股...")
    
    # 获取行业列表
    industry_list_df = ak.stock_board_industry_name_em()
    print(f"  行业数量：{len(industry_list_df)}")
    
    industry_data = []
    
    # 下载每个行业的成分股
    for idx, row in industry_list_df.iterrows():
        industry_name = row['板块']
        industry_code = row['代码']
        
        try:
            # 获取行业成分股
            cons_df = ak.stock_board_industry_cons_em(symbol=industry_code)
            
            if '股票代码' in cons_df.columns:
                for _, stock_row in cons_df.iterrows():
                    symbol = str(stock_row['股票代码']).zfill(6)
                    ts_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                    
                    industry_data.append({
                        'ts_code': ts_code,
                        'industry': industry_name
                    })
            
            if (idx + 1) % 10 == 0:
                print(f"  进度：{idx+1}/{len(industry_list_df)}")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  跳过 {industry_name}: {e}")
    
    print(f"\n  获取到 {len(industry_data)} 条行业数据")
    
except Exception as e:
    print(f"  失败：{e}")
    industry_data = []

# 保存到数据库
print("\n[3/3] 保存到数据库...")

if industry_data:
    industry_df = pd.DataFrame(industry_data)
    
    # 去重
    industry_df = industry_df.drop_duplicates(subset=['ts_code'])
    
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # 清空旧数据
        cursor.execute('DELETE FROM industry_classification')
        
        for _, row in industry_df.iterrows():
            cursor.execute("""
                INSERT OR REPLACE INTO industry_classification 
                (ts_code, industry_name, classification_date)
                VALUES (?, ?, ?)
            """, (row['ts_code'], row['industry'], '20260313'))
        
        conn.commit()
    
    print(f"  ✅ 已保存")
    
    # 验证
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM industry_classification')
        count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT industry_name) FROM industry_classification')
        ind_count = cursor.fetchone()[0]
        
        # 前 10 大行业
        cursor.execute("""
            SELECT industry_name, COUNT(*) as stock_count
            FROM industry_classification
            GROUP BY industry_name
            ORDER BY stock_count DESC
            LIMIT 10
        """)
        top_industries = cursor.fetchall()
    
    print(f"\n  数据库记录：{count} 条")
    print(f"  行业数量：{ind_count} 个")
    print(f"\n  前 10 大行业:")
    for ind, cnt in top_industries:
        print(f"    {ind}: {cnt} 只股票")
else:
    print("  ❌ 无数据保存")

print("\n" + "="*70)
print("行业数据下载完成！")
print("="*70)
