#!/usr/bin/env python3
"""
消息面/情绪面数据更新脚本

功能：
1. 抓取最新新闻
2. 计算情绪因子
3. 保存到数据库

使用:
    python3 scripts/update_news_factors.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from news import NewsCollector, SentimentAnalyzer, NewsFactor
from config.settings import DATABASE_PATH


def main():
    print("="*70)
    print("消息面/情绪面数据更新")
    print("="*70)
    
    # 1. 抓取新闻
    print("\n[1/3] 抓取新闻...")
    collector = NewsCollector()
    news_df = collector.fetch_all_news(page_size=50)
    
    if news_df.empty:
        print("  ❌ 未获取到新闻")
        return
    
    print(f"  ✅ 获取 {len(news_df)} 条新闻")
    
    # 2. 计算情绪因子
    print("\n[2/3] 计算情绪因子...")
    factor = NewsFactor()
    factors = factor.fetch_and_calculate_factors()
    
    if not factors:
        print("  ❌ 因子计算失败")
        return
    
    # 3. 保存
    print("\n[3/3] 保存因子...")
    factor.save_factors_to_db(factors)
    
    print("\n" + "="*70)
    print("更新完成！")
    print("="*70)
    
    # 显示摘要
    print("\n今日情绪摘要:")
    print(f"  情绪指数：{factors.get('market_sentiment_index', 0):.2f}")
    print(f"  正面比例：{factors.get('market_positive_ratio', 0)*100:.1f}%")
    print(f"  sentiment_factor: {factors.get('sentiment_factor', 0):.4f}")
    print(f"  news_count_factor: {factors.get('news_count_factor', 0):.4f}")
    print(f"  event_score: {factors.get('event_score', 0):.4f}")


if __name__ == "__main__":
    main()
