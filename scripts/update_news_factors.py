#!/usr/bin/env python3
"""
消息面/情绪面数据更新脚本（增强版）

功能：
1. 抓取最新新闻（东方财富 + 新浪 + 财联社）
2. 情绪分析（jieba+ 词典 + BERT 可选）
3. 事件检测（业绩/合同/并购等）
4. 计算 News 因子
5. 保存到数据库

使用:
    python3 scripts/update_news_factors.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from news import NewsCollector, SentimentAnalyzer, NewsFactor
from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def check_and_init_table():
    """检查并初始化数据库表"""
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # 创建 News 因子表
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
                topic_semiconductor REAL,
                topic_medical REAL,
                topic_finance REAL,
                topic_consumer REAL,
                news_count INTEGER,
                positive_count INTEGER,
                negative_count INTEGER,
                created_at TEXT
            )
        """)
        
        # 创建新闻明细表（只保留最近 7 天）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                source TEXT,
                publish_time TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                topics TEXT,
                event_type TEXT,
                created_at TEXT
            )
        """)
        
        conn.commit()


def cleanup_old_news(days: int = 7):
    """清理旧新闻数据"""
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # 删除 7 天前的新闻明细
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute(f"DELETE FROM news_details WHERE publish_time < '{cutoff_date}'")
        
        conn.commit()
        
        deleted = cursor.rowcount
        if deleted > 0:
            print(f"  清理了 {deleted} 条旧新闻")


def main():
    print("="*70)
    print("消息面/情绪面数据更新（增强版）")
    print("="*70)
    
    # 初始化表
    print("\n[0/5] 初始化数据库...")
    check_and_init_table()
    print("  ✅ 完成")
    
    # 1. 抓取新闻
    print("\n[1/5] 抓取新闻...")
    collector = NewsCollector()
    news_df = collector.fetch_all_news(page_size=50)
    
    if news_df.empty:
        print("  ❌ 未获取到新闻")
        return
    
    print(f"  ✅ 获取 {len(news_df)} 条新闻")
    
    # 清理旧数据
    cleanup_old_news(days=7)
    
    # 2. 情绪分析
    print("\n[2/5] 情绪分析...")
    analyzer = SentimentAnalyzer()
    
    # 批量分析
    texts = (news_df['title'].fillna('') + ' ' + news_df['content'].fillna('')).tolist()
    sentiment_results = analyzer.analyze_batch(texts)
    
    # 主题识别
    topics_list = []
    for text in texts:
        topics = analyzer.identify_topics(text)
        topics_list.append(','.join(topics))
    
    news_df['sentiment_score'] = sentiment_results['sentiment_score']
    news_df['sentiment_label'] = sentiment_results['sentiment_label']
    news_df['topics'] = topics_list
    
    positive_count = (sentiment_results['sentiment_label'] == 'positive').sum()
    negative_count = (sentiment_results['sentiment_label'] == 'negative').sum()
    
    print(f"  正面：{positive_count} 条 ({positive_count/len(news_df)*100:.1f}%)")
    print(f"  负面：{negative_count} 条 ({negative_count/len(news_df)*100:.1f}%)")
    print(f"  中性：{len(news_df)-positive_count-negative_count} 条")
    
    # 3. 事件检测
    print("\n[3/5] 事件检测...")
    factor = NewsFactor()
    
    event_types = []
    for _, row in news_df.iterrows():
        text = str(row.get('title', '')) + ' ' + str(row.get('content', ''))
        
        detected_events = []
        for event_type, keywords in factor.event_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    detected_events.append(event_type)
                    break
        
        event_types.append(','.join(detected_events))
    
    news_df['event_type'] = event_types
    event_count = (news_df['event_type'] != '').sum()
    print(f"  检测到 {event_count} 条重大事件")
    
    # 4. 计算因子
    print("\n[4/5] 计算 News 因子...")
    today = datetime.now().strftime('%Y-%m-%d')
    
    factors = {
        'date': today,
        'sentiment_factor': sentiment_results['sentiment_score'].mean(),
        'news_count_factor': min(len(news_df) / 50.0, 1.0),
        'event_score': min(event_count / 10.0, 1.0),
        'market_sentiment_index': 50 + sentiment_results['sentiment_score'].mean() * 50,
        'market_positive_ratio': positive_count / len(news_df),
        'news_count': len(news_df),
        'positive_count': positive_count,
        'negative_count': negative_count,
    }
    
    # 主题得分
    topic_scores = factor.calculate_topic_score(news_df)
    factors.update(topic_scores)
    
    print(f"  sentiment_factor: {factors['sentiment_factor']:.4f}")
    print(f"  news_count_factor: {factors['news_count_factor']:.4f}")
    print(f"  event_score: {factors['event_score']:.4f}")
    print(f"  market_sentiment_index: {factors['market_sentiment_index']:.2f}")
    
    # 5. 保存
    print("\n[5/5] 保存数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        
        # 保存 News 因子
        cursor.execute("""
            INSERT OR REPLACE INTO news_factors 
            (trade_date, sentiment_factor, news_count_factor, event_score,
             market_sentiment_index, market_positive_ratio,
             topic_ai, topic_new_energy, topic_semiconductor,
             topic_medical, topic_finance, topic_consumer,
             news_count, positive_count, negative_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            factors.get('医药', 0),
            factors.get('金融', 0),
            factors.get('消费', 0),
            factors.get('news_count', 0),
            factors.get('positive_count', 0),
            factors.get('negative_count', 0),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # 保存新闻明细
        for _, row in news_df.iterrows():
            cursor.execute("""
                INSERT INTO news_details 
                (title, content, source, publish_time, sentiment_score, 
                 sentiment_label, topics, event_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('title', ''),
                row.get('content', ''),
                row.get('source', ''),
                row.get('publish_time', ''),
                row.get('sentiment_score', 0),
                row.get('sentiment_label', 'neutral'),
                row.get('topics', ''),
                row.get('event_type', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        
        conn.commit()
    
    print(f"  ✅ 已保存")
    
    # 显示摘要
    print("\n" + "="*70)
    print("更新完成！")
    print("="*70)
    
    print("\n📊 今日情绪摘要:")
    print(f"  情绪指数：{factors['market_sentiment_index']:.1f} " + 
          ("🟢 正面" if factors['market_sentiment_index'] > 50 else "🔴 负面"))
    print(f"  新闻数量：{factors['news_count']} 条")
    print(f"  正面比例：{factors['market_positive_ratio']*100:.1f}%")
    print(f"  重大事件：{event_count} 条")
    
    # 热门主题
    topics = ['人工智能', '新能源', '半导体', '医药', '金融', '消费']
    print("\n🔥 主题热度:")
    for topic in topics:
        score = factors.get(topic, 0)
        if score > 0:
            print(f"  {topic}: {score:.4f}")


if __name__ == "__main__":
    main()
