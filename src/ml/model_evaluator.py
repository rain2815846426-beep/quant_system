"""
模型评估模块

功能：
1. 预测评估（IC、RankIC）
2. 回测评估
3. 模型对比
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ModelEvaluator:
    """
    模型评估器
    """
    
    def __init__(self):
        self.results = {}
    
    def evaluate_ic(
        self,
        predictions: pd.Series,
        actual_returns: pd.Series
    ) -> Dict:
        """
        计算 IC 指标
        
        Args:
            predictions: 预测值
            actual_returns: 实际收益
            
        Returns:
            IC 指标字典
        """
        # 对齐
        common_idx = predictions.index.intersection(actual_returns.index)
        pred = predictions.loc[common_idx]
        ret = actual_returns.loc[common_idx]
        
        # Pearson IC
        ic_pearson = pred.corr(ret, method='pearson')
        
        # Spearman RankIC
        ic_spearman = pred.corr(ret, method='spearman')
        
        # IC IR
        ic_ir = ic_pearson / pred.std() if pred.std() > 1e-10 else 0
        
        return {
            'ic_pearson': ic_pearson,
            'ic_spearman': ic_spearman,
            'ic_ir': ic_ir,
            'n_samples': len(common_idx)
        }
    
    def evaluate_portfolio(
        self,
        predictions: pd.DataFrame,
        actual_returns: pd.DataFrame,
        top_n: int = 10,
        bottom_n: int = 10
    ) -> Dict:
        """
        组合评估（多空收益）
        
        Args:
            predictions: 预测值（index: date, columns: stock）
            actual_returns: 实际收益
            top_n: 多头数量
            bottom_n: 空头数量
            
        Returns:
            组合评估指标
        """
        long_short_returns = []
        
        for date in predictions.index:
            if date not in actual_returns.index:
                continue
            
            pred_date = predictions.loc[date].dropna()
            ret_date = actual_returns.loc[date].dropna()
            
            common = pred_date.index.intersection(ret_date.index)
            
            if len(common) < top_n + bottom_n:
                continue
            
            # 按预测排序
            sorted_pred = pred_date.loc[common].sort_values(ascending=False)
            
            # 多头
            long_stocks = sorted_pred.head(top_n).index
            long_ret = ret_date.loc[long_stocks].mean()
            
            # 空头
            short_stocks = sorted_pred.tail(bottom_n).index
            short_ret = ret_date.loc[short_stocks].mean()
            
            # 多空收益
            ls_ret = long_ret - short_ret
            long_short_returns.append(ls_ret)
        
        if not long_short_returns:
            return {}
        
        ls_series = pd.Series(long_short_returns)
        
        return {
            'ls_mean': ls_series.mean(),
            'ls_std': ls_series.std(),
            'ls_ir': ls_series.mean() / ls_series.std() if ls_series.std() > 1e-10 else 0,
            'ls_sharpe': ls_series.mean() / ls_series.std() * np.sqrt(252) if ls_series.std() > 1e-10 else 0,
            'n_periods': len(long_short_returns)
        }
    
    def compare_models(
        self,
        model_predictions: Dict[str, pd.Series],
        actual_returns: pd.Series
    ) -> pd.DataFrame:
        """
        对比多个模型
        
        Args:
            model_predictions: {model_name: predictions}
            actual_returns: 实际收益
            
        Returns:
            对比结果 DataFrame
        """
        results = []
        
        for model_name, predictions in model_predictions.items():
            ic_metrics = self.evaluate_ic(predictions, actual_returns)
            results.append({
                'model': model_name,
                **ic_metrics
            })
        
        return pd.DataFrame(results)


def test_evaluator():
    """测试评估器"""
    print("="*70)
    print("模型评估器测试")
    print("="*70)
    
    evaluator = ModelEvaluator()
    
    # 创建测试数据
    np.random.seed(42)
    n = 1000
    
    predictions = pd.Series(np.random.randn(n))
    actual = pd.Series(np.random.randn(n))
    
    # IC 评估
    print("\nIC 评估:")
    ic_metrics = evaluator.evaluate_ic(predictions, actual)
    
    for metric, value in ic_metrics.items():
        print(f"  {metric}: {value:.4f}")
    
    print("\n" + "="*70)
    print("测试完成！")
    print("="*70)


if __name__ == "__main__":
    test_evaluator()
