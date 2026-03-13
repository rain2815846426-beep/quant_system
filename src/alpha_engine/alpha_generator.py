"""
Alpha 生成器

支持：
1. 随机生成 Alpha 表达式
2. 基于模板生成
"""
import random
import pandas as pd
import numpy as np
from typing import List, Dict, Callable
from src.operators import (
    rank, delay, delta, ts_rank, ts_max, ts_min,
    correlation, covariance, decay_linear, scale,
    signed_power, abs_value, log_value
)


class AlphaGenerator:
    """Alpha 生成器基类"""
    
    def __init__(self):
        self.operators = {}
        self.variables = {}
    
    def register_operator(self, name: str, func: Callable):
        """注册算子"""
        self.operators[name] = func
    
    def register_variable(self, name: str, series: pd.Series):
        """注册变量"""
        self.variables[name] = series
    
    def generate(self, expression: str) -> pd.Series:
        """生成 Alpha"""
        raise NotImplementedError


class RandomAlphaGenerator(AlphaGenerator):
    """随机 Alpha 生成器"""
    
    def __init__(self):
        super().__init__()
        
        # 注册算子
        self.register_operator('rank', lambda x: x.rank(pct=True))
        self.register_operator('ts_rank', lambda x, d=10: x.rolling(d, min_periods=1).apply(lambda s: s.rank(pct=True).iloc[-1] if len(s) > 1 else np.nan, raw=False))
        self.register_operator('delta', lambda x, d=1: x - x.shift(d))
        self.register_operator('delay', lambda x, d=1: x.shift(d))
        self.register_operator('correlation', lambda x, y, d=10: x.rolling(d, min_periods=1).corr(y))
        self.register_operator('scale', lambda x: x / x.abs().sum() * 1000000)
        self.register_operator('decay_linear', lambda x, d=10: x.rolling(d, min_periods=1).apply(lambda s: np.average(s, weights=list(range(1, d+1))), raw=False))
        self.register_operator('abs', lambda x: x.abs())
        self.register_operator('log', lambda x: np.log1p(x.abs()))
        self.register_operator('sign', lambda x: np.sign(x))
        
        # 算子参数范围
        self.operator_params = {
            'rank': {'d': [1]},
            'ts_rank': {'d': [5, 10, 20, 60]},
            'delta': {'d': [1, 3, 5, 10]},
            'delay': {'d': [1, 3, 5, 10]},
            'correlation': {'d': [5, 10, 20, 60]},
            'scale': {'d': [1]},
            'decay_linear': {'d': [5, 10, 20]},
            'abs': {'d': [1]},
            'log': {'d': [1]},
            'sign': {'d': [1]},
        }
    
    def register_data(self, df: pd.DataFrame):
        """注册数据"""
        # 基础变量
        self.register_variable('open', df['open'])
        self.register_variable('high', df['high'])
        self.register_variable('low', df['low'])
        self.register_variable('close', df['close'])
        self.register_variable('volume', np.log1p(df['volume']))
        
        # 衍生变量
        df['return'] = df['close'].pct_change()
        df['vwap'] = (df['high'] + df['low'] + df['close'] * 2) / 4
        self.register_variable('return', df['return'])
        self.register_variable('vwap', df['vwap'])
    
    def generate_random_alpha(self, depth: int = 3) -> str:
        """
        随机生成 Alpha 表达式
        
        Args:
            depth: 嵌套深度
            
        Returns:
            Alpha 表达式字符串
        """
        operators = list(self.operators.keys())
        variables = list(self.variables.keys())
        
        def build_expression(current_depth: int) -> str:
            if current_depth >= depth or random.random() < 0.3:
                # 返回变量
                return random.choice(variables)
            
            # 选择算子
            op = random.choice(operators)
            params = self.operator_params[op]
            
            # 构建参数
            param_values = []
            for param_name, param_options in params.items():
                if param_name == 'd':
                    d = random.choice(param_options)
                    param_values.append(str(d))
            
            # 构建子表达式
            if op == 'correlation':
                # 相关性需要两个变量
                sub1 = build_expression(current_depth + 1)
                sub2 = build_expression(current_depth + 1)
                expr = f"{op}({sub1}, {sub2}, {param_values[0]})"
            else:
                sub = build_expression(current_depth + 1)
                if param_values[0] == '1':
                    expr = f"{op}({sub})"
                else:
                    expr = f"{op}({sub}, {param_values[0]})"
            
            return expr
        
        return build_expression(0)
    
    def evaluate_alpha(self, expression: str) -> pd.Series:
        """
        计算 Alpha 表达式
        
        Args:
            expression: Alpha 表达式
            
        Returns:
            Alpha 值序列
        """
        try:
            # 解析并执行表达式
            # 替换表达式中的函数名
            expr = expression
            
            # 逐步计算
            result = self._eval_expression(expr)
            return result
            
        except Exception as e:
            return pd.Series(np.nan, index=list(self.variables.values())[0].index)
    
    def _eval_expression(self, expr: str) -> pd.Series:
        """递归计算表达式"""
        import re
        
        # 检查是否是变量
        for var_name in self.variables.keys():
            if expr.strip() == var_name:
                return self.variables[var_name]
        
        # 检查是否是函数调用
        for op_name in self.operators.keys():
            pattern = rf'{op_name}\((.+)\)'
            match = re.match(pattern, expr.strip())
            if match:
                args_str = match.group(1)
                
                # 分割参数（考虑嵌套括号）
                args = self._parse_args(args_str)
                
                # 递归计算参数
                if op_name == 'correlation':
                    arg1 = self._eval_expression(args[0])
                    arg2 = self._eval_expression(args[1])
                    d = int(args[2])
                    return self.operators[op_name](arg1, arg2, d)
                elif op_name in ['rank', 'scale', 'abs', 'log', 'sign']:
                    arg1 = self._eval_expression(args[0])
                    return self.operators[op_name](arg1)
                else:
                    arg1 = self._eval_expression(args[0])
                    d = int(args[1])
                    return self.operators[op_name](arg1, d)
        
        # 无法解析，返回 NaN
        return pd.Series(np.nan)
    
    def _parse_args(self, args_str: str) -> List[str]:
        """解析函数参数（处理嵌套括号）"""
        args = []
        current_arg = ""
        bracket_count = 0
        
        for char in args_str:
            if char == '(':
                bracket_count += 1
                current_arg += char
            elif char == ')':
                bracket_count -= 1
                current_arg += char
            elif char == ',' and bracket_count == 0:
                args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char
        
        if current_arg.strip():
            args.append(current_arg.strip())
        
        return args
    
    def generate_many(self, n: int = 1000, depth: int = 3) -> List[Dict]:
        """
        批量生成 Alpha
        
        Args:
            n: 生成数量
            depth: 嵌套深度
            
        Returns:
            Alpha 列表，每个包含表达式和名称
        """
        alphas = []
        
        for i in range(n):
            expr = self.generate_random_alpha(depth)
            alphas.append({
                'name': f'alpha_gen_{i+1}',
                'expression': expr
            })
        
        return alphas
