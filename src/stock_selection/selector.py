"""
股票筛选系统

每日对所有股票进行 Alpha Score 排名，输出 Top N 股票列表
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional


class StockSelector:
    """股票筛选器"""
    
    def __init__(
        self,
        top_n_list: List[int] = [10, 20, 50]
    ):
        """
        初始化
        
        Args:
            top_n_list: 需要输出的 Top N 列表
        """
        self.top_n_list = top_n_list
    
    def select_top_stocks(
        self,
        alpha_score: pd.Series,
        date: str
    ) -> Dict[int, pd.DataFrame]:
        """
        筛选 Top N 股票
        
        Args:
            alpha_score: Alpha Score（index: stocks）
            date: 交易日期
            
        Returns:
            Dict[N -> DataFrame with top N stocks]
        """
        results = {}
        
        # 按 Score 排序
        sorted_stocks = alpha_score.sort_values(ascending=False)
        
        for n in self.top_n_list:
            top_n = sorted_stocks.head(n)
            
            result_df = pd.DataFrame({
                'ts_code': top_n.index,
                'alpha_score': top_n.values,
                'rank': range(1, len(top_n) + 1)
            })
            
            result_df['trade_date'] = date
            result_df = result_df[['trade_date', 'ts_code', 'alpha_score', 'rank']]
            
            results[n] = result_df
        
        return results
    
    def save_results(
        self,
        results: Dict[int, pd.DataFrame],
        output_dir: Path
    ):
        """
        保存筛选结果
        
        Args:
            results: 筛选结果
            output_dir: 输出目录
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 合并所有 Top N 结果
        all_results = []
        for n, df in results.items():
            df['top_n'] = n
            all_results.append(df)
        
        combined = pd.concat(all_results, ignore_index=True)
        
        # 保存
        output_path = output_dir / 'top_stocks_daily.csv'
        
        # 如果文件存在，追加
        if output_path.exists():
            existing = pd.read_csv(output_path)
            combined = pd.concat([existing, combined], ignore_index=True)
        
        combined.to_csv(output_path, index=False)
        
        print(f"Top N 股票已保存：{output_path}")


def generate_daily_stock_selection(
    factor_data: pd.DataFrame,
    alpha_score_func,
    selector: StockSelector,
    output_dir: Path,
    risk_filter=None
) -> pd.DataFrame:
    """
    生成每日选股结果
    
    Args:
        factor_data: 因子数据 DataFrame (index: date, columns: stocks)
        alpha_score_func: Alpha Score 计算函数
        selector: 股票筛选器
        output_dir: 输出目录
        risk_filter: 风险过滤函数（可选）
        
    Returns:
        所有选股结果 DataFrame
    """
    all_results = []
    dates = factor_data.index
    
    for i, date in enumerate(dates):
        if (i + 1) % 100 == 0:
            print(f"处理进度：{i + 1}/{len(dates)}")
        
        # 获取当日因子值
        factor_date = factor_data.loc[date]
        
        # 风险过滤
        if risk_filter is not None:
            factor_date = risk_filter(factor_date, date)
        
        # 计算 Alpha Score
        alpha_score = alpha_score_func(factor_date)
        
        # 筛选 Top N
        results = selector.select_top_stocks(alpha_score, date)
        
        # 保存
        selector.save_results(results, output_dir)
        
        # 收集结果
        for n, df in results.items():
            all_results.append(df)
    
    return pd.concat(all_results, ignore_index=True)
