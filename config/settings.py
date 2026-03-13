"""
系统配置文件
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据库配置
DATABASE_PATH = PROJECT_ROOT / "database" / "quant.db"
DATABASE_PATH.parent.mkdir(exist_ok=True)

# 数据日期配置
DATA_START_DATE = "20100101"  # 历史数据从 2010 年开始

# Akshare 数据源配置
AKSHARE_STOCK_LIST = "A 股"  # A 股市场

# 指数代码配置
INDEX_CODES = {
    "HS300": "000300",      # 沪深 300
    "CSI500": "000905",     # 中证 500
    "CSI1000": "000852",    # 中证 1000
}

# 数据更新配置
UPDATE_TIME = "18:00"  # 每日收盘后更新时间

# 日志配置
LOG_LEVEL = "INFO"
LOG_PATH = PROJECT_ROOT / "logs"
LOG_PATH.mkdir(exist_ok=True)

# 模型配置
ML_CONFIG = {
    "predict_days": 20,       # 预测未来 20 日收益
    "train_window_years": 3,  # 使用过去 3 年数据训练
    "top_n_stocks": 20,       # 选股数量 Top 20
}

# 回测配置
BACKTEST_CONFIG = {
    "commission": 0.001,      # 手续费 0.1%
    "slippage": 0.0005,       # 滑点 0.05%
    "rebalance_freq": "M",    # 月度调仓
    "position_weight": 0.05,  # 等权 5%
}
