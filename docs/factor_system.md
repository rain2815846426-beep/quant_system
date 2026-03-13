# 因子系统使用说明

## 概述

因子系统用于计算各类量化因子，包括动量、波动率、成交量和技术指标。

---

## 因子列表

| 因子类别 | 因子名称 | 说明 | 计算周期 |
|---------|---------|------|---------|
| **动量因子** | momentum_5 | 5 日收益率 | 5 日 |
| | momentum_20 | 20 日收益率 | 20 日 |
| | momentum_60 | 60 日收益率 | 60 日 |
| **波动率因子** | volatility_20 | 20 日年化波动率 | 20 日 |
| **成交量因子** | volume_mean_20 | 20 日平均成交量 | 20 日 |
| | volume_ratio | 成交量比率 | 20 日 |
| **技术指标** | rsi_14 | 相对强弱指标 | 14 日 |

---

## 使用方法

### 1. 计算全部股票因子

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 计算所有股票的因子
python3 scripts/calculate_factors.py
```

### 2. 限制股票数量（测试用）

```bash
# 只计算前 100 只股票
python3 scripts/calculate_factors.py --limit 100
```

### 3. 指定数据库

```bash
python3 scripts/calculate_factors.py --db /path/to/your/database.db
```

---

## 输出示例

```
Calculating factors: 300 / 1470 stocks
Stock: 000001.SZ
Inserted rows: 256169
```

---

## 因子数据表

**表名**: `factor_values`

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | TEXT | 股票代码 |
| trade_date | TEXT | 交易日期 |
| factor_name | TEXT | 因子名称 |
| factor_value | REAL | 因子值 |

**索引**:
- `(ts_code, trade_date)` - 加速股票 + 日期查询
- `(factor_name)` - 加速因子筛选

---

## 查询示例

### 查询单只股票的因子

```sql
SELECT ts_code, trade_date, factor_name, factor_value
FROM factor_values
WHERE ts_code = '000001.SZ' AND trade_date >= '20260101'
ORDER BY trade_date, factor_name;
```

### 查询某日期的因子排名

```sql
-- 查询 2026-03-13 的 momentum_20 排名前 10
SELECT ts_code, factor_value
FROM factor_values
WHERE trade_date = '20260313' AND factor_name = 'momentum_20'
ORDER BY factor_value DESC
LIMIT 10;
```

### 查询多因子数据

```sql
-- 查询某股票的多因子数据
SELECT trade_date,
    MAX(CASE WHEN factor_name = 'momentum_20' THEN factor_value END) as momentum_20,
    MAX(CASE WHEN factor_name = 'volatility_20' THEN factor_value END) as volatility_20,
    MAX(CASE WHEN factor_name = 'rsi_14' THEN factor_value END) as rsi_14
FROM factor_values
WHERE ts_code = '000001.SZ'
GROUP BY trade_date
ORDER BY trade_date DESC
LIMIT 10;
```

---

## Python 查询示例

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('database/quant.db')

# 查询单只股票的因子时间序列
df = pd.read_sql_query("""
    SELECT ts_code, trade_date, factor_name, factor_value
    FROM factor_values
    WHERE ts_code = '000001.SZ' AND factor_name IN ('momentum_20', 'rsi_14')
    ORDER BY trade_date, factor_name
""", conn)

# 转换为宽格式
df_wide = df.pivot(index=['ts_code', 'trade_date'], columns='factor_name', values='factor_value')
print(df_wide)

conn.close()
```

---

## 因子计算公式

### 动量因子

```
momentum_N = (close_today - close_N_days_ago) / close_N_days_ago * 100
```

### 波动率因子

```
daily_return = close_today / close_yesterday - 1
volatility_20 = std(daily_return_20) * sqrt(252) * 100
```

### 成交量因子

```
volume_mean_20 = mean(volume_20)
volume_ratio = volume_today / volume_mean_20
```

### RSI 因子

```
delta = close_today - close_yesterday
gain = max(delta, 0)
loss = max(-delta, 0)
avg_gain = EMA(gain, 14)
avg_loss = EMA(loss, 14)
RS = avg_gain / avg_loss
RSI = 100 - 100 / (1 + RS)
```

---

## 性能说明

### 计算速度

| 股票数量 | 预计时间 |
|---------|---------|
| 100 只 | ~10 秒 |
| 500 只 | ~30 秒 |
| 1,470 只 | ~2-3 分钟 |

### 内存使用

- 批量处理：每批 100 只股票
- 单次加载：只加载一只股票的数据
- 内存占用：< 500 MB

---

## 注意事项

### 1. 数据不足处理

- 动量 60 需要至少 60 个交易日数据
- 波动率 20 需要至少 20 个交易日数据
- RSI 14 需要至少 14 个交易日数据

数据不足的股票会自动跳过。

### 2. 异常值处理

- 起始位置的因子值可能为 NaN（正常）
- 极端行情可能导致 inf/-inf（已过滤）

### 3. 计算频率

建议：
- 每日收盘后计算一次
- 与数据更新一起执行

---

## 扩展因子

如需添加新因子，在 `src/factors/` 目录下创建新模块：

```python
# src/factors/new_factor.py
import pandas as pd

def calculate_new_factors(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # 计算逻辑
    df['new_factor'] = ...
    return df
```

然后在 `scripts/calculate_factors.py` 中注册使用。

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `src/factors/momentum_factor.py` | 动量因子 |
| `src/factors/volatility_factor.py` | 波动率因子 |
| `src/factors/volume_factor.py` | 成交量因子 |
| `src/factors/rsi_factor.py` | RSI 因子 |
| `scripts/calculate_factors.py` | 因子计算脚本 |
