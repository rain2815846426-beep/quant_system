"""
News 因子构建模块

构建的因子：
1. sentiment_factor - 情绪得分因子
2. news_count_factor - 新闻数量因子
3. event_score - 事件得分
4. topic_score - 主题热度因子
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection
from news.news_collector import NewsCollector
from news.sentiment_analyzer import SentimentAnalyzer


class NewsFactor:
    """
    News 因子构建器
    
    因子列表：
    1. sentiment_factor - 情绪得分（-1 到 1）
    2. news_count_factor - 新闻数量（对数）
    3. event_score - 重大事件得分
    4. topic_score - 主题热度
    """
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """
        初始化
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.collector = NewsCollector()
        self.analyzer = SentimentAnalyzer()
        
        # 重大事件关键词
        self.event_keywords = {
            '业绩预告': ['业绩', '预告', '预增', '预亏', '预警'],
            '重大合同': ['中标', '签约', '大单', '合同'],
            '并购重组': ['并购', '重组', '收购', '合并'],
            '股份回购': ['回购', '增持', '减持'],
            '政策发布': ['政策', '发布', '规定', '通知'],
        }
    
    def calculate_sentiment_factor(
        self,
        news_df: pd.DataFrame,
        date: str
    ) -> float:
        """
        计算情绪因子
        
        Args:
            news_df: 新闻 DataFrame
            date: 交易日期
            
        Returns:
            情绪因子值（-1 到 1）
        """
        if news_df.empty:
            return 0.0
        
        # 分析情绪
        texts = (news_df['title'].fillna('') + ' ' + news_df['content'].fillna('')).tolist()
        results = self.analyzer.analyze_batch(texts)
        
        # 平均情绪得分
        sentiment_factor = results['sentiment_score'].mean()
        
        return sentiment_factor
    
    def calculate_news_count_factor(
        self,
        news_df: pd.DataFrame,
        date: str
    ) -> float:
        """
        计算新闻数量因子
        
        Args:
            news_df: 新闻 DataFrame
            date: 交易日期
            
        Returns:
            新闻数量因子（对数标准化）
        """
        if news_df.empty:
            return 0.0
        
        # 新闻数量（对数）
        news_count = len(news_df)
        news_count_factor = np.log1p(news_count)
        
        # 标准化到 0-1
        news_count_factor = min(news_count_factor / 5.0, 1.0)
        
        return news_count_factor
    
    def calculate_event_score(
        self,
        news_df: pd.DataFrame,
        date: str
    ) -> float:
        """
        计算事件得分
        
        Args:
            news_df: 新闻 DataFrame
            date: 交易日期
            
        Returns:
            事件得分（0 到 1）
        """
        if news_df.empty:
            return 0.0
        
        event_score = 0.0
        
        # 检查每篇新闻
        for _, row in news_df.iterrows():
            text = str(row.get('title', '')) + ' ' + str(row.get('content', ''))
            
            # 检查事件类型
            for event_type, keywords in self.event_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        # 不同事件权重不同
                        if event_type in ['业绩预告', '重大合同']:
                            event_score += 0.3
                        elif event_type in ['并购重组', '政策发布']:
                            event_score += 0.2
                        else:
                            event_score += 0.1
                        break
        
        # 标准化到 0-1
        event_score = min(event_score / 3.0, 1.0)
        
        return event_score
    
    def calculate_topic_score(
        self,
        news_df: pd.DataFrame,
        date: str,
        target_topics: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        计算主题热度因子
        
        Args:
            news_df: 新闻 DataFrame
            date: 交易日期
            target_topics: 目标主题列表
            
        Returns:
            主题得得分字典
        """
        if news_df.empty:
            return {}
        
        topic_scores = {}
        
        # 默认关注主题
        if target_topics is None:
            target_topics = ['人工智能', '新能源', '半导体', '医药', '消费']
        
        # 统计每个主题的新闻数量
        for topic in target_topics:
            count = 0
            
            for _, row in news_df.iterrows():
                text = str(row.get('title', '')) + ' ' + str(row.get('content', ''))
                
                if topic in text:
                    count += 1
            
            # 主题热度（对数标准化）
            topic_scores[topic] = np.log1p(count) / 3.0
        
        return topic_scores
    
    def fetch_and_calculate_factors(
        self,
        date: Optional[str] = None
    ) -> Dict:
        """
        获取新闻并计算所有因子
        
        Args:
            date: 交易日期（默认今天）
            
        Returns:
            因子字典
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"计算 {date} 的 News 因子...")
        
        # 抓取新闻
        news_df = self.collector.fetch_all_news(page_size=50)
        
        if news_df.empty:
            print("  无新闻数据")
            return {}
        
        # 计算因子
        factors = {
            'date': date,
            'sentiment_factor': self.calculate_sentiment_factor(news_df, date),
            'news_count_factor': self.calculate_news_count_factor(news_df, date),
            'event_score': self.calculate_event_score(news_df, date),
        }
        
        # 主题得分
        topic_scores = self.calculate_topic_score(news_df, date)
        factors.update(topic_scores)
        
        # 市场情绪指标
        market_sentiment = self.analyzer.calculate_market_sentiment(news_df)
        factors['market_sentiment_index'] = market_sentiment['sentiment_index']
        factors['market_positive_ratio'] = market_sentiment['positive_ratio']
        
        print(f"  sentiment_factor: {factors['sentiment_factor']:.4f}")
        print(f"  news_count_factor: {factors['news_count_factor']:.4f}")
        print(f"  event_score: {factors['event_score']:.4f}")
        print(f"  market_sentiment_index: {factors['market_sentiment_index']:.2f}")
        
        return factors
    
    def save_factors_to_db(
        self,
        factors: Dict
    ):
        """
        保存因子到数据库
        
        Args:
            factors: 因子字典
        """
        if not factors:
            return
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_factors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_date TEXT NOT NULL UNIQUE,
                    sentiment_factor REAL,
                    news_count_factor REAL,
                    event_score REAL,
                    market_sentiment_index REAL,
                    market_positive_ratio REAL,
                    topic_ai REAL,
                    topic_new_energy REAL,
                    topic_semiconductor REAL
                )
            """)
            
            # 插入数据
            cursor.execute("""
                INSERT OR REPLACE INTO news_factors 
                (trade_date, sentiment_factor, news_count_factor, event_score,
                 market_sentiment_index, market_positive_ratio,
                 topic_ai, topic_new_energy, topic_semiconductor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                factors['date'],
                factors.get('sentiment_factor', 0),
                factors.get('news_count_factor', 0),
                factors.get('event_score', 0),
                factors.get('market_sentiment_index', 0),
                factors.get('market_positive_ratio', 0),
                factors.get('人工智能', 0),
                factors.get('新能源', 0),
                factors.get('半导体', 0),
            ))
            
            conn.commit()
        
        print(f"因子已保存到数据库")


def test_news_factor():
    """测试 News 因子"""
    print("="*70)
    print("News 因子测试")
    print("="*70)
    
    factor = NewsFactor()
    
    # 计算因子
    factors = factor.fetch_and_calculate_factors()
    
    if factors:
        print("\n因子计算结果:")
        for key, value in factors.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
        
        # 保存到数据库
        factor.save_factors_to_db(factors)
    else:
        print("\n因子计算失败")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == "__main__":
    test_news_factor()
