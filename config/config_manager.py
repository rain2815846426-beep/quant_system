"""
配置管理模块

功能：
1. 读取配置文件
2. 保存用户偏好
3. 提供默认配置
"""
import configparser
from pathlib import Path
from typing import Dict, Any, Optional

project_root = Path(__file__).parent.parent


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化
        
        Args:
            config_path: 配置文件路径（默认 config/config.ini）
        """
        if config_path is None:
            config_path = project_root / "config" / "config.ini"
        
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.load()
    
    def load(self):
        """加载配置"""
        if self.config_path.exists():
            self.config.read(self.config_path, encoding='utf-8')
    
    def save(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """获取配置值"""
        try:
            return self.config.get(section, key)
        except:
            return fallback
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置"""
        try:
            return self.config.getint(section, key)
        except:
            return fallback
    
    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点配置"""
        try:
            return self.config.getfloat(section, key)
        except:
            return fallback
    
    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置"""
        try:
            return self.config.getboolean(section, key)
        except:
            return fallback
    
    def set(self, section: str, key: str, value: Any):
        """设置配置值"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = str(value)
        self.save()
    
    # ========== 回测配置 ==========
    @property
    def backtest_config(self) -> Dict:
        """获取回测配置"""
        return {
            'factor': self.get('backtest', 'default_factor', 'momentum_20'),
            'top_n': self.get_int('backtest', 'default_top_n', 20),
            'holding_period': self.get_int('backtest', 'default_holding_period', 20),
            'position_size': self.get_float('backtest', 'default_position_size', 0.6),
            'stop_loss': self.get_float('backtest', 'default_stop_loss', 0.10),
            'use_reverse': self.get_bool('backtest', 'default_use_reverse', True),
        }
    
    def save_backtest_config(self, **kwargs):
        """保存回测配置"""
        for key, value in kwargs.items():
            self.set('backtest', f'default_{key}', value)
    
    # ========== 数据源配置 ==========
    @property
    def data_config(self) -> Dict:
        """获取数据源配置"""
        return {
            'primary': self.get('data', 'primary_data_source', 'akshare'),
            'fallback': self.get('data', 'fallback_data_source', 'tushare'),
            'tushare_token': self.get('data', 'tushare_token', ''),
        }
    
    def set_tushare_token(self, token: str):
        """设置 Tushare Token"""
        self.set('data', 'tushare_token', token)
    
    # ========== 数据库配置 ==========
    @property
    def database_path(self) -> Path:
        """获取数据库路径"""
        return project_root / self.get('database', 'db_path', 'database/quant.db')


# 全局配置实例
config = ConfigManager()


def get_backtest_defaults() -> Dict:
    """获取回测默认参数"""
    return config.backtest_config


def save_backtest_preferences(**kwargs):
    """保存回测偏好"""
    config.save_backtest_config(**kwargs)
    print(f"✅ 回测配置已保存")
    print(f"   因子：{kwargs.get('factor', 'momentum_20')}")
    print(f"   Top N: {kwargs.get('top_n', 20)}")
    print(f"   仓位：{kwargs.get('position_size', 0.6)}")
    print(f"   止损：{kwargs.get('stop_loss', 0.10)}")


def get_data_sources() -> Dict:
    """获取数据源配置"""
    return config.data_config


def set_tushare_token(token: str):
    """设置 Tushare Token"""
    config.set_tushare_token(token)
    print(f"✅ Tushare Token 已保存")


if __name__ == "__main__":
    # 测试配置
    print("="*70)
    print("配置管理测试")
    print("="*70)
    
    print("\n回测默认配置:")
    backtest_cfg = get_backtest_defaults()
    for k, v in backtest_cfg.items():
        print(f"  {k}: {v}")
    
    print("\n数据源配置:")
    data_cfg = get_data_sources()
    for k, v in data_cfg.items():
        print(f"  {k}: {v}")
    
    print("\n" + "="*70)
