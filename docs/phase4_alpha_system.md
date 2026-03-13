# Phase 4 - A 股 Alpha 扩展系统 + 自动 Alpha 生成系统

## 概述

Phase 4 实现了：
1. **50 个 A 股扩展因子**（5 大类）
2. **随机 Alpha 生成器**（暴力尝试）
3. **遗传算法 Alpha 进化**（智能优化）
4. **Alpha 去重和筛选机制**

---

## 目录结构

```
src/factors_extended/       # 扩展因子库
├── __init__.py
├── factor_factory.py       # 因子工厂基类
├── momentum_factors.py     # 动量因子 (10 个)
├── reversal_factors.py     # 反转因子 (10 个)
├── volume_factors.py       # 成交量因子 (10 个)
├── volatility_factors.py   # 波动率因子 (10 个)
└── moneyflow_factors.py    # 资金流因子 (10 个)

src/alpha_engine/           # Alpha 引擎
├── __init__.py
├── alpha_generator.py      # 随机 Alpha 生成器
├── alpha_evaluator.py      # Alpha 评估器
├── alpha_selector.py       # Alpha 选择器
└── genetic_alpha.py        # 遗传算法引擎

scripts/
└── generate_alphas.py      # 主运行脚本
```

---

## 50 个扩展因子

### 1. 动量因子 (10 个)

| 因子 | 说明 | 公式 |
|------|------|------|
| return_1 | 1 日收益 | close.pct_change(1) |
| return_3 | 3 日收益 | close.pct_change(3) |
| return_5 | 5 日收益 | close.pct_change(5) |
| return_10 | 10 日收益 | close.pct_change(10) |
| return_20 | 20 日收益 | close.pct_change(20) |
| momentum_5 | 5 日动量 | 同 return_5 |
| momentum_10 | 10 日动量 | 同 return_10 |
| momentum_20 | 20 日动量 | 同 return_20 |
| momentum_60 | 60 日动量 | close.pct_change(60) |
| price_rank_20 | 20 日价格排名 | close.rolling(20).rank(pct=True) |

### 2. 反转因子 (10 个)

| 因子 | 说明 | 公式 |
|------|------|------|
| reversal_1 | 1 日反转 | -return_1 |
| reversal_3 | 3 日反转 | -return_3 |
| reversal_5 | 5 日反转 | -return_5 |
| short_term_reversal | 短期反转 | -close.pct_change(5) |
| gap_reversal | 跳空反转 | -(open - close.shift(1)) / close.shift(1) |
| overnight_return | 隔夜收益 | (open - close.shift(1)) / close.shift(1) |
| intraday_reversal | 日内反转 | -(close - open) / open |
| high_low_reversal | 高低点反转 | -(high - low) / close |
| volatility_reversal | 波动率反转 | -volatility |
| drawdown_reversal | 回撤反转 | -(close - rolling_max) / rolling_max |

### 3. 成交量因子 (10 个)

| 因子 | 说明 | 公式 |
|------|------|------|
| volume_ratio | 成交量比率 | volume / volume.rolling(5).mean() |
| volume_change | 成交量变化 | volume.pct_change() |
| volume_spike | 成交量突增 | (volume - mean) / std |
| volume_rank_20 | 20 日成交量排名 | volume.rolling(20).rank(pct=True) |
| volume_mean_ratio | 成交量均值比 | vol_5 / vol_20 |
| turnover_rate | 换手率 | volume / volume.rolling(252).mean() |
| turnover_change | 换手率变化 | turnover.pct_change() |
| adv20_ratio | 20 日平均成交量比率 | volume / adv20 |
| volume_volatility | 成交量波动率 | volume.pct_change().std() |
| volume_price_corr | 量价相关性 | volume.rolling(20).corr(close) |

### 4. 波动率因子 (10 个)

| 因子 | 说明 | 公式 |
|------|------|------|
| realized_volatility | 已实现波动率 | return.rolling(20).std() * sqrt(252) |
| downside_volatility | 下行波动率 | downside_return.rolling(20).std() |
| upside_volatility | 上行波动率 | upside_return.rolling(20).std() |
| atr | 平均真实波幅 | tr.rolling(14).mean() |
| price_range | 价格范围 | (high - low) / close |
| high_low_ratio | 高低比率 | high / low |
| volatility_5 | 5 日波动率 | return.rolling(5).std() |
| volatility_10 | 10 日波动率 | return.rolling(10).std() |
| volatility_20 | 20 日波动率 | return.rolling(20).std() |
| volatility_rank | 波动率排名 | volatility.rolling(252).rank(pct=True) |

### 5. 资金流因子 (10 个)

| 因子 | 说明 | 公式 |
|------|------|------|
| money_flow | 资金流 | typical_price * volume |
| price_volume_trend | 价量趋势 | money_flow.rolling(20).sum() |
| volume_weighted_return | 成交量加权收益 | (return * volume).rolling(20).mean() |
| vwap_deviation | VWAP 偏离度 | (close - vwap) / vwap |
| large_trade_ratio | 大单比率 | large_days / 20 |
| accumulation_distribution | 累积分布线 | clv * volume |
| volume_pressure | 成交量压力 | (up_vol - down_vol) / total |
| order_imbalance | 订单不平衡 | position * volume |
| smart_money | 聪明钱 | (up & vol_up).rolling(20).sum() / 20 |
| price_impact | 价格冲击 | return / volume |

