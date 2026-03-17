"""
多数据源支持模块

支持的数据源：
1. Akshare（主数据源，免费）
2. Tushare（备用数据源，需要 Token）

功能：
1. 自动切换数据源
2. 失败重试
3. 数据缓存
"""
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import time

from config.config_manager import get_data_sources
from src.utils import setup_logger

logger = setup_logger("data_source")


class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self):
        """初始化"""
        self.config = get_data_sources()
        self.primary_source = self.config.get('primary', 'akshare')
        self.fallback_source = self.config.get('fallback', 'tushare')
        self.tushare_token = self.config.get('tushare_token', '')
        
        # 初始化 Tushare
        if self.tushare_token:
            try:
                import tushare as ts
                ts.set_token(self.tushare_token)
                self.tushare_pro = ts.pro_api()
                logger.info("Tushare 初始化成功")
            except Exception as e:
                logger.warning(f"Tushare 初始化失败：{e}")
                self.tushare_pro = None
        else:
            self.tushare_pro = None
            logger.warning("未配置 Tushare Token，只使用 Akshare")
    
    def fetch_daily_data(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        adjust: str = 'qfq'
    ) -> Optional[pd.DataFrame]:
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型 (qfq/hfq/None)
        
        Returns:
            DataFrame 或 None
        """
        # 尝试主数据源
        try:
            logger.info(f"使用 {self.primary_source} 获取 {ts_code} 数据...")
            df = self._fetch_from_source(
                self.primary_source,
                ts_code,
                start_date,
                end_date,
                adjust
            )
            
            if df is not None and not df.empty:
                logger.info(f"  ✅ 成功获取 {len(df)} 条数据")
                return df
            
        except Exception as e:
            logger.warning(f"{self.primary_source} 失败：{e}")
        
        # 主数据源失败，尝试备用源
        if self.tushare_pro:
            try:
                logger.info(f"使用 {self.fallback_source} 获取 {ts_code} 数据...")
                df = self._fetch_from_source(
                    self.fallback_source,
                    ts_code,
                    start_date,
                    end_date,
                    adjust
                )
                
                if df is not None and not df.empty:
                    logger.info(f"  ✅ 成功获取 {len(df)} 条数据")
                    return df
                    
            except Exception as e:
                logger.error(f"{self.fallback_source} 失败：{e}")
        
        logger.error(f"所有数据源都失败：{ts_code}")
        return None
    
    def _fetch_from_source(
        self,
        source: str,
        ts_code: str,
        start_date: str,
        end_date: str,
        adjust: str
    ) -> Optional[pd.DataFrame]:
        """
        从指定数据源获取数据
        
        Args:
            source: 数据源名称
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
        
        Returns:
            DataFrame 或 None
        """
        symbol = ts_code.split('.')[0]
        
        if source == 'akshare':
            return self._fetch_akshare(symbol, start_date, end_date, adjust)
        elif source == 'tushare':
            return self._fetch_tushare(ts_code, start_date, end_date, adjust)
        else:
            logger.error(f"未知数据源：{source}")
            return None
    
    def _fetch_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str
    ) -> Optional[pd.DataFrame]:
        """从 Akshare 获取数据"""
        import akshare as ak
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adjust=adjust
                )
                
                if df.empty:
                    return None
                
                # 数据清洗
                return self._clean_akshare_data(df)
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.debug(f"Akshare 失败，{wait_time}秒后重试 ({attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise e
        
        return None
    
    def _fetch_tushare(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
        adjust: str
    ) -> Optional[pd.DataFrame]:
        """从 Tushare 获取数据"""
        if not self.tushare_pro:
            return None
        
        try:
            # Tushare 数据获取
            df = self.tushare_pro.daily(
                ts_code=ts_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", "")
            )
            
            if df.empty:
                return None
            
            # 数据清洗
            return self._clean_tushare_data(df)
            
        except Exception as e:
            logger.error(f"Tushare 失败：{e}")
            return None
    
    def _clean_akshare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗 Akshare 数据"""
        column_mapping = {
            "日期": "trade_date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "turnover",
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
        
        final_cols = ["trade_date", "open", "high", "low", "close", "volume", "turnover"]
        final_cols = [col for col in final_cols if col in df.columns]
        
        return df[final_cols]
    
    def _clean_tushare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗 Tushare 数据"""
        # Tushare 字段名
        column_mapping = {
            "trade_date": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "volume",
            "amount": "turnover",
        }
        
        df = df.rename(columns=column_mapping)
        
        final_cols = ["trade_date", "open", "high", "low", "close", "volume", "turnover"]
        final_cols = [col for col in final_cols if col in df.columns]
        
        return df[final_cols]


# 全局数据源管理器
data_source_manager = DataSourceManager()


def get_daily_data(
    ts_code: str,
    start_date: str,
    end_date: str,
    adjust: str = 'qfq'
) -> Optional[pd.DataFrame]:
    """
    获取日线数据（自动切换数据源）
    
    Args:
        ts_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        adjust: 复权类型
    
    Returns:
        DataFrame 或 None
    """
    return data_source_manager.fetch_daily_data(
        ts_code,
        start_date,
        end_date,
        adjust
    )


def set_tushare_token(token: str):
    """
    设置 Tushare Token
    
    Args:
        token: Tushare API Token
    """
    from config.config_manager import set_tushare_token as save_token
    save_token(token)
    
    # 重新初始化数据源管理器
    global data_source_manager
    data_source_manager = DataSourceManager()
    
    print(f"✅ Tushare Token 已设置")
    print(f"   Token: {token[:10]}...{token[-5:]}")


if __name__ == "__main__":
    print("="*70)
    print("多数据源测试")
    print("="*70)
    
    # 测试数据获取
    print("\n测试：获取贵州茅台数据")
    df = get_daily_data(
        ts_code="600519.SH",
        start_date="20260301",
        end_date="20260317"
    )
    
    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 条数据")
        print(df.head())
    else:
        print("❌ 获取失败")
    
    print("\n" + "="*70)
