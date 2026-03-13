# Phase 5 - Factor Evaluation & Portfolio System

## 关键设计原则：避免前视偏差（Look-ahead Bias）

### 什么是前视偏差？

前视偏差是指在预测时使用了未来数据，导致：
- IC 虚高
- 回测结果过于乐观
- 实盘失效

**错误示例**：
```python
# ❌ 错误：使用了 t 日的收盘价计算 t 日的因子，然后预测 t 日收益
factor[t] = close[t] / close[t-1]  # 包含 t 日信息
return[t] = close[t] / close[t-1] - 1  # 这是已知的答案！
IC = corr(factor[t], return[t])  # 虚假的高相关性
```

**正确做法**：
```python
# ✅ 正确：t 日的因子只能使用 t-1 及之前的信息
factor[t-1] = close[t-1] / close[t-20]  # t-1 日已知
return[t] = close[t] / close[t-1] - 1  # t 日收益
IC = corr(factor[t-1], return[t])  # 真正的预测能力
```

---

## 系统实现

### 1. 因子预处理（截面处理）

**文件**: `src/factor_pipeline/factor_cleaner.py`

**关键**：所有处理只使用截面数据（同一交易日）

```python
# t 日的因子处理流程
def process_factor_today(factor_values_t, industry_t, log_mv_t):
    # 1. 去极值（截面）- 只使用 t 日的数据
    factor_clean = winsorize(factor_values_t, method='mad')
    
    # 2. 标准化（截面）- 只使用 t 日的均值和标准差
    factor_standard = zscore(factor_clean)
    
    # 3. 中性化（截面）- 只使用 t 日的行业和市值
    factor_neutral = neutralize(factor_standard, industry_t, log_mv_t)
    
    return factor_neutral
```

**实现函数**：
- `winsorize_factor()` - MAD 或 3σ去极值
- `zscore_factor()` - 截面标准化
- `neutralize_factor()` - 行业市值中性化

---

### 2. 未来收益计算（正确的时间对齐）

**文件**: `src/factor_pipeline/factor_returns.py`

```python
def calculate_forward_returns(close_prices, periods=[1, 5, 10, 20]):
    """
    计算未来收益
    
    forward_return[t, period] = (price[t+period] - price[t]) / price[t]
    
    这是 t 日因子要预测的目标
    """
    forward_returns = {}
    for period in periods:
        # 使用 shift(-period) 获取未来价格
        returns = close_prices.shift(-period) / close_prices - 1
        forward_returns[period] = returns
    return forward_returns
```

**时间对齐**：
```
t 日的因子值  →  预测  →  t+1 到 t+20 的收益
factor[t]               forward_return[t]
```

---

### 3. IC 计算（截面相关性）

**文件**: `src/factor_pipeline/factor_returns.py`

```python
def calculate_ic_time_series(factor_values, forward_returns, method='pearson'):
    """
    计算 IC 时间序列
    
    每个交易日计算一次截面相关性：
    IC[t] = corr(factor[t], forward_return[t])
    
    其中：
    - factor[t] 是 t 日的因子值（截面）
    - forward_return[t] 是 t 日因子预测的未来收益
    """
    ic_series = []
    
    for date in common_dates:
        # 获取 t 日的因子值和未来收益（都是截面数据）
        factor_date = factor_values.loc[date]
        ret_date = forward_returns.loc[date]
        
        # 计算相关性
        ic = factor_date.corr(ret_date, method=method)
        ic_series.append(ic)
    
    return pd.Series(ic_series, index=dates)
```

**IC 统计指标**：
- IC Mean：平均 IC
- IC Std：IC 标准差
- IC IR：IC / IC Std
- T-stat：显著性检验
- P-value：p 值

---

### 4. 分层回测（避免前视偏差）

**文件**: `src/factor_pipeline/factor_backtest.py`

