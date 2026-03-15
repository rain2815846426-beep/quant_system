"""
粒子滤波市场状态判断

原理：
用粒子群估计市场状态（牛市/熊市/震荡市）的概率

简化版实现：
- 3 个状态：bull, bear, neutral
- 100 个粒子
- 观测变量：指数收益率

优势：
- 概率输出而非硬分类
- 更灵敏的状态转换
- 延迟<1 秒

使用：
    from src.risk_control.particle_filter import ParticleFilter
    
    pf = ParticleFilter()
    regime_prob = pf.update(returns)
    # regime_prob['bull'], regime_prob['bear'], regime_prob['neutral']
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


class ParticleFilter:
    """
    粒子滤波器 - 市场状态判断
    
    状态空间：
    - bull: 牛市（高收益低波动）
    - bear: 熊市（低收益高波动）
    - neutral: 震荡市（中等收益波动）
    """
    
    def __init__(
        self,
        n_particles: int = 100,
        seed: int = 42
    ):
        """
        初始化
        
        Args:
            n_particles: 粒子数量
            seed: 随机种子
        """
        self.n_particles = n_particles
        np.random.seed(seed)
        
        # 状态定义
        self.states = ['bull', 'bear', 'neutral']
        
        # 状态转移矩阵（简化：假设状态稳定）
        self.transition_matrix = np.array([
            [0.90, 0.05, 0.05],  # bull → bull/bear/neutral
            [0.05, 0.90, 0.05],  # bear → bull/bear/neutral
            [0.10, 0.10, 0.80]   # neutral → bull/bear/neutral
        ])
        
        # 状态参数（均值和标准差）
        self.state_params = {
            'bull': {'mean': 0.01, 'std': 0.01},      # 牛市：日收益 1%，波动 1%
            'bear': {'mean': -0.01, 'std': 0.02},     # 熊市：日收益 -1%，波动 2%
            'neutral': {'mean': 0.0, 'std': 0.015}    # 震荡：日收益 0%，波动 1.5%
        }
        
        # 初始化粒子权重（均匀分布）
        self.weights = np.ones(n_particles) / n_particles
        
        # 初始化粒子状态
        self.particles = np.random.choice(
            len(self.states),
            size=n_particles,
            p=[1/3, 1/3, 1/3]
        )
        
        # 历史观测
        self.observations = []
    
    def _likelihood(
        self,
        observation: float,
        state: str
    ) -> float:
        """
        计算似然函数 P(observation | state)
        
        假设观测服从正态分布
        """
        params = self.state_params[state]
        mean = params['mean']
        std = params['std']
        
        # 正态分布概率密度
        likelihood = (1.0 / (np.sqrt(2 * np.pi) * std)) * \
                     np.exp(-0.5 * ((observation - mean) / std) ** 2)
        
        return likelihood
    
    def update(
        self,
        observation: float
    ) -> Dict[str, float]:
        """
        更新粒子滤波器
        
        Args:
            observation: 新观测值（日收益率）
            
        Returns:
            状态概率字典 {state: probability}
        """
        self.observations.append(observation)
        
        # 1. 计算权重（似然）
        new_weights = np.zeros(self.n_particles)
        
        for i in range(self.n_particles):
            state = self.states[self.particles[i]]
            likelihood = self._likelihood(observation, state)
            new_weights[i] = self.weights[i] * likelihood
        
        # 2. 归一化权重
        weight_sum = new_weights.sum()
        
        if weight_sum > 1e-10:
            new_weights /= weight_sum
        else:
            # 权重退化，重新初始化
            new_weights = np.ones(self.n_particles) / self.n_particles
        
        # 确保权重和为 1 且长度正确
        new_weights = new_weights / new_weights.sum()  # 再次确保和为 1
        assert len(new_weights) == self.n_particles
        
        self.weights = new_weights
        
        # 3. 重采样（如果有效粒子数太低）
        n_eff = 1.0 / ((self.weights + 1e-10) ** 2).sum()  # 添加小值避免除零
        
        if n_eff < self.n_particles / 2:
            # 系统状态重采样（简化版，避免权重问题）
            # 根据当前概率重新分配粒子
            state_probs = self._get_state_probs()
            probs_array = np.array([state_probs[s] for s in self.states])
            probs_array = probs_array / (probs_array.sum() + 1e-10)  # 确保和为 1
            
            self.particles = np.random.choice(
                len(self.states),
                size=self.n_particles,
                p=probs_array
            )
            self.weights = np.ones(self.n_particles) / self.n_particles
        
        # 4. 状态转移（小概率）
        if np.random.random() < 0.1:  # 10% 概率转移
            for i in range(self.n_particles):
                if np.random.random() < 0.05:  # 5% 转移概率
                    current_state = self.particles[i]
                    transition_probs = self.transition_matrix[current_state]
                    self.particles[i] = np.random.choice(
                        len(self.states),
                        p=transition_probs
                    )
        
        # 5. 计算状态概率
        state_probs = {}
        for i, state in enumerate(self.states):
            mask = self.particles == i
            state_probs[state] = float(self.weights[mask].sum())
        
        return state_probs
    
    def get_regime(self) -> str:
        """
        获取当前市场状态（概率最高的状态）
        
        Returns:
            市场状态字符串
        """
        if not self.observations:
            return 'neutral'
        
        # 使用最新观测计算状态概率
        state_probs = self._get_state_probs()
        return max(state_probs, key=state_probs.get)
    
    def _get_state_probs(self) -> Dict[str, float]:
        """获取当前状态概率"""
        state_probs = {}
        for i, state in enumerate(self.states):
            mask = self.particles == i
            state_probs[state] = self.weights[mask].sum()
        return state_probs
    
    def get_position_size(
        self,
        target_vol: float = 0.20
    ) -> float:
        """
        根据市场状态计算仓位
        
        Args:
            target_vol: 目标波动率
            
        Returns:
            仓位比例 (0-1)
        """
        state_probs = self._get_state_probs()
        
        # 不同状态的基准仓位
        base_positions = {
            'bull': 1.0,       # 牛市满仓
            'neutral': 0.5,    # 震荡市半仓
            'bear': 0.2        # 熊市 2 成仓
        }
        
        # 加权平均仓位
        position = sum(
            state_probs[state] * base_positions[state]
            for state in self.states
        )
        
        # 限制在 20%-100%
        return max(0.2, min(1.0, position))
    
    def reset(self):
        """重置滤波器"""
        self.weights = np.ones(self.n_particles) / self.n_particles
        self.particles = np.random.choice(
            len(self.states),
            size=self.n_particles,
            p=[1/3, 1/3, 1/3]
        )
        self.observations = []


def test_particle_filter():
    """测试粒子滤波器"""
    print("="*70)
    print("粒子滤波器测试")
    print("="*70)
    
    # 创建滤波器
    pf = ParticleFilter(n_particles=100, seed=42)
    
    # 模拟市场数据
    print("\n模拟市场数据测试:")
    print("-"*70)
    
    # 牛市数据
    print("\n牛市阶段（日收益 +1% 左右）:")
    bull_returns = np.random.normal(0.01, 0.01, 20)
    
    for i, ret in enumerate(bull_returns):
        probs = pf.update(ret)
        if (i + 1) % 5 == 0:
            print(f"  第{i+1}天：牛市概率={probs['bull']*100:.1f}%, "
                  f"熊市概率={probs['bear']*100:.1f}%, "
                  f"震荡概率={probs['neutral']*100:.1f}%")
            print(f"  建议仓位：{pf.get_position_size()*100:.0f}%")
    
    # 熊市数据
    print("\n熊市阶段（日收益 -1% 左右）:")
    bear_returns = np.random.normal(-0.01, 0.02, 20)
    
    for i, ret in enumerate(bear_returns):
        probs = pf.update(ret)
        if (i + 1) % 5 == 0:
            print(f"  第{i+1}天：牛市概率={probs['bull']*100:.1f}%, "
                  f"熊市概率={probs['bear']*100:.1f}%, "
                  f"震荡概率={probs['neutral']*100:.1f}%")
            print(f"  建议仓位：{pf.get_position_size()*100:.0f}%")
    
    # 震荡市数据
    print("\n震荡市阶段（日收益 0% 左右）:")
    neutral_returns = np.random.normal(0.0, 0.015, 20)
    
    for i, ret in enumerate(neutral_returns):
        probs = pf.update(ret)
        if (i + 1) % 5 == 0:
            print(f"  第{i+1}天：牛市概率={probs['bull']*100:.1f}%, "
                  f"熊市概率={probs['bear']*100:.1f}%, "
                  f"震荡概率={probs['neutral']*100:.1f}%")
            print(f"  建议仓位：{pf.get_position_size()*100:.0f}%")
    
    print("\n" + "="*70)
    print("测试完成！")
    print("="*70)


if __name__ == "__main__":
    test_particle_filter()
