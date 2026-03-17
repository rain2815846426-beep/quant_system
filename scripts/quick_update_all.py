#!/usr/bin/env python3
"""
一键更新所有数据

功能：
1. 更新日线数据（分批更新，自动处理）
2. 计算因子
3. 更新情绪数据

使用方法:
    python3 scripts/quick_update_all.py
    
    # 快速模式（只更新成分股）
    python3 scripts/quick_update_all.py --fast
    
    # 完整模式（更新全部股票）
    python3 scripts/quick_update_all.py --full
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def check_latest_date() -> str:
    """检查数据库最新日期"""
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        result = cursor.fetchone()[0]
        return result if result else "未知"


def update_daily_data(batch_size: int = 100, delay: int = 2):
    """
    更新日线数据（分批）
    
    Args:
        batch_size: 每批股票数量
        delay: 股票间延迟（秒）
    """
    print("\n" + "="*70)
    print("步骤 1/3: 更新日线数据")
    print("="*70)
    
    # 获取股票总数
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM stock_list")
        total_stocks = cursor.fetchone()[0]
    
    total_batches = (total_stocks + batch_size - 1) // batch_size
    
    print(f"股票总数：{total_stocks}")
    print(f"批次大小：{batch_size}")
    print(f"总批次：{total_batches}")
    print(f"预计时间：{total_batches * batch_size * delay / 60:.0f} 分钟")
    
    # 运行分批更新
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "update_batch.py"),
        "--all",
        "--size", str(batch_size),
        "--delay", str(delay),
        "--batch-delay", "30"
    ]
    
    subprocess.run(cmd)


def calculate_factors():
    """计算因子"""
    print("\n" + "="*70)
    print("步骤 2/3: 计算因子")
    print("="*70)
    
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "calculate_factors.py")
    ]
    
    subprocess.run(cmd)


def update_news():
    """更新情绪数据"""
    print("\n" + "="*70)
    print("步骤 3/3: 更新情绪数据")
    print("="*70)
    
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "update_news_factors.py")
    ]
    
    subprocess.run(cmd)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="一键更新所有数据")
    parser.add_argument('--fast', action='store_true', help='快速模式（只更新成分股）')
    parser.add_argument('--full', action='store_true', help='完整模式（更新全部股票）')
    parser.add_argument('--batch-size', type=int, default=100, help='每批股票数量')
    parser.add_argument('--delay', type=int, default=2, help='股票间延迟（秒）')
    
    args = parser.parse_args()
    
    print("="*70)
    print("一键更新所有数据")
    print("="*70)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查当前状态
    latest = check_latest_date()
    print(f"\n数据库最新日期：{latest}")
    
    # 选择模式
    if args.fast:
        print("\n模式：快速模式（只更新成分股）")
        batch_size = 50
        delay = 2
    elif args.full:
        print("\n模式：完整模式（更新全部股票）")
        batch_size = args.batch_size
        delay = args.delay
    else:
        print("\n模式：默认模式（更新前 500 只）")
        batch_size = 100
        delay = 2
    
    # 询问确认
    print(f"\n配置:")
    print(f"  每批数量：{batch_size}")
    print(f"  延迟：{delay}秒")
    
    confirm = input("\n开始更新？(y/n): ")
    
    if confirm.lower() != 'y':
        print("已取消")
        return
    
    # 执行更新
    update_daily_data(batch_size, delay)
    calculate_factors()
    update_news()
    
    # 显示最终状态
    print("\n" + "="*70)
    print("更新完成！")
    print("="*70)
    
    latest = check_latest_date()
    print(f"数据库最新日期：{latest}")
    print(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
