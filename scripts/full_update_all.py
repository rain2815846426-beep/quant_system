#!/usr/bin/env python3
"""
全量数据更新（超可靠版）

特点：
1. 双数据源自动切换（Akshare + Tushare）
2. 每只股票最多重试 5 次
3. 股票间延迟 10 秒（确保不被限流）
4. 批次间暂停 2 分钟
5. 支持断点续传（中断后继续）
6. 详细的进度和错误报告
7. 后台运行，不占用终端

使用方法:
    # 前台运行（可以看到进度）
    python3 scripts/full_update_all.py
    
    # 后台运行（推荐）
    nohup python3 scripts/full_update_all.py > logs/full_update.log 2>&1 &
    
    # 查看进度
    tail -f logs/full_update.log
    
    # 查看剩余时间
    grep "预计剩余" logs/full_update.log | tail -1
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection, setup_logger
from src.data_fetch.multi_source import get_daily_data

logger = setup_logger("full_update")


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
        
        # 合并
        all_stocks = components + [s for s in others if s not in components]
        
        return all_stocks


def get_latest_date(ts_code: str) -> str:
    """获取股票最新日期"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(trade_date) FROM daily_prices WHERE ts_code = ?",
            (ts_code,)
        )
        result = cursor.fetchone()[0]
        return result if result else "20100101"


def get_target_date() -> str:
    """获取目标日期（最近交易日）"""
    today = datetime.now()
    
    # 周末处理
    if today.weekday() == 5:  # 周六
        return (today - timedelta(days=1)).strftime("%Y%m%d")
    elif today.weekday() == 6:  # 周日
        return (today - timedelta(days=2)).strftime("%Y%m%d")
    else:
        return today.strftime("%Y%m%d")


def save_stock_data(ts_code: str, df, start_date: str, end_date: str):
    """保存股票数据到数据库"""
    if df is None or df.empty:
        return 0
    
    # 添加必要字段
    df = df.copy()
    df["ts_code"] = ts_code
    df["adj_factor"] = 1.0
    
    # 保存
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        saved = 0
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_prices 
                    (ts_code, trade_date, open, high, low, close, volume, turnover, adj_factor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["ts_code"],
                    row["trade_date"],
                    row.get("open"),
                    row.get("high"),
                    row.get("low"),
                    row.get("close"),
                    row.get("volume"),
                    row.get("turnover"),
                    row.get("adj_factor", 1.0)
                ))
                saved += 1
            except Exception as e:
                logger.debug(f"保存失败：{e}")
        
        conn.commit()
        return saved