```python
def factor_group_backtest(factor_values, forward_returns, n_groups=5):
    """
    分层回测
    
    每日按因子值分组，计算各组未来收益
    """
    for date in dates:
        # t 日按因子值分组
        factor_date = factor_values.loc[date]
        groups = pd.qcut(factor_date, q=n_groups, labels=False)
        
        # 计算各组未来收益
        for g in range(n_groups):
            group_stocks = groups[groups == g].index
            group_return = forward_returns.loc[date, group_stocks].mean()
```

**分组**：
- Q1: 因子值最低 20%
- Q2: 20%-40%
- Q3: 40%-60%
- Q4: 60%-80%
- Q5: 因子值最高 20%

**多空组合**：Long Q5 - Short Q1

---

### 5. 多因子组合

**文件**: `src/factor_pipeline/factor_combiner.py`

**方法**：
1. **等权组合**：各因子权重相同
2. **IC 加权**：IC_IR 高的因子权重高

```python
def combine_factors_ic_weighted(factor_data, ic_scores, factor_names):
    """IC 加权组合"""
    # 计算权重
    weights = {name: abs(ic_scores[name]) for name in factor_names}
    total_ic = sum(weights.values())
    
    # 归一化
    for name in weights:
        weights[name] /= total_ic
    
    # 加权组合
    combined = sum(factor_data[name] * weights[name] for name in factor_names)
    return combined
```

---

## 使用方法

### 运行因子评估

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 评估单个因子
python3 scripts/factor_evaluation.py --factor momentum_20

# 指定日期范围
python3 scripts/factor_evaluation.py --factor momentum_20 --start_date 20200101
```

### 输出文件

| 文件 | 内容 |
|------|------|
| `{factor}_ic_timeseries.csv` | IC 时间序列 |
| `factor_backtest_summary.csv` | IC 统计汇总 |
| `{factor}_group_returns.csv` | 分层收益 |
| `{factor}_cumulative.csv` | 累计收益曲线 |

---

## 输出示例

### IC 统计结果

```
IC 统计结果:
  IC Mean:    0.0312
  IC Std:     0.0523
  IC IR:      0.5966
  IC T-stat:  4.2341
  IC P-value: 0.000023
  样本数：     1986

RankIC 统计结果:
  RankIC Mean: 0.0285
  RankIC IR:   0.5421
```

### 分层回测结果

```
各组表现:
       annual_return  annual_vol  sharpe  max_drawdown
Q1         -0.0523      0.1823   -0.287      -0.3521
Q2         -0.0234      0.1756   -0.133      -0.2845
Q3          0.0123      0.1698    0.072      -0.2234
Q4          0.0345      0.1712    0.201      -0.1987
Q5          0.0678      0.1789    0.379      -0.1756
Long_Short  0.1201      0.0823    1.459      -0.0923
```

---

## 关键检查清单

### ✅ 避免前视偏差

- [x] 因子计算只使用 t 日及之前的数据
- [x] 去极值使用截面数据（t 日）
- [x] 标准化使用截面均值和标准差（t 日）
- [x] 中性化使用 t 日的行业和市值
- [x] IC 计算是 t 日因子与未来收益的相关性
- [x] 分层回测使用 t 日的因子值分组

### ✅ 数据对齐

```
t-1 日：计算因子值 factor[t-1]
  ↓
t 日：因子值用于预测 t 日到 t+N 日的收益
  ↓
t+N 日：实现收益 return[t]
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/factor_pipeline/factor_cleaner.py` | 因子清洗 |
| `src/factor_pipeline/factor_returns.py` | 收益和 IC 计算 |
| `src/factor_pipeline/factor_backtest.py` | 分层回测 |
| `src/factor_pipeline/factor_combiner.py` | 多因子组合 |
| `scripts/factor_evaluation.py` | 主运行脚本 |

---

## Phase 5 完成状态

| 模块 | 状态 |
|------|------|
| 因子预处理 | ✅ 完成 |
| IC 计算（避免前视偏差） | ✅ 完成 |
| 分层回测 | ✅ 完成 |
| 多因子组合 | ✅ 完成 |
| 运行脚本 | ✅ 完成 |

---

**Phase 5 完成！** 系统现在具备严谨的因子评估能力，避免了前视偏差。
