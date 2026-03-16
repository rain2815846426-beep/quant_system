#!/usr/bin/env python3
"""
行业数据下载脚本（后台运行）

只下载成分股（约 1300 只）的行业数据
预计时间：5-10 分钟

使用:
    nohup python3 scripts/download_real_industry.py > logs/industry_download.log 2>&1 &
"""
import sys
from pathlib import Path
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection
import akshare as ak
import pandas as pd

print("="*70)
print("行业数据下载（成分股）")
print("="*70)

# 1. 获取成分股列表
print("\n[1/3] 获取成分股列表...")

with get_db_connection(DATABASE_PATH) as conn:
    component_df = pd.read_sql_query('''
        SELECT DISTINCT ts_code FROM index_components
        WHERE index_code IN ('000300', '000905', '000852')
    ''', conn)

print(f"  成分股数量：{len(component_df)}")

# 2. 下载行业数据
print("\n[2/3] 下载行业数据...")
print(f"  预计时间：{len(component_df) * 0.3 / 60:.1f} 分钟")

industry_data = []
errors = []

for i, row in component_df.iterrows():
    ts_code = row['ts_code']
    symbol = ts_code.split('.')[0]
    
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        
        # 获取行业信息
        industry_row = df[df['item'] == '行业']
        
        if len(industry_row) > 0:
            industry = industry_row['value'].values[0]
            industry_data.append({
                'ts_code': ts_code,
                'industry': industry
            })
        
        if (i + 1) % 100 == 0:
            elapsed = (i + 1) * 0.3 / 60
            print(f"  进度：{i+1}/{len(component_df)} ({(i+1)/len(component_df)*100:.1f}%), 已获取 {len(industry_data)} 条")
        
        # 避免请求过快
        time.sleep(0.3)
        
    except Exception as e:
        errors.append({'ts_code': ts_code, 'error': str(e)})
        if len(errors) % 50 == 0:
            print(f"  失败：{len(errors)} 条")

print(f"\n  成功：{len(industry_data)} 条")
print(f"  失败：{len(errors)} 条")

# 3. 保存到数据库
print("\n[3/3] 保存到数据库...")

if industry_data:
    industry_df = pd.DataFrame(industry_data)
    
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

print("\n" + "="*70)
print("行业数据下载完成！")
print("="*70)

# 保存错误日志
if errors:
    error_df = pd.DataFrame(errors)
    error_df.to_csv('logs/industry_download_errors.csv', index=False)
    print(f"\n错误日志已保存：logs/industry_download_errors.csv")