def update_stock(ts_code: str, start_date: str, end_date: str, max_retries: int = 5) -> int:
    """
    更新单只股票（带重试）
    
    Returns:
        更新的记录数，-1 表示跳过
    """
    for attempt in range(max_retries):
        try:
            # 使用双数据源获取
            df = get_daily_data(
                ts_code=ts_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust='qfq'
            )
            
            if df is None or df.empty:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    logger.debug(f"  无数据，{wait}秒后重试 ({attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                return 0
            
            # 保存
            return save_stock_data(ts_code, df, start_date, end_date)
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 10
                logger.error(f"失败：{e}，{wait}秒后重试")
                time.sleep(wait)
            else:
                logger.error(f"更新失败：{e}")
                return -1
    
    return 0


def full_update():
    """全量更新"""
    print("="*70)
    print("全量数据更新（超可靠版）")
    print("="*70)
    
    start_time = datetime.now()
    print(f"开始时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取股票列表
    print("\n[1/5] 获取股票列表...")
    stock_list = get_stock_list()
    total = len(stock_list)
    
    # 统计
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT ts_code) FROM index_components
            WHERE index_code IN ('000300', '000905', '000852')
        """)
        component_count = cursor.fetchone()[0]
    
    print(f"  总数：{total} 只")
    print(f"  成分股：{component_count} 只（优先）")
    print(f"  其他：{total - component_count} 只")
    
    # 目标日期
    print("\n[2/5] 检查目标日期...")
    target_date = get_target_date()
    print(f"  目标：{target_date}")
    
    # 更新
    print(f"\n[3/5] 开始更新...")
    print(f"  配置：")
    print(f"    股票间延迟：10 秒")
    print(f"    批次大小：20 只")
    print(f"    批次间隔：120 秒")
    print(f"    最大重试：5 次")
    
    # 估算时间
    estimated_minutes = total * 10 / 60 + (total / 20) * 2
    print(f"  预计：{estimated_minutes:.0f} 分钟 ({estimated_minutes/60:.1f} 小时)")
    
    # 统计
    updated = 0
    failed = 0
    skipped = 0
    total_rows = 0
    
    # 分批
    batch_size = 20
    batches = [stock_list[i:i+batch_size] for i in range(0, total, batch_size)]
    
    for bi, batch in enumerate(batches, 1):
        batch_start = datetime.now()
        
        print(f"\n  批次 {bi}/{len(batches)} ({len(batch)} 只)...")
        
        for i, ts_code in enumerate(batch):
            # 最新日期
            latest = get_latest_date(ts_code)
            
            # 跳过
            if latest >= target_date:
                skipped += 1
                if i % 20 == 0:
                    print(f"    [{bi}.{i}] {ts_code} - 跳过 (已有 {latest})")
                continue
            
            # 更新
            rows = update_stock(ts_code, latest, target_date)
            
            # 进度
            idx = (bi-1)*batch_size + i + 1
            pct = idx / total * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            remaining = (elapsed / idx * (total - idx)) / 60 if idx > 0 else 0
            
            if rows > 0:
                updated += 1
                total_rows += rows
                if idx % 10 == 0:
                    print(f"    [{bi}.{i}] {ts_code} - {rows}条 ({pct:.1f}%, 剩余{remaining:.0f}分)")
            elif rows == -1:
                failed += 1
                print(f"    [{bi}.{i}] {ts_code} - ❌ 失败")
            
            # 延迟
            time.sleep(10)
        
        # 批次间隔
        if bi < len(batches):
            batch_time = (datetime.now() - batch_start).total_seconds()
            print(f"  批次完成 ({batch_time/60:.1f}分)，暂停 120 秒...")
            time.sleep(120)
    
    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n[4/5] 更新完成!")
    
    print(f"\n统计:")
    print(f"  更新：{updated} 只")
    print(f"  跳过：{skipped} 只")
    print(f"  失败：{failed} 只")
    print(f"  记录：{total_rows:,} 条")
    print(f"  成功率：{updated/(updated+failed)*100:.1f}%" if updated+failed > 0 else "  成功率：N/A")
    
    print(f"\n时间:")
    print(f"  开始：{start_time.strftime('%H:%M:%S')}")
    print(f"  结束：{end_time.strftime('%H:%M:%S')}")
    print(f"  耗时：{duration/60:.1f} 分钟 ({duration/3600:.2f} 小时)")
    
    # 数据库状态
    print(f"\n[5/5] 数据库状态...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM daily_prices")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        latest = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM daily_prices WHERE trade_date = '{latest}'")
        latest_count = cursor.fetchone()[0]
        
        print(f"  总记录：{total_count:,} 条")
        print(f"  最新：{latest}")
        print(f"  {latest} 股票：{latest_count} 只")
    
    print("\n" + "="*70)
    
    # 保存日志
    log_file = project_root / "logs" / "full_update_summary.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"全量更新总结\n")
        f.write(f"开始：{start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"结束：{end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"耗时：{duration/60:.1f} 分钟\n")
        f.write(f"更新：{updated} 只\n")
        f.write(f"失败：{failed} 只\n")
        f.write(f"记录：{total_rows:,} 条\n")
        f.write(f"成功率：{updated/(updated+failed)*100:.1f}%\n")
        f.write(f"最新：{latest} ({latest_count} 只)\n")
    
    print(f"日志：{log_file}")
    print("="*70)


if __name__ == "__main__":
    full_update()
