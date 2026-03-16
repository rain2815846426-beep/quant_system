"""
情绪分析模块

使用 jieba 分词 + 金融情感词典
输出：
- 情绪得分（-1 到 1）
- 情绪分类（正面/负面/中性）
- 情绪强度
"""
import jieba
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from news.financial_sentiment_dict import (
    POSITIVE_WORDS,
    NEGATIVE_WORDS,
    DEGREE_WORDS,
    NEGATION_WORDS,
    INDUSTRY_TOPICS
)


class SentimentAnalyzer:
    """
    情绪分析器
    
    方法：
    1. 词典匹配（快速）
    2. 考虑程度副词和否定词
    3. 输出情绪得分和分类
    """
    
    def __init__(self):
        """初始化"""
        # 加载词典
        self.positive_words = set(POSITIVE_WORDS)
        self.negative_words = set(NEGATIVE_WORDS)
        self.degree_words = DEGREE_WORDS
        self.negation_words = set(NEGATION_WORDS)
        self.industry_topics = INDUSTRY_TOPICS
        
        # 加载 jieba 词典
        self._load_jieba_dict()
    
    def _load_jieba_dict(self):
        """加载自定义词典"""
        # 添加金融词汇到 jieba
        for word in self.positive_words:
            jieba.add_word(word)
        
        for word in self.negative_words:
            jieba.add_word(word)
        
        for word in self.negation_words:
            jieba.add_word(word)
        
        for word in self.degree_words.keys():
            jieba.add_word(word)
        
        # 添加行业词汇
        for topic, words in self.industry_topics.items():
            for word in words:
                jieba.add_word(word)
    
    def analyze_sentiment(
        self,
        text: str
    ) -> Dict:
        """
        分析文本情绪
        
        Args:
            text: 输入文本
            
        Returns:
            情绪分析结果字典
        """
        if not text:
            return {
                'sentiment_score': 0,
                'sentiment_label': 'neutral',
                'positive_count': 0,
                'negative_count': 0,
                'intensity': 0
            }
        
        # 分词
        words = list(jieba.cut(text))
        
        # 统计情绪词
        positive_count = 0
        negative_count = 0
        intensity_sum = 0
        
        # 遍历分词
        for i, word in enumerate(words):
            # 检查程度副词
            degree = 1.0
            if i > 0 and words[i-1] in self.degree_words:
                degree = self.degree_words[words[i-1]]
            
            # 检查否定词
            negation = 1.0
            if i > 0 and words[i-1] in self.negation_words:
                negation = -1.0
            
            # 正面词
            if word in self.positive_words:
                score = degree * negation
                positive_count += score
                intensity_sum += abs(score)
            
            # 负面词
            elif word in self.negative_words:
                score = degree * negation
                negative_count += score
                intensity_sum += abs(score)
        
        # 计算情绪得分（-1 到 1）
        total_count = positive_count + negative_count
        
        if total_count == 0:
            sentiment_score = 0
            sentiment_label = 'neutral'
        else:
            sentiment_score = (positive_count - negative_count) / (total_count + 1)
            
            if sentiment_score > 0.1:
                sentiment_label = 'positive'
            elif sentiment_score < -0.1:
                sentiment_label = 'negative'
            else:
                sentiment_label = 'neutral'
        
        # 情绪强度（0 到 1）
        intensity = min(intensity_sum / 10, 1.0)
        
        return {
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'intensity': intensity,
            'word_count': len(words)
        }
    
    def analyze_batch(
        self,
        texts: List[str]
    ) -> pd.DataFrame:
        """
        批量分析情绪
        
        Args:
            texts: 文本列表
            
        Returns:
            DataFrame 格式的结果
        """
        results = []
        
        for i, text in enumerate(texts):
            result = self.analyze_sentiment(text)
            result['index'] = i
            results.append(result)
        
        df = pd.DataFrame(results)
        
        return df
    
    def identify_topics(
        self,
        text: str
    ) -> List[str]:
        """
        识别文本主题（行业）
        
        Args:
            text: 输入文本
            
        Returns:
            识别到的主题列表
        """
        topics = []
        
        for topic, keywords in self.industry_topics.items():
            for keyword in keywords:
                if keyword in text:
                    if topic not in topics:
                        topics.append(topic)
                    break
        
        return topics
    
    def calculate_market_sentiment(
        self,
        news_df: pd.DataFrame,
        title_col: str = 'title',
        content_col: str = 'content'
    ) -> Dict:
        """
        计算市场整体情绪
        
        Args:
            news_df: 新闻 DataFrame
            title_col: 标题列名
            content_col: 内容列名
            
        Returns:
            市场情绪指标字典
        """
        # 合并标题和内容
        texts = []
        
        for _, row in news_df.iterrows():
            text = str(row.get(title_col, '')) + ' ' + str(row.get(content_col, ''))
            texts.append(text)
        
        # 批量分析
        results = self.analyze_batch(texts)
        
        # 计算整体情绪
        avg_score = results['sentiment_score'].mean()
        positive_ratio = (results['sentiment_label'] == 'positive').sum() / len(results)
        negative_ratio = (results['sentiment_label'] == 'negative').sum() / len(results)
        neutral_ratio = (results['sentiment_label'] == 'neutral').sum() / len(results)
        
        # 情绪指数（0-100）
        sentiment_index = 50 + avg_score * 50
        
        return {
            'sentiment_index': sentiment_index,
            'avg_score': avg_score,
            'positive_ratio': positive_ratio,
            'negative_ratio': negative_ratio,
            'neutral_ratio': neutral_ratio,
            'total_news': len(results),
            'avg_intensity': results['intensity'].mean()
        }


def test_sentiment_analyzer():
    """测试情绪分析"""
    print("="*70)
    print("情绪分析测试")
    print("="*70)
    
    analyzer = SentimentAnalyzer()
    
    # 测试文本
    test_texts = [
        "公司业绩大幅增长，净利润创新高，非常利好",
        "业绩下滑，亏损严重，投资者担忧",
        "中性消息，无明显利好利空",
        "中标大单，业绩预期向好，但不确定性仍存",
        "政策利好支持，行业发展前景广阔",
    ]
    
    print("\n单条测试:")
    for text in test_texts:
        result = analyzer.analyze_sentiment(text)
        topics = analyzer.identify_topics(text)
        
        print(f"\n文本：{text}")
        print(f"  情绪得分：{result['sentiment_score']:.3f}")
        print(f"  情绪分类：{result['sentiment_label']}")
        print(f"  情绪强度：{result['intensity']:.3f}")
        print(f"  识别主题：{topics}")
    
    # 批量测试
    print("\n" + "="*70)
    print("批量测试")
    print("="*70)
    
    results_df = analyzer.analyze_batch(test_texts)
    print("\n批量分析结果:")
    print(results_df.to_string())
    
    # 市场情绪
    print("\n" + "="*70)
    print("市场情绪计算")
    print("="*70)
    
    news_df = pd.DataFrame({
        'title': test_texts,
        'content': [''] * len(test_texts)
    })
    
    market_sentiment = analyzer.calculate_market_sentiment(news_df)
    
    print(f"\n市场情绪指数：{market_sentiment['sentiment_index']:.2f}")
    print(f"平均得分：{market_sentiment['avg_score']:.3f}")
    print(f"正面比例：{market_sentiment['positive_ratio']*100:.1f}%")
    print(f"负面比例：{market_sentiment['negative_ratio']*100:.1f}%")
    print(f"中性比例：{market_sentiment['neutral_ratio']*100:.1f}%")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == "__main__":
    test_sentiment_analyzer()
