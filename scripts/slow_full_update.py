#!/usr/bin/env python3
"""
全量数据更新（Akshare 单数据源 - 超慢但可靠版）

特点：
1. 只用 Akshare（免费无限制）
2. 每只股票延迟 15 秒（确保不被限流）
3. 最多重试 10 次
4. 批次间暂停 5 分钟
5. 支持断点续传
6. 预计时间：24-48 小时

使用方法:
    nohup python3 scripts/slow_full_update.py > logs/slow_update.log 2>&1 &
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger
import akshare as ak

logger = setup_logger("slow_update")


def get_stock_list() -> list:
    """获取股票列表（成分股优先）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 成分股优先
        cursor.execute("""
            SELECT DISTINCT ts_code FROM index_components
            WHERE index_code IN ('000300', '000905', '000852')
            ORDER BY ts_code
        """)
        components = [row[0] for row in cursor.fetchall()]
        
        # 其他股票
        cursor.execute("SELECT DISTINCT ts_code FROM stock_list ORDER BY ts_code")
        others = [row[0] for row in cursor.fetchall()]
        
        return components + [s for s in others if s not in components]


def get_latest_date(ts_code: str) -> str:
    """获取最新日期"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(trade_date) FROM daily_prices WHERE ts_code = ?",
            (ts_code,)
        )
        result = cursor.fetchone()[0]
        return result if result else "20100101"


def get_target_date() -> str:
    """获取目标日期"""
    today = datetime.now()
    if today.weekday() >= 5:
        days = 2 if today.weekday() == 6 else 1
        return (today - timedelta(days=days)).strftime("%Y%m%d")
    return today.strftime("%Y%m%d")


def update_stock(ts_code: str, start_date: str, end_date: str) -> int:
    """更新单只股票（最多重试 10 次）"""
    symbol = ts_code.split('.')[0]
    
    for attempt in range(10):
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            
            if df.empty:
                if attempt < 9:
                    time.sleep((attempt + 1) * 5)
                    continue
                return 0
            
            # 保存
            df["ts_code"] = ts_code
            df["trade_date"] = pd.to_datetime(df["日期"]).dt.strftime("%Y%m%d")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for _, row in df.iterrows():
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_prices 
                        (ts_code, trade_date, open, high, low, close, volume, turnover, adj_factor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ts_code,
                        row["trade_date"],
                        row.get("开盘"),
                        row.get("最高"),
                        row.get("最低"),
                        row.get("收盘"),
                        row.get("成交量"),
                        row.get("成交额"),
                        1.0
                    ))
                conn.commit()
            
            return len(df)
            
        except Exception as e:
            if attempt < 9:
                wait = (attempt + 1) * 10
                logger.debug(f"失败，{wait}秒后重试 ({attempt+1}/10)")
                time.sleep(wait)
            else:
                logger.error(f"更新失败：{e}")
                return -1
    
    return 0


def slow_full_update():
    """超慢全量更新"""
    print("="*70)
    print("全量数据更新（超慢可靠版）")
    print("="*70)
    
    start = datetime.now()
    print(f"开始：{start.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 股票列表
    print("\n[1/4] 获取股票列表...")
    stocks = get_stock_list()
    total = len(stocks)
    print(f"  总数：{total} 只")
    
    # 目标日期
    print("\n[2/4] 目标日期...")
    target = get_target_date()
    print(f"  {target}")
    
    # 更新
    print(f"\n[3/4] 开始更新...")
    print(f"  延迟：15 秒/只")
    print(f"  重试：10 次")
    print(f"  预计：{total * 15 / 3600:.1f} 小时")
    
    updated = failed = skipped = rows = 0
    
    for i, ts_code in enumerate(stocks, 1):
        latest = get_latest_date(ts_code)
        
        if latest >= target:
            skipped += 1
            continue
        
        r = update_stock(ts_code, latest, target)
        
        if r > 0:
            updated += 1
            rows += r
        elif r < 0:
            failed += 1
        
        # 进度
        if i % 10 == 0:
            pct = i / total * 100
            elapsed = (datetime.now() - start).total_seconds() / 3600
            remaining = elapsed / i * (total - i) if i > 0 else 0
            print(f"[{i}/{total}] {ts_code} - {pct:.1f}%, 剩余{remaining:.1f}小时")
        
        # 延迟
        time.sleep(15)
    
    # 完成
    end = datetime.now()
    duration = (end - start).total_seconds() / 3600
    
    print(f"\n[4/4] 完成!")
    print(f"  更新：{updated} 只")
    print(f"  失败：{failed} 只")
    print(f"  记录：{rows:,} 条")
    print(f"  耗时：{duration:.1f} 小时")
    
    # 数据库状态
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        latest = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM daily_prices WHERE trade_date='{latest}'")
        count = cursor.fetchone()[0]
    
    print(f"\n数据库:")
    print(f"  最新：{latest} ({count} 只)")
    print("="*70)


if __name__ == "__main__":
    import pandas as pd
    slow_full_update()
