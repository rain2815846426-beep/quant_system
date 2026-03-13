# Alpha 因子系统（Phase 3）

## 概述

基于 WorldQuant《101 Formulaic Alphas》论文实现的 Alpha 因子计算框架。

---

## 目录结构

```
src/operators/              # Alpha 算子库
├── __init__.py
└── alpha_operators.py      # 核心算子实现

src/alphas/                 # Alpha 因子实现
├── __init__.py
└── worldquant_alphas.py    # Top 10 Alpha

scripts/
└── calculate_alphas.py     # Alpha 计算脚本
```

---

## 核心算子

### 横截面算子

| 算子 | 说明 | 公式 |
|------|------|------|
| `rank(x)` | 横截面排序（百分位） | `x.rank(pct=True)` |
| `cs_rank(x)` | 横截面排序 | 同上 |
| `cs_neutralize(x, group)` | 行业中性化 | 组内标准化 |

### 时间序列算子

| 算子 | 说明 | 公式 |
|------|------|------|
| `delay(x, d)` | 延迟 d 天 | `x.shift(d)` |
| `delta(x, d)` | 差分 | `x - x.shift(d)` |
| `ts_rank(x, d)` | 时间序列排序 | 滚动窗口内排名 |
| `ts_max(x, d)` | 时间序列最大值 | `rolling(d).max()` |
| `ts_min(x, d)` | 时间序列最小值 | `rolling(d).min()` |
| `ts_mean(x, d)` | 时间序列均值 | `rolling(d).mean()` |
| `ts_stddev(x, d)` | 时间序列标准差 | `rolling(d).std()` |

### 统计算子

| 算子 | 说明 | 公式 |
|------|------|------|
| `correlation(x, y, d)` | 滚动相关系数 | `rolling(d).corr()` |
| `covariance(x, y, d)` | 滚动协方差 | `rolling(d).cov()` |

### 数学算子

| 算子 | 说明 | 公式 |
|------|------|------|
| `decay_linear(x, d)` | 线性衰减加权 | WMA |
| `scale(x, target)` | 归一化 | `x * target / sum(|x|)` |
| `signed_power(x, a)` | 带符号幂 | `sign(x) * |x|^a` |
| `abs_value(x)` | 绝对值 | `|x|` |
| `log_value(x)` | 对数 | `log(x)` |
| `indicator(x)` | 指示函数 | `1 if x>0 else 0` |

---

## Top 10 Alpha 因子

### Alpha 1
```python
(rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns,20) : close), 2.), 5)) - 0.5
```

### Alpha 2
```python
((-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6)) * -1
```

### Alpha 3
```python
(-1 * correlation(rank(open), rank(volume), 10))
```

### Alpha 4
```python
(-1 * Ts_Rank(rank(low), 9))
```

### Alpha 5
```python
(rank(open - (sum(vwap, 10) / 10))) * (-1 * abs(rank(close - vwap)))
```

### Alpha 6
```python
(-1 * correlation(open, volume, 10))
```

### Alpha 7
```python
((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1 * 1))
```

### Alpha 8
```python
(-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))))
```

### Alpha 9
```python
((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))
```

### Alpha 10
```python
rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))
```

---

## 使用方法

### 1. 计算 Alpha 因子

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 计算所有股票的 Alpha
python3 scripts/calculate_alphas.py

# 测试：只计算前 100 只股票
python3 scripts/calculate_alphas.py --limit 100
```

### 2. 分析 Alpha IC

```bash
# 分析所有 Alpha 因子的 IC
python3 scripts/analyze_factors.py --forward_period 20
```

### 3. 查看结果

```bash
cat research_results/factor_ic_summary.csv
```

---

## 数据库表

**表名**: `alpha_factors`

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | TEXT | 股票代码 |
| trade_date | TEXT | 交易日期 |
| alpha_1 ~ alpha_10 | REAL | Alpha 因子值 |

**索引**:
- `(ts_code, trade_date)` - 加速股票 + 日期查询

---

## 输出示例

### Alpha 计算输出

```
Calculating alphas: 100 / 2949 (3.4%)
  Stock: 000001.SZ
  Inserted rows: 3860
```

### IC 分析结果

```
================================================================================
因子 IC 分析结果
================================================================================

因子                      IC Mean      IC IR  RankIC Mean    RankIC IR          
--------------------------------------------------------------------------------
alpha_1                  0.0412     0.5823       0.0385       0.5234            
alpha_2                  0.0321     0.4312       0.0298       0.4156            
alpha_3                  0.0285     0.3621       0.0256       0.3489            
...
```

---

## 数据处理

### 停牌处理
- 使用前值填充（ffill）

### 成交量处理
- 对数化：`log1p(volume)`
- 避免极端值影响

### 涨跌停过滤
- 可在分析阶段过滤

---

## 性能优化

### 批量处理
- 每批 100 只股票
- 避免内存溢出

### 向量化计算
- 所有算子使用 pandas 向量化
- 避免循环

### 数据库索引
- `(ts_code, trade_date)` 复合索引
- 加速查询

---

## 扩展 Alpha

### 添加新 Alpha

1. 在 `src/alphas/worldquant_alphas.py` 中实现：

```python
def alpha_11(open_p, high, low, close, volume):
    # 实现逻辑
    return result
```

2. 在 `__init__.py` 中导出：

```python
from .worldquant_alphas import alpha_11
```

3. 在 `calculate_alphas.py` 中注册：

```python
ALPHA_FUNCS = {
    'alpha_11': alpha_11,
    # ...
}
```

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/operators/alpha_operators.py` | 算子实现 |
| `src/alphas/worldquant_alphas.py` | Alpha 因子 |
| `scripts/calculate_alphas.py` | 计算脚本 |

---

## 下一步

1. ✅ 实现 Top 10 Alpha
2. ⏳ 扩展到更多 Alpha（50/101）
3. ⏳ Alpha 组合优化
4. ⏳ 机器学习模型集成

---

**论文参考**: 
[101 Formulaic Alphas](https://arxiv.org/pdf/1601.00991.pdf)
