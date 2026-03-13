#!/usr/bin/env python3
"""
数据下载快速启动脚本（带进度显示）

使用方法:
    # 下载全部历史数据（从 2010 年至今）
    python scripts/download_data.py
    
    # 下载指定日期范围的数据
    python scripts/download_data.py --start_date 20200101 --end_date 20231231
    
    # 更新数据（只获取新增数据）
    python scripts/download_data.py --action update
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetch.download_all import main

if __name__ == "__main__":
    main()
