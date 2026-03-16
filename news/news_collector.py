"""
新闻抓取模块

数据源：
1. 东方财富网
2. 新浪财经

功能：
1. 获取最新财经新闻
2. 获取个股相关新闻
3. 数据清洗
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import time


class NewsCollector:
    """
    新闻抓取器
    
    支持：
    - 东方财富网
    - 新浪财经
    """
    
    def __init__(self):
        """初始化"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 东方财富 API
        self.eastmoney_api = "http://api.eastmoney.com/v1/news/list"
        
        # 新浪财经 API
        self.sina_api = "https://feed.mix.sina.com.cn/api/roll/get"
    
    def fetch_eastmoney_news(
        self,
        page_size: int = 50,
        keyword: Optional[str] = None
    ) -> List[Dict]:
        """
        抓取东方财富新闻
        
        Args:
            page_size: 新闻数量
            keyword: 关键词（可选）
            
        Returns:
            新闻列表
        """
        news_list = []
        
        try:
            # 东方财富新闻 API
            params = {
                'page': 1,
                'page_size': page_size,
                'type': 'bg',  # 报告类型
            }
            
            response = requests.get(
                self.eastmoney_api,
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data:
                    for item in data['data']:
                        news = {
                            'title': item.get('Title', ''),
                            'content': item.get('Content', ''),
                            'source': '东方财富',
                            'publish_time': item.get('ShowTime', ''),
                            'url': item.get('Url', ''),
                        }
                        news_list.append(news)
                        
        except Exception as e:
            print(f"东方财富抓取失败：{e}")
        
        return news_list
    
    def fetch_sina_news(
        self,
        page_size: int = 50,
        keyword: Optional[str] = None
    ) -> List[Dict]:
        """
        抓取新浪财经新闻
        
        Args:
            page_size: 新闻数量
            keyword: 关键词（可选）
            
        Returns:
            新闻列表
        """
        news_list = []
        
        try:
            # 新浪财经 API
            params = {
                'page': 1,
                'pagelen': page_size,
                'cid': '766',  # 财经频道
            }
            
            response = requests.get(
                self.sina_api,
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'result' in data and 'data' in data['result']:
                    for item in data['result']['data']:
                        news = {
                            'title': item.get('title', ''),
                            'content': item.get('description', ''),
                            'source': '新浪财经',
                            'publish_time': item.get('ctime', ''),
                            'url': item.get('url', ''),
                        }
                        news_list.append(news)
                        
        except Exception as e:
            print(f"新浪财经抓取失败：{e}")
        
        return news_list
    
    def fetch_stock_news(
        self,
        stock_code: str,
        source: str = 'eastmoney'
    ) -> List[Dict]:
        """
        抓取个股相关新闻
        
        Args:
            stock_code: 股票代码（如 000001）
            source: 数据源
            
        Returns:
            新闻列表
        """
        news_list = []
        
        try:
            if source == 'eastmoney':
                # 东方财富个股新闻
                url = f"http://search-api-web.eastmoney.com/search/jsonp"
                params = {
                    'keyword': stock_code,
                    'type': 'news',
                    'page': 1,
                    'pagesize': 20,
                }
                
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'Result' in data:
                        for item in data['Result']:
                            news = {
                                'title': item.get('Title', ''),
                                'content': item.get('Content', ''),
                                'source': '东方财富',
                                'publish_time': item.get('ShowTime', ''),
                                'url': item.get('Url', ''),
                                'stock_code': stock_code,
                            }
                            news_list.append(news)
                            
        except Exception as e:
            print(f"个股新闻抓取失败：{e}")
        
        return news_list
    
    def fetch_all_news(
        self,
        page_size: int = 50
    ) -> pd.DataFrame:
        """
        抓取所有新闻（合并多个数据源）
        
        Args:
            page_size: 每个数据源的新闻数量
            
        Returns:
            DataFrame 格式的新闻数据
        """
        print("抓取新闻...")
        
        # 抓取东方财富
        print("  东方财富...")
        eastmoney_news = self.fetch_eastmoney_news(page_size)
        print(f"    获取 {len(eastmoney_news)} 条")
        
        # 抓取新浪财经
        print("  新浪财经...")
        sina_news = self.fetch_sina_news(page_size)
        print(f"    获取 {len(sina_news)} 条")
        
        # 合并
        all_news = eastmoney_news + sina_news
        
        # 去重（按标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            if news['title'] not in seen_titles:
                seen_titles.add(news['title'])
                unique_news.append(news)
        
        # 转换为 DataFrame
        df = pd.DataFrame(unique_news)
        
        if not df.empty:
            # 时间格式化
            df['publish_time'] = pd.to_datetime(df['publish_time'], errors='coerce')
            df = df.sort_values('publish_time', ascending=False)
        
        print(f"总计：{len(df)} 条新闻")
        
        return df
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 去除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 去除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 去除多余空格
        text = ' '.join(text.split())
        
        return text


def test_news_collector():
    """测试新闻抓取"""
    print("="*70)
    print("新闻抓取测试")
    print("="*70)
    
    collector = NewsCollector()
    
    # 抓取最新新闻
    df = collector.fetch_all_news(page_size=20)
    
    if not df.empty:
        print(f"\n获取到 {len(df)} 条新闻")
        print("\n最新 10 条:")
        print(df[['title', 'source', 'publish_time']].head(10).to_string())
        
        # 保存
        df.to_csv('news/latest_news.csv', index=False, encoding='utf-8-sig')
        print("\n已保存到：news/latest_news.csv")
    else:
        print("\n未获取到新闻")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == "__main__":
    test_news_collector()
