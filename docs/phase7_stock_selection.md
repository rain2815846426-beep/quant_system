# Phase 7 - Alpha Ranking 与量化选股系统

## 概述

Phase 7 实现了完整的量化选股系统，核心功能：
1. 从 57 个因子中筛选高质量因子
2. 构建 Alpha Score（股票评分）
3. 对全市场股票进行每日排名
4. 输出 Top N 股票列表
5. 选股策略回测

**重点**：Alpha Ranking + Stock Selection

---

## 系统架构

```
src/factor_processing/     # 因子预处理
├── __init__.py
└── factor_preprocessing.py    # 去极值、标准化

src/research/
└── factor_filter.py           # 因子质量筛选

src/model/
└── alpha_ranking.py           # Alpha Score 计算

src/stock_selection/
└── selector.py                # 股票筛选

src/risk_control/
└── risk_filter.py             # 风险过滤

scripts/
├── run_stock_selection.py     # 主运行脚本
└── backtest_stock_selection.py # 回测脚本
```

---

## 核心模块

### 1. 因子预处理

**文件**: `src/factor_processing/factor_preprocessing.py`

**功能**:
- 去极值（3 种方法）
  - MAD 法
  - Sigma 法（标准差）
  - 分位数法
- 横截面标准化（Z-Score）

**使用**:
```python
from src.factor_processing import process_factor_cross_section

# 单交易日截面处理
processed = process_factor_cross_section(
    factor_series,
    winsorize_method='mad',
    winsorize_nstd=3.0,
    standardize=True
)
```

### 2. 因子质量筛选

**文件**: `src/research/factor_filter.py`

**筛选规则**:
- IC Mean > 0.02
- IC IR > 0.3
- IC Positive Rate > 55%
- 保留 Top 20 因子

**使用**:
```python
from src.research.factor_filter import filter_factors_by_ic

top_factors = filter_factors_by_ic(
    ic_results,
    ic_mean_threshold=0.02,
    ic_ir_threshold=0.3,
    positive_rate_threshold=0.55,
    top_n=20
)
```

### 3. Alpha Ranking 模型

**文件**: `src/model/alpha_ranking.py`

**三种 Score 计算方法**:

#### 等权法
```python
score = mean(zscore(factors))
```

#### IC 加权法
```python
weight_i = IC_i / sum(|IC|)
score = Σ weight_i * factor_i
```

#### 排名平均法
```python
score = mean(rank(factors))
```

**使用**:
```python
from src.model.alpha_ranking import calculate_alpha_score

# 等权
score = calculate_alpha_score(factor_data, method='equal')

# IC 加权
score = calculate_alpha_score(factor_data, method='ic', ic_scores=ic_dict)

# 排名平均
score = calculate_alpha_score(factor_data, method='rank')
```

### 4. 股票筛选系统

**文件**: `src/stock_selection/selector.py`

**功能**:
- 每日对所有股票进行 Alpha Score 排名
- 输出 Top 10 / Top 20 / Top 50

**使用**:
```python
from src.stock_selection.selector import StockSelector

selector = StockSelector(top_n_list=[10, 20, 50])
results = selector.select_top_stocks(alpha_score, date)
```

### 5. 风险过滤

**文件**: `src/risk_control/risk_filter.py`

**过滤规则**:
- 波动率过滤：剔除 > 90% 分位
- 流动性过滤：剔除 日成交额 < 5000 万
- ST 股票过滤

**使用**:
```python
from src.risk_control.risk_filter import RiskFilter

risk_filter = RiskFilter(
    volatility_percentile=0.90,
    min_daily_turnover=5e7,
    filter_st=True
)

filtered = risk_filter.apply_all_filters(stock_data, date)
```

### 6. 选股回测

**文件**: `scripts/backtest_stock_selection.py`

**策略规则**:
- 调仓周期：每月调仓
- 持仓：Top 10 / Top 20
- 权重：等权

**回测指标**:
- 年化收益
- Sharpe 比率
- 最大回撤
- 胜率
- 换手率

---

## 使用方法

### 运行选股系统

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 运行完整选股系统
python3 scripts/run_stock_selection.py

# 指定参数
python3 scripts/run_stock_selection.py --top_n 20 --start_date 20200101
```

### 运行回测

```bash
python3 scripts/backtest_stock_selection.py --top_n 10
```

---

## 输出文件

**目录**: `research_results/stock_selection/`

| 文件 | 内容 |
|------|------|
| `top_stocks_daily.csv` | 每日 Top N 股票列表 |
| `backtest_equity_curve.csv` | 回测权益曲线 |
| `performance_report.md` | 绩效报告 |

### 输出示例

**top_stocks_daily.csv**:
```csv
trade_date,ts_code,alpha_score,rank,top_n
20200102,000001.SZ,2.34,1,10
20200102,000002.SZ,2.12,2,10
...
```

**performance_report.md**:
```markdown
# 量化选股系统绩效报告

## 系统信息
- 运行时间：2026-03-13
- 因子数量：8
- Top N: 10

## 回测结果
- 年化收益：0.0823
- 夏普比率：0.62
- 交易次数：36
```

---

## 完整流程

```
1. 加载因子数据
   ↓
2. 因子预处理（去极值、标准化）
   ↓
3. 计算 Alpha Score（等权/IC 加权/排名平均）
   ↓
4. 股票筛选（Top N）
   ↓
5. 风险过滤（波动率、流动性、ST）
   ↓
6. 回测
   ↓
7. 输出结果
```

---

## 关键设计

### 避免前视偏差

1. **因子值使用 t 日数据**
2. **排名在 t 日收盘后进行**
3. **预测 t+1 日收益**

### 数据质量

1. **去极值**：MAD 法（稳健）
2. **标准化**：Z-Score
3. **缺失值处理**：自动剔除

### 风险控制

1. **波动率过滤**：避免高波动股票
2. **流动性过滤**：避免流动性风险
3. **ST 过滤**：避免问题股票

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/factor_processing/factor_preprocessing.py` | 因子预处理 |
| `src/research/factor_filter.py` | 因子筛选 |
| `src/model/alpha_ranking.py` | Alpha Ranking |
| `src/stock_selection/selector.py` | 股票筛选 |
| `src/risk_control/risk_filter.py` | 风险过滤 |
| `scripts/run_stock_selection.py` | 主运行脚本 |
| `scripts/backtest_stock_selection.py` | 回测脚本 |

---

## Phase 7 完成状态

| 模块 | 状态 |
|------|------|
| 因子预处理 | ✅ 完成 |
| 因子质量筛选 | ✅ 完成 |
| Alpha Ranking 模型 | ✅ 完成 |
| 股票筛选系统 | ✅ 完成 |
| 风险过滤 | ✅ 完成 |
| 选股回测 | ✅ 完成 |

---

**Phase 7 完成！** 系统现在具备完整的量化选股能力，可直接用于实盘选股。
