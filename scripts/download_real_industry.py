#!/usr/bin/env python3
"""
行业数据下载脚本（后台运行）

只下载成分股（约 1300 只）的行业数据
预计时间：10-20 分钟（增加延迟避免网络问题）

使用:
    nohup python3 scripts/download_real_industry.py > logs/industry_download.log 2>&1 &
"""
import sys
from pathlib import Path
import time
import random

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger
import akshare as ak
import pandas as pd

logger = setup_logger("download_industry")

print("="*70)
print("行业数据下载（成分股）")
print("="*70)

# 1. 获取成分股列表
print("\n[1/4] 获取成分股列表...")

with get_db_connection(DATABASE_PATH) as conn:
    component_df = pd.read_sql_query('''
        SELECT DISTINCT ts_code FROM index_components
        WHERE index_code IN ('000300', '000905', '000852')
    ''', conn)

print(f"  成分股数量：{len(component_df)}")

# 2. 下载行业数据
print("\n[2/4] 下载行业数据...")
print(f"  预计时间：{len(component_df) * 0.5 / 60:.1f} 分钟")

industry_data = []
errors = []
retry_count = 0
max_retries = 3

for i, row in component_df.iterrows():
    ts_code = row['ts_code']
    symbol = ts_code.split('.')[0]
    
    success = False
    for attempt in range(max_retries):
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
                success = True
                retry_count = 0  # 重置重试计数
                break
            else:
                logger.warning(f"{ts_code}: 无行业信息")
                break
                
        except Exception as e:
            logger.debug(f"{ts_code} 失败 (尝试{attempt+1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # 指数退避 + 随机抖动
                wait_time = (attempt + 1) * 2 + random.uniform(0.5, 1.5)
                time.sleep(wait_time)
            else:
                errors.append({'ts_code': ts_code, 'error': str(e)})
                retry_count += 1
    
    # 进度报告
    if (i + 1) % 50 == 0:
        progress = (i+1) / len(component_df) * 100
        elapsed = (i+1) * 0.5 / 60
        print(f"  进度：{i+1}/{len(component_df)} ({progress:.1f}%), 已获取 {len(industry_data)} 条，失败 {len(errors)} 条")
        
        # 如果连续失败太多，暂停一下
        if retry_count > 10:
            print(f"  连续失败{retry_count}次，暂停 30 秒...")
            time.sleep(30)
            retry_count = 0
    
    # 避免请求过快
    time.sleep(0.3 + random.uniform(0, 0.2))

print(f"\n  成功：{len(industry_data)} 条")
print(f"  失败：{len(errors)} 条")
print(f"  成功率：{len(industry_data)/len(component_df)*100:.1f}%")

# 3. 保存到数据库
print("\n[3/4] 保存到数据库...")

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

# 4. 保存错误日志
print("\n[4/4] 保存错误日志...")

if errors:
    error_df = pd.DataFrame(errors)
    error_df.to_csv('logs/industry_download_errors.csv', index=False)
    print(f"  错误日志：logs/industry_download_errors.csv ({len(errors)} 条)")
else:
    print(f"  ✅ 无错误")

print("\n" + "="*70)
print("行业数据下载完成！")
print("="*70)
