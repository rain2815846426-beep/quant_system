"""
消息面/情绪面分析模块

功能：
1. 财经新闻抓取
2. 情绪分析（jieba+ 金融词典）
3. News 因子构建

使用:
    from news import NewsCollector, SentimentAnalyzer, NewsFactor
"""
from .news_collector import NewsCollector
from .sentiment_analyzer import SentimentAnalyzer
from .news_factor import NewsFactor

__all__ = [
    'NewsCollector',
    'SentimentAnalyzer',
    'NewsFactor'
]
