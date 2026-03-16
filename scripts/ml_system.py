#!/usr/bin/env python3
"""
机器学习系统 - 主运行脚本

功能：
1. 特征工程
2. 模型训练（LightGBM/XGBoost/RandomForest）
3. 模型评估
4. 特征重要性分析
5. 预测与选股

使用:
    python3 scripts/ml_system.py
    
    # 指定模型
    python3 scripts/ml_system.py --model lightgbm
    
    # 只测试
    python3 scripts/ml_system.py --test
"""
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection
from src.ml.feature_engineering import FeatureEngineer
from src.ml.model_trainer import ModelTrainer
from src.ml.model_evaluator import ModelEvaluator
from src.ml.feature_importance import FeatureImportanceAnalyzer


def run_ml_pipeline(
    model_type: str = 'lightgbm',
    start_date: str = '20200101',
    end_date: str = '20260313',
    target_period: int = 20,
    test_mode: bool = False
):
    """
    运行完整机器学习流程
    
    Args:
        model_type: 模型类型
        start_date: 开始日期
        end_date: 结束日期
        target_period: 预测周期
        test_mode: 测试模式
    """
    print("="*70)
    print("机器学习系统")
    print("="*70)
    print(f"模型：{model_type}")
    print(f"日期：{start_date} - {end_date}")
    print(f"预测周期：{target_period}日")
    print(f"模式：{'测试' if test_mode else '完整'}")
    print("="*70)
    
    # 1. 特征工程
    print("\n[1/5] 特征工程...")
    fe = FeatureEngineer(db_path=DATABASE_PATH, target_period=target_period)
    
    if test_mode:
        # 测试模式：使用少量数据
        data = fe.load_data(start_date='20251201', end_date='20260313')
    else:
        data = fe.load_data(start_date=start_date, end_date=end_date)
    
    if data.empty:
        print("  ❌ 数据为空")
        return
    
    # 准备特征
    data, feature_names = fe.prepare_features(
        data,
        lag_days=[1, 5],
        rolling_windows=[5, 10, 20],
        standardize=True
    )
    
    # 获取特征矩阵
    X, y, ts_codes, trade_dates = fe.get_feature_matrix(data)
    
    print(f"  特征矩阵：{X.shape}")
    print(f"  目标向量：{y.shape}")
    
    # 划分训练验证集（按时间）
    unique_dates = sorted(list(set(trade_dates)))
    split_date_idx = int(len(unique_dates) * 0.8)
    split_date = unique_dates[split_date_idx]
    
    train_mask = trade_dates < split_date
    valid_mask = trade_dates >= split_date
    
    X_train, X_valid = X[train_mask], X[valid_mask]
    y_train, y_valid = y[train_mask], y[valid_mask]
    
    print(f"  训练集：{X_train.shape[0]} 条")
    print(f"  验证集：{X_valid.shape[0]} 条")
    
    # 2. 模型训练
    print("\n[2/5] 模型训练...")
    trainer = ModelTrainer(model_type=model_type)
    trainer.train(X_train, y_train, X_valid, y_valid, feature_names)
    
    # 3. 模型预测
    print("\n[3/5] 模型预测...")
    y_pred_valid = trainer.predict(X_valid)
    
    # 4. 模型评估
    print("\n[4/5] 模型评估...")
    evaluator = ModelEvaluator()
    
    # 创建预测 Series
    valid_idx = np.where(valid_mask)[0]
    pred_series = pd.Series(y_pred_valid, index=[f"{ts_codes[i]}_{trade_dates[i]}" for i in valid_idx])
    actual_series = pd.Series(y_valid, index=[f"{ts_codes[i]}_{trade_dates[i]}" for i in valid_idx])
    
    # IC 评估
    ic_metrics = evaluator.evaluate_ic(pred_series, actual_series)
    
    print("\nIC 评估结果:")
    print(f"  Pearson IC: {ic_metrics['ic_pearson']:.6f}")
    print(f"  Spearman RankIC: {ic_metrics['ic_spearman']:.6f}")
    print(f"  IC IR: {ic_metrics['ic_ir']:.6f}")
    print(f"  样本数：{ic_metrics['n_samples']}")
    
    # 5. 特征重要性
    print("\n[5/5] 特征重要性分析...")
    analyzer = FeatureImportanceAnalyzer(trainer.model, model_type=model_type)
    importance_df = analyzer.get_importance_from_model(feature_names)
    
    print("\nTop 20 特征:")
    print(importance_df.head(20).to_string())
    
    # 保存结果
    print("\n" + "="*70)
    print("保存结果...")
    print("="*70)
    
    output_dir = Path(__file__).parent.parent / "research_results" / "ml"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存特征重要性
    importance_df.to_csv(output_dir / f'{model_type}_feature_importance.csv', index=False)
    print(f"  特征重要性：{output_dir / f'{model_type}_feature_importance.csv'}")
    
    # 保存模型
    model_path = output_dir / f'{model_type}_model.pkl'
    trainer.save(str(model_path))
    print(f"  模型：{model_path}")
    
    # 保存评估结果
    eval_results = {
        'model': model_type,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        **ic_metrics
    }
    eval_df = pd.DataFrame([eval_results])
    eval_df.to_csv(output_dir / f'{model_type}_evaluation.csv', index=False)
    print(f"  评估结果：{output_dir / f'{model_type}_evaluation.csv'}")
    
    print("\n" + "="*70)
    print("机器学习流程完成！")
    print("="*70)
    
    return {
        'trainer': trainer,
        'evaluator': evaluator,
        'analyzer': analyzer,
        'ic_metrics': ic_metrics,
        'importance_df': importance_df
    }


def main():
    parser = argparse.ArgumentParser(description="机器学习系统")
    parser.add_argument(
        '--model',
        type=str,
        default='lightgbm',
        choices=['lightgbm', 'xgboost', 'randomforest'],
        help='模型类型'
    )
    parser.add_argument(
        '--start_date',
        type=str,
        default='20200101',
        help='开始日期'
    )
    parser.add_argument(
        '--end_date',
        type=str,
        default='20260313',
        help='结束日期'
    )
    parser.add_argument(
        '--target_period',
        type=int,
        default=20,
        help='预测周期'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='测试模式（快速运行）'
    )
    
    args = parser.parse_args()
    
    run_ml_pipeline(
        model_type=args.model,
        start_date=args.start_date,
        end_date=args.end_date,
        target_period=args.target_period,
        test_mode=args.test
    )


if __name__ == "__main__":
    main()