---

## Alpha 自动生成系统

### 1. 随机生成器

**算子集合**：
- rank, ts_rank, delta, delay
- correlation, scale, decay_linear
- abs, log, sign

**变量**：
- open, high, low, close, volume
- vwap, return

**生成示例**：
```
rank(ts_rank(close, 5))
rank(delta(volume, 3))
correlation(close, volume, 10)
delay(scale(ts_rank(correlation(close, volume, 5), 5)))
```

### 2. 遗传算法

**流程**：
1. 初始化种群（100 个 Alpha）
2. 评估适应度（IC 作为适应度函数）
3. 选择父代（锦标赛选择）
4. 交叉和变异
5. 迭代进化（5-10 代）

**优势**：
- 智能进化，而非纯随机
- 保留精英个体
- 逐步优化 IC

### 3. 评估和筛选

**评估指标**：
- IC Mean
- RankIC Mean
- IC IR
- RankIC IR

**筛选规则**：
- IC > 0.02
- IC_IR > 0.3
- 去重：去除高度相关的 Alpha

---

## 使用方法

### 运行 Alpha 生成

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 完整运行
python3 scripts/generate_alphas.py

# 指定参数
python3 scripts/generate_alphas.py \
  --n_random 500 \
  --n_genetic 100 \
  --generations 5 \
  --limit_stocks 50
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --n_random | 500 | 随机生成 Alpha 数量 |
| --n_genetic | 100 | 遗传算法种群大小 |
| --generations | 5 | 遗传算法代数 |
| --limit_stocks | 50 | 测试用股票数量 |

---

## 输出文件

| 文件 | 说明 |
|------|------|
| `generated_alphas.csv` | 所有生成的 Alpha 表达式 |
| `alpha_ic_results.csv` | IC 评估结果 |
| `best_alphas.csv` | 筛选后的优质 Alpha |

### 输出示例

**best_alphas.csv**:
```csv
name,expression,ic_mean,rank_ic_mean,ic_ir,rank_ic_ir
alpha_gen_24,close,0.0786,0.0743,1.5725,1.4860
alpha_gen_12,low,0.0743,0.0728,1.4860,1.4568
alpha_gen_70,vwap,0.0728,0.0695,1.4568,1.4235
...
```

---

## 运行示例

```
============================================================
Alpha 生成与分析系统
============================================================
时间：2026-03-13 17:30:00
随机 Alpha 数量：500
遗传算法种群：100 x 5
============================================================

加载数据...
数据量：25,000 条记录，50 只股票

============================================================
随机生成 500 个 Alpha...
============================================================
已生成 500 个 Alpha 表达式
示例：rank(ts_rank(correlation(close, volume, 5), 5))

============================================================
评估 500 个 Alpha...
============================================================
评估进度：50/500
评估进度：100/500
...
完成评估：485 个 Alpha

============================================================
遗传算法进化 Alpha (generations=5, population=100)...
============================================================
Generation 1/5...
Generation 2/5...
...
进化完成，历代最优 Alpha:
  Gen 1: fitness=0.0423, expr=rank(delta(close, 5))...
  Gen 2: fitness=0.0512, expr=correlation(volume, close, 10)...
  Gen 3: fitness=0.0587, expr=scale(ts_rank(return, 20))...

============================================================
保存结果...
============================================================
结果已保存：research_results/alpha_ic_results.csv
结果已保存：research_results/best_alphas.csv

筛选出 87 个优质 Alpha

Top 10 Alpha:
  1. alpha_gen_124: IC=0.0823, IC_IR=1.6452
     表达式：rank(ts_rank(correlation(close, volume, 5), 5))
  2. alpha_gen_87: IC=0.0756, IC_IR=1.5123
     表达式：decay_linear(scale(delta(close, 3)))
  ...

============================================================
完成！
============================================================
```

---

## 系统特点

### 1. 因子工厂模式
- 配置化生成相似因子
- 代码复用，易于扩展

### 2. 随机 + 遗传双模式
- 随机生成：暴力尝试，发现意外之喜
- 遗传算法：智能进化，逐步优化

### 3. Alpha 去重机制
- 避免生成高度相关的 Alpha
- 确保因子多样性

### 4. 向量化计算
- 所有因子使用 pandas 向量化
- 支持批量计算

---

## 下一步扩展

1. ✅ 实现 50 个扩展因子
2. ✅ 随机 Alpha 生成
3. ✅ 遗传算法进化
4. ⏳ 扩展到 100+ 因子
5. ⏳ Alpha 组合优化
6. ⏳ 机器学习模型集成

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/factors_extended/` | 50 个扩展因子 |
| `src/alpha_engine/` | Alpha 生成引擎 |
| `scripts/generate_alphas.py` | 主运行脚本 |
| `research_results/` | 输出结果 |

---

**Phase 4 完成！** 系统现在支持 50+ 基础因子和自动 Alpha 发现功能。
