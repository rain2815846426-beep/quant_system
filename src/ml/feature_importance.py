"""
特征重要性分析模块

功能：
1. 模型特征重要性
2. SHAP 值分析
3. 特征选择
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class FeatureImportanceAnalyzer:
    """
    特征重要性分析器
    """
    
    def __init__(self, model=None, model_type: str = 'lightgbm'):
        """
        初始化
        
        Args:
            model: 训练好的模型
            model_type: 模型类型
        """
        self.model = model
        self.model_type = model_type
    
    def get_importance_from_model(
        self,
        feature_names: List[str]
    ) -> pd.DataFrame:
        """
        从模型获取特征重要性
        
        Args:
            feature_names: 特征名称
            
        Returns:
            特征重要性 DataFrame
        """
        if self.model is None:
            print("  ⚠️  模型未提供")
            return pd.DataFrame()
        
        if self.model_type == 'lightgbm':
            importance = self.model.feature_importance(importance_type='gain')
        elif self.model_type == 'xgboost':
            importance_dict = self.model.get_score(importance_type='gain')
            importance = np.array([importance_dict.get(f'f{i}', 0) for i in range(len(feature_names))])
        elif self.model_type == 'randomforest':
            importance = self.model.feature_importances_
        else:
            print(f"  ⚠️  不支持的模型类型：{self.model_type}")
            return pd.DataFrame()
        
        # 创建 DataFrame
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False).reset_index(drop=True)
        
        return importance_df
    
    def plot_importance(
        self,
        importance_df: pd.DataFrame,
        top_n: int = 20,
        save_path: Optional[str] = None
    ):
        """
        绘制特征重要性图
        
        Args:
            importance_df: 特征重要性 DataFrame
            top_n: 显示前 N 个特征
            save_path: 保存路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("  ⚠️  需要安装 matplotlib: pip install matplotlib")
            return
        
        top_features = importance_df.head(top_n)
        
        plt.figure(figsize=(10, 8))
        plt.barh(range(len(top_features)), top_features['importance'])
        plt.yticks(range(len(top_features)), top_features['feature'])
        plt.xlabel('Importance')
        plt.title(f'Top {top_n} Feature Importance')
        plt.gca().invert_yaxis()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"  图已保存：{save_path}")
        else:
            plt.show()
    
    def shap_analysis(
        self,
        X: np.ndarray,
        feature_names: List[str],
        sample_size: int = 100
    ) -> pd.DataFrame:
        """
        SHAP 值分析
        
        Args:
            X: 特征矩阵
            feature_names: 特征名称
            sample_size: 样本数量
            
        Returns:
            SHAP 分析结果
        """
        try:
            import shap
        except ImportError:
            print("  ⚠️  需要安装 shap: pip install shap")
            return pd.DataFrame()
        
        if self.model is None:
            print("  ⚠️  模型未提供")
            return pd.DataFrame()
        
        # 采样
        if len(X) > sample_size:
            indices = np.random.choice(len(X), sample_size, replace=False)
            X_sample = X[indices]
        else:
            X_sample = X
        
        # 创建解释器
        if self.model_type == 'lightgbm':
            explainer = shap.TreeExplainer(self.model)
        elif self.model_type == 'xgboost':
            explainer = shap.TreeExplainer(self.model)
        elif self.model_type == 'randomforest':
            explainer = shap.TreeExplainer(self.model)
        else:
            print(f"  ⚠️  不支持的模型类型：{self.model_type}")
            return pd.DataFrame()
        
        # 计算 SHAP 值
        shap_values = explainer.shap_values(X_sample)
        
        # 平均绝对 SHAP 值
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        
        # 创建 DataFrame
        shap_df = pd.DataFrame({
            'feature': feature_names,
            'mean_abs_shap': mean_abs_shap
        }).sort_values('mean_abs_shap', ascending=False).reset_index(drop=True)
        
        return shap_df
    
    def select_features(
        self,
        importance_df: pd.DataFrame,
        threshold: float = 0.01,
        top_n: Optional[int] = None
    ) -> List[str]:
        """
        特征选择
        
        Args:
            importance_df: 特征重要性 DataFrame
            threshold: 重要性阈值
            top_n: 保留前 N 个特征
            
        Returns:
            选中的特征名称列表
        """
        if top_n:
            selected = importance_df.head(top_n)['feature'].tolist()
        else:
            total_importance = importance_df['importance'].sum()
            if total_importance > 0:
                importance_df = importance_df.copy()
                importance_df['cumulative'] = importance_df['importance'].cumsum() / total_importance
                selected = importance_df[importance_df['cumulative'] <= (1 - threshold)]['feature'].tolist()
            else:
                selected = []
        
        print(f"  原始特征数：{len(importance_df)}")
        print(f"  选中特征数：{len(selected)}")
        
        return selected


def test_importance_analyzer():
    """测试特征重要性分析"""
    print("="*70)
    print("特征重要性分析测试")
    print("="*70)
    
    from .model_trainer import ModelTrainer
    
    # 创建测试数据
    np.random.seed(42)
    n_samples = 500
    n_features = 20
    
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)
    
    split_idx = int(n_samples * 0.8)
    X_train, X_valid = X[:split_idx], X[split_idx:]
    y_train, y_valid = y[:split_idx], y[split_idx:]
    
    feature_names = [f'feature_{i}' for i in range(n_features)]
    
    # 训练模型
    print("\n训练模型...")
    trainer = ModelTrainer(model_type='lightgbm')
    trainer.train(X_train, y_train, X_valid, y_valid, feature_names)
    
    # 特征重要性分析
    print("\n特征重要性分析...")
    analyzer = FeatureImportanceAnalyzer(trainer.model, model_type='lightgbm')
    
    importance_df = analyzer.get_importance_from_model(feature_names)
    
    print("\nTop 10 特征:")
    print(importance_df.head(10).to_string())
    
    # 特征选择
    print("\n特征选择...")
    selected = analyzer.select_features(importance_df, top_n=10)
    print(f"  选中特征：{selected}")
    
    print("\n" + "="*70)
    print("测试完成！")
    print("="*70)


if __name__ == "__main__":
    test_importance_analyzer()
