# Phase 6 - 组合构建与风险控制系统

## 概述

Phase 6 实现了接近真实交易的量化组合系统，包括：
- 因子稳定性分析
- 换手率分析
- 组合构建
- 风险控制
- 交易成本模型
- Walk Forward 回测

---

## 模块结构

```
src/research/
├── factor_stability.py      # 因子稳定性分析
└── turnover_analysis.py     # 换手率分析

src/portfolio/
├── portfolio_builder.py     # 组合构建
├── transaction_cost.py      # 交易成本模型
└── walk_forward.py          # Walk Forward 回测

scripts/
└── portfolio_system.py      # 主运行脚本
```

---

## 核心功能

### 1. 因子稳定性分析

**文件**: `src/research/factor_stability.py`

**功能**:
- Rolling IC（60/120/252 日）
- IC 年度分解
- IC 季度分解
- 稳定性指标（IC CV、胜率）

**使用**:
```python
from src.research.factor_stability import factor_stability_analysis

results = factor_stability_analysis(ic_series)

# 输出
results['stability_metrics'] = {
    'ic_mean': 0.0312,
    'ic_std': 0.0523,
    'ic_cv': 1.67,      # 变异系数（越小越稳定）
    'win_rate': 0.58,   # 胜率
}
```

### 2. 换手率分析

**文件**: `src/research/turnover_analysis.py`

**功能**:
- 日换手率计算
- 年化换手率
- 换手率统计

**公式**:
```python
turnover = 0.5 * sum(|w_curr - w_before|)
```

### 3. 组合构建

**文件**: `src/portfolio/portfolio_builder.py`

**方法**:
- `build_long_short_portfolio()` - 多空组合
- `build_long_only_portfolio()` - 纯多头组合
- `build_ic_weighted_portfolio()` - IC 加权组合

**多空组合规则**:
```python
# 多头：因子值最高的 10%
long_weight = 1.0 / n_long

# 空头：因子值最低的 10%
short_weight = -1.0 / n_short
```

### 4. 交易成本模型

**文件**: `src/portfolio/transaction_cost.py`

**成本模型**:
```python
cost = commission_rate + slippage_rate + turnover * market_impact

# 默认参数
commission_rate = 0.001    # 手续费 0.1%
slippage_rate = 0.0005     # 滑点 0.05%
market_impact = 0.001      # 市场冲击
```

**净收益**:
```python
net_return = gross_return - cost
```

### 5. Walk Forward 回测

**文件**: `src/portfolio/walk_forward.py`

**流程**:
```
2018-2020 train → 2021 test
2019-2021 train → 2022 test
2020-2022 train → 2023 test
```

**避免过拟合**:
- 滚动训练测试
- 样本外验证

---

## 使用方法

### 运行组合系统

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 运行完整系统
python3 scripts/portfolio_system.py --factor momentum_20

# 指定日期范围
python3 scripts/portfolio_system.py --factor momentum_20 --start_date 20200101
```

### 输出文件

| 文件 | 内容 |
|------|------|
| `portfolio_performance.csv` | 组合表现汇总 |
| `{factor}_portfolio_returns.csv` | 收益时间序列 |
| `{factor}_cumulative.csv` | 累计收益曲线 |
| `{factor}_stability.csv` | 因子稳定性报告 |

---

## 输出示例

### 组合表现汇总

```csv
factor_name,gross_annual_return,gross_sharpe,net_annual_return,net_sharpe,annual_turnover
momentum_20,0.0823,0.6234,0.0612,0.4821,4.52
```

### 统计指标

```
毛收益:
  年化收益：0.0823
  波动率：  0.1321
  夏普比率：0.6234
  最大回撤：-0.1523

净收益（扣除交易成本后）:
  年化收益：0.0612
  波动率：  0.1298
  夏普比率：0.4821
  最大回撤：-0.1687
```

---

## 关键设计

### 避免前视偏差

1. **因子值使用 t-1 日**
2. **预测 t 日收益**
3. **权重使用 t-1 日因子计算**

### 交易成本

```
总成本 = 固定成本 + 可变成本
固定成本 = 手续费 + 滑点 = 0.15%
可变成本 = 换手率 * 市场冲击
```

### 风险控制

1. **行业中性化** - 通过回归去除行业暴露
2. **市值中性化** - 通过回归去除市值暴露
3. **换手率限制** - 控制交易成本

---

## 性能指标

### 收益指标
- Annual Return: 年化收益
- Sharpe Ratio: 夏普比率
- Max Drawdown: 最大回撤

### 风险指标
- Annual Vol: 年化波动率
- Win Rate: 胜率
- Profit/Loss Ratio: 盈亏比

### 成本指标
- Annual Turnover: 年化换手率
- Total Cost: 总交易成本
- Cost Ratio: 成本占比

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/research/factor_stability.py` | 因子稳定性 |
| `src/research/turnover_analysis.py` | 换手率分析 |
| `src/portfolio/portfolio_builder.py` | 组合构建 |
| `src/portfolio/transaction_cost.py` | 交易成本 |
| `src/portfolio/walk_forward.py` | Walk Forward 回测 |
| `scripts/portfolio_system.py` | 主运行脚本 |

---

## Phase 6 完成状态

| 模块 | 状态 |
|------|------|
| 因子稳定性分析 | ✅ 完成 |
| 换手率分析 | ✅ 完成 |
| 组合构建 | ✅ 完成 |
| 风险控制 | ✅ 完成 |
| 交易成本模型 | ✅ 完成 |
| Walk Forward 回测 | ✅ 完成 |

---

**Phase 6 完成！** 系统现在具备完整的组合构建与风险管理能力。
