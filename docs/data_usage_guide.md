# 数据层使用指南

## 完整运行命令

### 1. 下载全部历史数据

从项目根目录执行：

```bash
# 下载全部 A 股日线数据（从 2010 年开始）
python3 scripts/download_data.py
```

**说明**：
- 首次下载需要 30-60 分钟（5000+ 只股票）
- 数据会自动保存到 `database/quant.db`
- 支持断点续传，中断后重新运行即可

### 2. 查看数据（SQL 查询示例）

```bash
# 使用查询工具
python3 scripts/query_data.py
```

**SQL 查询示例**（手动查询）：

```bash
python3
```

```python
import sqlite3

conn = sqlite3.connect('database/quant.db')
cursor = conn.cursor()

# 查看日线数据前 10 行
cursor.execute("""
    SELECT ts_code, trade_date, open, high, low, close, volume, turnover
    FROM daily_prices
    ORDER BY ts_code, trade_date
    LIMIT 10
""")

for row in cursor.fetchall():
    print(row)

conn.close()
```

**常用查询**：

```sql
-- 查询贵州茅台最近 10 个交易日
SELECT * FROM daily_prices 
WHERE ts_code = '600519.SH' 
ORDER BY trade_date DESC 
LIMIT 10;

-- 查询某日期的所有股票数据
SELECT * FROM daily_prices 
WHERE trade_date = '20260313' 
LIMIT 10;

-- 统计数据总量
SELECT COUNT(*) FROM daily_prices;

-- 查询最新日期
SELECT MAX(trade_date) FROM daily_prices;
```

### 3. 每日更新数据

每日收盘后（建议 18:00 后）执行：

```bash
python3 scripts/update_daily.py
```

**说明**：
- 只下载新增数据（速度快）
- 自动识别每个股票的最新日期
- 同时更新股票列表和指数数据

---

## 脚本说明

| 脚本 | 功能 | 执行时间 |
|------|------|---------|
| `scripts/download_data.py` | 下载全部历史数据 | 30-60 分钟 |
| `scripts/update_daily.py` | 每日更新数据 | 1-5 分钟 |
| `scripts/query_data.py` | 查询数据库状态 | 即时 |
| `tests/test_data_layer.py` | 测试数据层 | 1 分钟 |

---

## 数据库结构

**数据库路径**: `database/quant.db`

### 核心表

| 表名 | 说明 | 记录数 |
|------|------|--------|
| stock_list | 股票列表 | ~5,489 |
| daily_prices | A 股日线行情 | ~13,000,000 |
| financial_data | 财务数据 | - |
| index_prices | 指数行情 | - |
| index_components | 指数成分股 | - |

### daily_prices 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| ts_code | TEXT | 股票代码（000001.SZ） |
| trade_date | TEXT | 交易日期（20260313） |
| open | REAL | 开盘价 |
| high | REAL | 最高价 |
| low | REAL | 最低价 |
| close | REAL | 收盘价 |
| volume | REAL | 成交量 |
| turnover | REAL | 成交额 |
| adj_factor | REAL | 复权因子 |

---

## 数据验证

### 检查数据完整性

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('database/quant.db')
cursor = conn.cursor()

# 股票数量
cursor.execute('SELECT COUNT(*) FROM stock_list')
print(f'股票数量：{cursor.fetchone()[0]}')

# 日线数据量
cursor.execute('SELECT COUNT(*) FROM daily_prices')
print(f'日线数据：{cursor.fetchone()[0]:,}条')

# 最新日期
cursor.execute('SELECT MAX(trade_date) FROM daily_prices')
print(f'最新日期：{cursor.fetchone()[0]}')

# 最早日期
cursor.execute('SELECT MIN(trade_date) FROM daily_prices')
print(f'最早日期：{cursor.fetchone()[0]}')

conn.close()
"
```

### 预期结果

- 股票数量：~5,489 只
- 日线数据：~13,000,000 条（5489 股 × 约 2400 交易日）
- 最早日期：20100104
- 最新日期：当前交易日

---

## 常见问题

### Q1: 下载中断了怎么办？
A: 重新运行 `python3 scripts/download_data.py`，已下载的数据会自动跳过。

### Q2: 某些股票数据获取失败？
A: 可能是停牌或退市股票，不影响整体数据。

### Q3: 如何验证数据是否正确？
A: 运行 `python3 scripts/query_data.py` 查看数据状态。

### Q4: 数据更新频率？
A: 建议每日收盘后（18:00）执行一次 `python3 scripts/update_daily.py`。

### Q5: 数据库文件多大？
A: 完整数据约 500MB-1GB。

---

## 下一步

数据层验证完成后，开始开发 **Phase 2 - 因子系统**：
- 动量因子（5 日、20 日、60 日收益）
- 波动率因子（20 日波动率、ATR）
- 成交量因子
- 技术指标（RSI、MACD、布林带）
- 因子预处理（Z-Score 标准化、中性化）
