"""
数据抓取模块 - 使用 Akshare 获取 A 股市场数据
"""
from .daily_prices import fetch_all_daily_prices, fetch_single_stock_daily_prices, update_daily_prices
from .index_data import fetch_index_prices, fetch_all_index_prices
from .financial_data import fetch_financial_data, fetch_all_financial_data
from .index_components import fetch_index_components, fetch_all_index_components
from .industry import fetch_industry_classification, fetch_all_industry_classification
from .stock_list import fetch_stock_list

__all__ = [
    "fetch_all_daily_prices",
    "fetch_single_stock_daily_prices",
    "update_daily_prices",
    "fetch_index_prices",
    "fetch_all_index_prices",
    "fetch_financial_data",
    "fetch_all_financial_data",
    "fetch_index_components",
    "fetch_all_index_components",
    "fetch_industry_classification",
    "fetch_all_industry_classification",
    "fetch_stock_list",
]
