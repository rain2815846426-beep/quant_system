"""
特征工程模块

功能：
1. 特征选择
2. 特征标准化
3. 特征滞后（避免前视偏差）
4. 滚动统计特征
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


class FeatureEngineer:
    """
    特征工程器
    
    提供完整的特征工程流程：
    1. 数据加载
    2. 特征选择
    3. 特征标准化
    4. 特征滞后（避免前视偏差）
    5. 滚动统计特征
    """
    
    def __init__(
        self,
        db_path: str = DATABASE_PATH,
        target_period: int = 20
    ):
        """
        初始化
        
        Args:
            db_path: 数据库路径
            target_period: 预测周期（默认 20 日）
        """
        self.db_path = db_path
        self.target_period = target_period
        
        # 特征列表
        self.feature_names = []
        
        # 标准化参数
        self.feature_means = {}
        self.feature_stds = {}
    
    def load_data(
        self,
        start_date: str = '20200101',
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        加载数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            特征和目标 DataFrame
        """
        print("加载数据...")
        
        with get_db_connection(self.db_path) as conn:
            # 加载因子数据
            factor_query = """
                SELECT ts_code, trade_date, factor_name, factor_value
                FROM factor_values
                WHERE trade_date >= ? AND trade_date <= ?
                ORDER BY ts_code, trade_date
            """
            
            if end_date:
                df = pd.read_sql_query(factor_query, conn, params=(start_date, end_date))
            else:
                df = pd.read_sql_query(factor_query.replace('AND trade_date <= ?', ''), 
                                      conn, params=(start_date,))
            
            # Pivot 因子数据
            if not df.empty:
                feature_df = df.pivot_table(
                    index=['ts_code', 'trade_date'],
                    columns='factor_name',
                    values='factor_value'
                ).reset_index()
            else:
                feature_df = pd.DataFrame()
            
            # 加载价格数据（用于计算目标和额外特征）
            price_query = """
                SELECT ts_code, trade_date, close, volume
                FROM daily_prices
                WHERE trade_date >= ?
                ORDER BY ts_code, trade_date
            """
            price_df = pd.read_sql_query(price_query, conn, params=(start_date,))
            
            # Pivot 价格数据
            if not price_df.empty:
                price_pivot = price_df.pivot_table(
                    index=['ts_code', 'trade_date'],
                    values=['close', 'volume']
                ).reset_index()
                
                # 合并
                data = feature_df.merge(price_pivot, on=['ts_code', 'trade_date'], how='left')
            else:
                data = feature_df
        
        print(f"  加载数据：{len(data)} 条")
        
        return data
    
    def create_target(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        创建目标变量（未来收益）
        
        Args:
            data: 原始数据
            
        Returns:
            带目标的 DataFrame
        """
        print("创建目标变量...")
        
        data = data.copy()
        
        # 按股票分组计算未来收益
        def calc_future_return(group):
            group = group.sort_values('trade_date')
            group[f'target_{self.target_period}'] = group['close'].shift(-self.target_period) / group['close'] - 1
            return group
        
        data = data.groupby('ts_code').apply(calc_future_return)
        
        # 删除最后 self.target_period 行（无法计算目标）
        data = data.dropna(subset=[f'target_{self.target_period}'])
        
        print(f"  目标变量：{len(data)} 条")
        
        return data
    
    def create_lagged_features(
        self,
        data: pd.DataFrame,
        lag_days: List[int] = [1, 5, 10]
    ) -> pd.DataFrame:
        """
        创建滞后特征（避免前视偏差）
        
        Args:
            data: 原始数据
            lag_days: 滞后天数列表
            
        Returns:
            带滞后特征的 DataFrame
        """
        print(f"创建滞后特征...")
        
        data = data.copy()
        
        # 需要滞后的特征（所有因子）
        feature_cols = [col for col in data.columns 
                       if col not in ['ts_code', 'trade_date', 'close', 'volume', f'target_{self.target_period}']]
        
        self.feature_names = feature_cols.copy()
        
        # 创建滞后特征
        for lag in lag_days:
            for col in feature_cols:
                lag_col = f'{col}_lag{lag}'
                
                # 按股票滞后（重置索引避免歧义）
                data[lag_col] = data.reset_index(drop=True).groupby('ts_code')[col].shift(lag)
                
                if lag_col not in self.feature_names:
                    self.feature_names.append(lag_col)
        
        # 删除有 NaN 的行
        lag_cols = [f'{col}_lag{lag}' for lag in lag_days for col in feature_cols]
        data = data.dropna(subset=lag_cols)
        
        print(f"  滞后特征数：{len(lag_cols)}")
        print(f"  处理后数据：{len(data)} 条")
        
        return data
    
    def create_rolling_features(
        self,
        data: pd.DataFrame,
        windows: List[int] = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        创建滚动统计特征
        
        Args:
            data: 原始数据
            windows: 滚动窗口列表
            
        Returns:
            带滚动特征的 DataFrame
        """
        print(f"创建滚动统计特征...")
        
        data = data.copy()
        
        # 对价格和成交量创建滚动特征
        for window in windows:
            # 滚动均值
            data[f'close_ma{window}'] = data.groupby('ts_code')['close'].transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
            
            # 滚动标准差
            data[f'close_std{window}'] = data.groupby('ts_code')['close'].transform(
                lambda x: x.rolling(window, min_periods=1).std()
            )
            
            data[f'volume_ma{window}'] = data.groupby('ts_code')['volume'].transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
        
        print(f"  滚动特征：{len(windows) * 3} 个")
        
        return data
    
    def standardize_features(
        self,
        data: pd.DataFrame,
        fit: bool = True
    ) -> pd.DataFrame:
        """
        特征标准化
        
        Args:
            data: 原始数据
            fit: 是否重新拟合标准化参数
            
        Returns:
            标准化后的 DataFrame
        """
        print("特征标准化...")
        
        data = data.copy()
        
        for col in self.feature_names:
            if col not in data.columns:
                continue
            
            if fit:
                # 计算并保存参数
                self.feature_means[col] = data[col].mean()
                self.feature_stds[col] = data[col].std()
            
            # 标准化
            mean = self.feature_means.get(col, data[col].mean())
            std = self.feature_stds.get(col, data[col].std())
            
            if std > 1e-10:
                data[col] = (data[col] - mean) / std
            else:
                data[col] = 0
        
        print(f"  标准化特征：{len(self.feature_names)} 个")
        
        return data
    
    def prepare_features(
        self,
        data: pd.DataFrame,
        lag_days: List[int] = [1, 5],
        rolling_windows: List[int] = [5, 10, 20],
        standardize: bool = True
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        完整的特征准备流程
        
        Args:
            data: 原始数据
            lag_days: 滞后天数
            rolling_windows: 滚动窗口
            standardize: 是否标准化
            
        Returns:
            (处理后的 DataFrame, 特征名称列表)
        """
        print("\n" + "="*70)
        print("特征工程流程")
        print("="*70)
        
        # 1. 创建目标
        data = self.create_target(data)
        
        # 2. 创建滞后特征
        data = self.create_lagged_features(data, lag_days)
        
        # 3. 创建滚动特征
        data = self.create_rolling_features(data, rolling_windows)
        
        # 4. 标准化
        if standardize:
            data = self.standardize_features(data, fit=True)
        
        # 5. 删除 NaN
        data = data.dropna()
        
        print(f"\n最终数据：{len(data)} 条")
        print(f"特征数量：{len(self.feature_names)}")
        
        return data, self.feature_names
    
    def get_feature_matrix(
        self,
        data: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        获取特征矩阵和目标向量
        
        Returns:
            (X, y, ts_codes, trade_dates)
        """
        feature_cols = [col for col in self.feature_names if col in data.columns]
        target_col = f'target_{self.target_period}'
        
        X = data[feature_cols].values
        y = data[target_col].values
        ts_codes = data['ts_code'].values
        trade_dates = data['trade_date'].values
        
        return X, y, ts_codes, trade_dates


def test_feature_engineering():
    """测试特征工程"""
    print("="*70)
    print("特征工程测试")
    print("="*70)
    
    fe = FeatureEngineer(target_period=20)
    
    # 加载数据
    data = fe.load_data(start_date='20250101', end_date='20260313')
    
    if data.empty:
        print("  ❌ 数据为空")
        return
    
    # 准备特征
    data, features = fe.prepare_features(
        data,
        lag_days=[1, 5],
        rolling_windows=[5, 10, 20],
        standardize=True
    )
    
    # 获取特征矩阵
    X, y, ts_codes, dates = fe.get_feature_matrix(data)
    
    print(f"\n特征矩阵形状：{X.shape}")
    print(f"目标向量形状：{y.shape}")
    print(f"特征数量：{len(features)}")
    
    print("\n前 10 个特征:")
    for i, feat in enumerate(features[:10]):
        print(f"  {i+1}. {feat}")
    
    print("\n" + "="*70)
    print("特征工程测试完成！")
    print("="*70)


if __name__ == "__main__":
    test_feature_engineering()
