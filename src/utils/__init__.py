"""
工具模块 - 数据库连接和日志
"""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

from config.settings import DATABASE_PATH, LOG_PATH, LOG_LEVEL


# ============== 日志配置 ==============

def setup_logger(name: str, level: str = LOG_LEVEL) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志名称
        level: 日志级别
        
    Returns:
        logging.Logger: 日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件 handler
    log_file = LOG_PATH / f"{name}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


# ============== 数据库连接 ==============

@contextmanager
def get_db_connection(db_path: Path = DATABASE_PATH):
    """
    数据库连接上下文管理器
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    
    Args:
        db_path: 数据库文件路径
        
    Yields:
        sqlite3.Connection: 数据库连接
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 支持字典方式访问
    try:
        yield conn
    finally:
        conn.close()


def init_database(db_path: Path = DATABASE_PATH):
    """
    初始化数据库，创建所有表结构
    
    Args:
        db_path: 数据库文件路径
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. 日线行情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                adj_factor REAL,
                UNIQUE(ts_code, trade_date)
            )
        """)
        
        # 2. 财务数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                report_date TEXT NOT NULL,
                pe REAL,
                pb REAL,
                roe REAL,
                roa REAL,
                revenue REAL,
                profit REAL,
                debt_ratio REAL,
                UNIQUE(ts_code, report_date)
            )
        """)
        
        # 3. 因子值表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factor_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                factor_name TEXT NOT NULL,
                factor_value REAL,
                UNIQUE(ts_code, trade_date, factor_name)
            )
        """)
        
        # 4. 预测结果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                predicted_return REAL,
                model_name TEXT,
                UNIQUE(ts_code, trade_date, model_name)
            )
        """)
        
        # 5. 指数行情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_code TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                turnover REAL,
                UNIQUE(index_code, trade_date)
            )
        """)
        
        # 6. 指数成分股表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_code TEXT NOT NULL,
                ts_code TEXT NOT NULL,
                entry_date TEXT,
                exit_date TEXT,
                UNIQUE(index_code, ts_code, entry_date)
            )
        """)
        
        # 7. 行业分类表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_classification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                industry_name TEXT NOT NULL,
                industry_code TEXT,
                classification_date TEXT,
                UNIQUE(ts_code, classification_date)
            )
        """)
        
        # 8. 股票列表表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL UNIQUE,
                symbol TEXT,
                name TEXT,
                area TEXT,
                industry TEXT,
                list_date TEXT,
                list_status TEXT
            )
        """)
        
        # 创建索引以加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_code_date ON daily_prices(ts_code, trade_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factors_code_date ON factor_values(ts_code, trade_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factors_name ON factor_values(factor_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_financial_code ON financial_data(ts_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_index_code_date ON index_prices(index_code, trade_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_index ON index_components(index_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_stock ON index_components(ts_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_industry_code ON industry_classification(ts_code)")
        
        conn.commit()
    
    logger = setup_logger("database")
    logger.info(f"数据库初始化完成：{db_path}")


# ============== 数据验证工具 ==============

def validate_date_format(date_str: str) -> bool:
    """
    验证日期格式是否为 YYYYMMDD
    
    Args:
        date_str: 日期字符串
        
    Returns:
        bool: 是否有效
    """
    if not isinstance(date_str, str):
        return False
    if len(date_str) != 8:
        return False
    try:
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        if year < 1900 or year > 2100:
            return False
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False
        return True
    except ValueError:
        return False


def format_date(date_str: str) -> str:
    """
    格式化日期为 YYYYMMDD 格式
    
    Args:
        date_str: 日期字符串（支持多种格式）
        
    Returns:
        str: 格式化后的日期
    """
    # 如果已经是 YYYYMMDD 格式，直接返回
    if validate_date_format(date_str):
        return date_str
    
    # 尝试解析其他格式
    from datetime import datetime
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    
    raise ValueError(f"无法解析日期格式：{date_str}")
