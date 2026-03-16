"""
模型训练模块

支持：
- LightGBM
- XGBoost
- RandomForest
- 滚动训练
- 超参数优化
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import sys
import joblib
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ModelTrainer:
    """
    模型训练器
    
    支持多种模型和训练策略
    """
    
    def __init__(
        self,
        model_type: str = 'lightgbm',
        params: Optional[Dict] = None
    ):
        """
        初始化
        
        Args:
            model_type: 模型类型 ('lightgbm' / 'xgboost' / 'randomforest')
            params: 模型参数
        """
        self.model_type = model_type
        self.params = params or self._get_default_params()
        self.model = None
        self.feature_names = []
    
    def _get_default_params(self) -> Dict:
        """获取默认参数"""
        if self.model_type == 'lightgbm':
            return {
                'objective': 'regression',
                'metric': 'mse',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'n_estimators': 1000,
                'early_stopping_rounds': 50
            }
        elif self.model_type == 'xgboost':
            return {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'n_estimators': 1000,
                'early_stopping_rounds': 50
            }
        elif self.model_type == 'randomforest':
            return {
                'n_estimators': 100,
                'max_depth': 10,
                'min_samples_split': 5,
                'min_samples_leaf': 2,
                'n_jobs': -1
            }
        else:
            raise ValueError(f"未知模型类型：{self.model_type}")
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: np.ndarray,
        y_valid: np.ndarray,
        feature_names: Optional[List[str]] = None
    ) -> Any:
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练目标
            X_valid: 验证特征
            y_valid: 验证目标
            feature_names: 特征名称
            
        Returns:
            训练好的模型
        """
        print(f"\n训练 {self.model_type} 模型...")
        
        self.feature_names = feature_names or []
        
        if self.model_type == 'lightgbm':
            self.model = self._train_lightgbm(X_train, y_train, X_valid, y_valid)
        elif self.model_type == 'xgboost':
            self.model = self._train_xgboost(X_train, y_train, X_valid, y_valid)
        elif self.model_type == 'randomforest':
            self.model = self._train_randomforest(X_train, y_train)
        
        print(f"  模型训练完成")
        
        return self.model
    
    def _train_lightgbm(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: np.ndarray,
        y_valid: np.ndarray
    ) -> Any:
        """训练 LightGBM"""
        try:
            import lightgbm as lgb
        except ImportError:
            print("  ❌ 需要安装 lightgbm: pip install lightgbm")
            return None
        
        # 创建数据集
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)
        
        # 训练
        model = lgb.train(
            self.params,
            train_data,
            valid_sets=[train_data, valid_data],
            valid_names=['train', 'valid'],
            num_boost_round=1000,
            early_stopping_rounds=self.params.get('early_stopping_rounds', 50),
            verbose_eval=100
        )
        
        # 打印最佳迭代
        print(f"  最佳迭代：{model.best_iteration}")
        
        return model
    
    def _train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_valid: np.ndarray,
        y_valid: np.ndarray
    ) -> Any:
        """训练 XGBoost"""
        try:
            import xgboost as xgb
        except ImportError:
            print("  ❌ 需要安装 xgboost: pip install xgboost")
            return None
        
        # 创建数据集
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)
        
        # 训练
        evals = [(dtrain, 'train'), (dvalid, 'valid')]
        
        model = xgb.train(
            self.params,
            dtrain,
            num_boost_round=1000,
            evals=evals,
            early_stopping_rounds=self.params.get('early_stopping_rounds', 50),
            verbose_eval=100
        )
        
        print(f"  最佳迭代：{model.best_iteration}")
        
        return model
    
    def _train_randomforest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray
    ) -> Any:
        """训练 RandomForest"""
        from sklearn.ensemble import RandomForestRegressor
        
        model = RandomForestRegressor(**self.params)
        model.fit(X_train, y_train)
        
        return model
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测
        
        Args:
            X: 特征矩阵
            
        Returns:
            预测值
        """
        if self.model is None:
            raise ValueError("模型未训练")
        
        if self.model_type == 'xgboost':
            import xgboost as xgb
            dtest = xgb.DMatrix(X)
            return self.model.predict(dtest)
        else:
            return self.model.predict(X)
    
    def save(self, path: str):
        """
        保存模型
        
        Args:
            path: 保存路径
        """
        if self.model is None:
            print("  ⚠️  模型未训练，无法保存")
            return
        
        save_data = {
            'model': self.model,
            'model_type': self.model_type,
            'params': self.params,
            'feature_names': self.feature_names
        }
        
        joblib.dump(save_data, path)
        print(f"  模型已保存：{path}")
    
    def load(self, path: str):
        """
        加载模型
        
        Args:
            path: 模型路径
        """
        save_data = joblib.load(path)
        
        self.model = save_data['model']
        self.model_type = save_data['model_type']
        self.params = save_data['params']
        self.feature_names = save_data['feature_names']
        
        print(f"  模型已加载：{path}")


def test_model_trainer():
    """测试模型训练器"""
    print("="*70)
    print("模型训练器测试")
    print("="*70)
    
    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20
    
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)
    
    # 划分训练验证集
    split_idx = int(n_samples * 0.8)
    X_train, X_valid = X[:split_idx], X[split_idx:]
    y_train, y_valid = y[:split_idx], y[split_idx:]
    
    feature_names = [f'feature_{i}' for i in range(n_features)]
    
    # 测试 LightGBM
    print("\n[1/3] 测试 LightGBM...")
    trainer_lgb = ModelTrainer(model_type='lightgbm')
    trainer_lgb.train(X_train, y_train, X_valid, y_valid, feature_names)
    
    # 预测
    pred = trainer_lgb.predict(X_valid)
    print(f"  预测形状：{pred.shape}")
    
    # 测试 XGBoost
    print("\n[2/3] 测试 XGBoost...")
    trainer_xgb = ModelTrainer(model_type='xgboost')
    trainer_xgb.train(X_train, y_train, X_valid, y_valid, feature_names)
    
    # 测试 RandomForest
    print("\n[3/3] 测试 RandomForest...")
    trainer_rf = ModelTrainer(model_type='randomforest')
    trainer_rf.train(X_train, y_train, X_valid, y_valid, feature_names)
    
    print("\n" + "="*70)
    print("模型训练器测试完成！")
    print("="*70)


if __name__ == "__main__":
    test_model_trainer()
