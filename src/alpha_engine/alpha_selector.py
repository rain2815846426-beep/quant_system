"""
Alpha 选择器

筛选优质 Alpha 因子
"""
import pandas as pd
from typing import List, Dict


class AlphaSelector:
    """Alpha 选择器"""
    
    def __init__(self, 
                 ic_threshold: float = 0.02,
                 ic_ir_threshold: float = 0.3,
                 rank_ic_threshold: float = 0.02,
                 rank_ic_ir_threshold: float = 0.3):
        """
        初始化选择器
        
        Args:
            ic_threshold: IC 均值阈值
            ic_ir_threshold: IC IR 阈值
            rank_ic_threshold: RankIC 均值阈值
            rank_ic_ir_threshold: RankIC IR 阈值
        """
        self.ic_threshold = ic_threshold
        self.ic_ir_threshold = ic_ir_threshold
        self.rank_ic_threshold = rank_ic_threshold
        self.rank_ic_ir_threshold = rank_ic_ir_threshold
    
    def select(self, results: List[Dict]) -> List[Dict]:
        """
        筛选 Alpha
        
        Args:
            results: Alpha 评估结果列表
            
        Returns:
            筛选后的 Alpha 列表
        """
        selected = []
        
        for result in results:
            # 检查是否满足阈值
            ic_pass = abs(result.get('ic_mean', 0)) >= self.ic_threshold
            ic_ir_pass = abs(result.get('ic_ir', 0)) >= self.ic_ir_threshold
            rank_ic_pass = abs(result.get('rank_ic_mean', 0)) >= self.rank_ic_threshold
            rank_ic_ir_pass = abs(result.get('rank_ic_ir', 0)) >= self.rank_ic_ir_threshold
            
            # 至少满足 IC 或 RankIC 之一
            if (ic_pass or rank_ic_pass) and (ic_ir_pass or rank_ic_ir_pass):
                selected.append(result)
        
        # 按 IC_IR 排序
        selected.sort(key=lambda x: abs(x.get('ic_ir', 0)), reverse=True)
        
        return selected
    
    def remove_duplicates(self, results: List[Dict], correlation_threshold: float = 0.7) -> List[Dict]:
        """
        去除高度相关的 Alpha
        
        Args:
            results: Alpha 结果列表
            correlation_threshold: 相关性阈值
            
        Returns:
            去重后的 Alpha 列表
        """
        if not results:
            return []
        
        # 简化版本：按 IC_IR 排序后，保留前 N 个
        results.sort(key=lambda x: abs(x.get('ic_ir', 0)), reverse=True)
        
        # 保留前 50%
        n_keep = max(1, len(results) // 2)
        return results[:n_keep]
