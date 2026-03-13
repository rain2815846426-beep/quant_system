"""
遗传算法 Alpha 引擎

通过进化方式发现优质 Alpha
"""
import random
import pandas as pd
import numpy as np
from typing import List, Dict
from .alpha_generator import RandomAlphaGenerator


class GeneticAlphaEngine:
    """遗传算法 Alpha 引擎"""
    
    def __init__(self, population_size: int = 100, mutation_rate: float = 0.1):
        """
        初始化
        
        Args:
            population_size: 种群大小
            mutation_rate: 变异率
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.generator = RandomAlphaGenerator()
        self.population = []
        self.fitness = []
    
    def initialize_population(self, df: pd.DataFrame, n: int = 100):
        """初始化种群"""
        self.generator.register_data(df)
        self.population = self.generator.generate_many(n, depth=3)
        self.fitness = [0] * n
    
    def evaluate_fitness(self, df: pd.DataFrame) -> List[float]:
        """
        评估适应度
        
        使用 IC 作为适应度函数
        """
        fitness = []
        
        # 计算未来收益
        forward_returns = df.groupby('ts_code')['close'].transform(
            lambda x: x.shift(-20) / x - 1
        ) * 100
        
        for alpha_info in self.population:
            try:
                expr = alpha_info['expression']
                alpha_values = self.generator.evaluate_alpha(expr)
                
                # 计算 IC
                ic_by_date = []
                for date in alpha_values['trade_date'].unique():
                    date_mask = alpha_values['trade_date'] == date
                    alpha_date = alpha_values.loc[date_mask, 'alpha_value']
                    ret_date = forward_returns[forward_returns.index.get_level_values('trade_date') == date]
                    
                    if len(alpha_date) > 30 and len(ret_date) > 30:
                        ic = alpha_date.corr(ret_date, method='pearson')
                        ic_by_date.append(ic)
                
                fitness_score = np.mean(ic_by_date) if ic_by_date else 0
                fitness.append(abs(fitness_score))  # 使用绝对值
                
            except Exception as e:
                fitness.append(0)
        
        self.fitness = fitness
        return fitness
    
    def select_parents(self, n_parents: int = 20) -> List[Dict]:
        """选择父代（锦标赛选择）"""
        parents = []
        
        for _ in range(n_parents):
            # 随机选择 3 个个体
            indices = random.sample(range(len(self.population)), 3)
            
            # 选择适应度最高的
            best_idx = max(indices, key=lambda i: self.fitness[i])
            parents.append(self.population[best_idx])
        
        return parents
    
    def crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """交叉"""
        # 随机选择父代 1 或父代 2 的表达式
        if random.random() < 0.5:
            return {'name': f'alpha_cross_{random.randint(1, 10000)}', 'expression': parent1['expression']}
        else:
            return {'name': f'alpha_cross_{random.randint(1, 10000)}', 'expression': parent2['expression']}
    
    def mutate(self, alpha: Dict) -> Dict:
        """变异"""
        if random.random() < self.mutation_rate:
            # 生成新的 Alpha
            return self.generator.generate_random_alpha(depth=3)
        return alpha['expression']
    
    def evolve(self, df: pd.DataFrame, generations: int = 10) -> List[Dict]:
        """
        进化
        
        Args:
            df: 数据 DataFrame
            generations: 进化代数
            
        Returns:
            最优 Alpha 列表
        """
        # 初始化
        self.initialize_population(df, self.population_size)
        
        best_alphas = []
        
        for gen in range(generations):
            print(f"Generation {gen + 1}/{generations}...")
            
            # 评估
            self.evaluate_fitness(df)
            
            # 记录当代最优
            best_idx = np.argmax(self.fitness)
            best_alphas.append({
                'generation': gen + 1,
                'expression': self.population[best_idx]['expression'],
                'fitness': self.fitness[best_idx]
            })
            
            # 选择
            parents = self.select_parents(n_parents=self.population_size // 5)
            
            # 生成新一代
            new_population = []
            
            # 保留精英（前 10%）
            elite_count = self.population_size // 10
            elite_indices = np.argsort(self.fitness)[-elite_count:]
            for idx in elite_indices:
                new_population.append(self.population[idx])
            
            # 交叉和变异产生剩余个体
            while len(new_population) < self.population_size:
                parent1 = random.choice(parents)
                parent2 = random.choice(parents)
                
                child_expr = self.crossover(parent1, parent2)['expression']
                child_expr = self.mutate({'expression': child_expr})
                
                new_population.append({
                    'name': f'alpha_gen{gen + 1}_{len(new_population)}',
                    'expression': child_expr
                })
            
            self.population = new_population
        
        # 返回历代最优
        return best_alphas
