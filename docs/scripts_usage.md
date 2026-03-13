# 数据下载脚本使用说明

## 脚本列表

| 脚本 | 功能 | 执行时间 |
|------|------|---------|
| `download_daily_prices.py` | 下载全部历史数据（优化版） | 45-60 分钟 |
| `update_daily.py` | 每日更新数据 | 15-30 分钟 |
| `check_download_progress.py` | 查看下载进度 | 即时 |

---

## 1. 下载全部历史数据

### 基本用法

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system
python3 scripts/download_daily_prices.py
```

### 指定日期范围

```bash
# 下载 2020 年至今的数据
python3 scripts/download_daily_prices.py --start_date 20200101

# 下载指定日期范围
python3 scripts/download_daily_prices.py --start_date 20200101 --end_date 20231231
```

### 功能特性

✅ **断点续传**：自动跳过已下载的股票  
✅ **分批下载**：每批 100 只股票，降低接口压力  
✅ **自动重试**：失败股票自动重试 2 次  
✅ **进度显示**：实时显示下载进度  

### 输出示例

```
批次 1/55
----------------------------------------------------------------------
Skipping: 1 / 5489 (0.0%) - 000001.SZ (已存在)
Downloading: 2 / 5489 (0.0%) - 000002.SZ - Rows: 3775
Downloading: 3 / 5489 (0.1%) - 000004.SZ - Rows: 3679
...
批次完成，暂停 2 秒...
```

---

## 2. 每日更新数据

### 执行方法

```bash
# 每日收盘后执行（建议 18:00 后）
python3 scripts/update_daily.py
```

### 功能特性

✅ **智能识别**：自动识别每只股票的最新日期  
✅ **增量更新**：只下载新增数据  
✅ **批量处理**：每批 50 只股票  

---

## 3. 查看下载进度

### 执行方法

```bash
python3 scripts/check_download_progress.py
```

### 输出示例

```
======================================================================
  数据下载进度检查
======================================================================

📊 股票统计
  总股票数：     5,489 只
  已下载：       2,500 只
  剩余：         2,989 只
  下载进度：     45.54%

📈 数据量统计
  总记录数：     9,500,000 条
  估算总量：     13,173,600 条
  数据进度：     72.11%

📅 日期范围
  最早日期：     20100104
  最新日期：     20260313
  交易天数：     3,930 天

💾 数据库文件
  数据库路径：   /Users/yuanxiaoyu/Downloads/quant_system/database/quant.db
  文件大小：     2,048.50 MB

📊 下载进度条
  [███████████████████████░░░░░░░░░░░░░░░░░░░░░] 45.5%

⏳ 下载进行中...

💡 提示：继续下载命令
   python3 scripts/download_daily_prices.py
```

---

## 4. 配置说明

### 下载配置（可修改）

在 `scripts/download_daily_prices.py` 中：

```python
BATCH_SIZE = 100    # 每批下载股票数量
BATCH_SLEEP = 2     # 批次间暂停秒数
MAX_RETRIES = 2     # 失败重试次数
```

### 更新配置

在 `scripts/update_daily.py` 中：

```python
BATCH_SIZE = 50     # 每批更新股票数量
BATCH_SLEEP = 2     # 批次间暂停秒数
```

---

## 5. 常见问题

### Q1: 下载中断了怎么办？

A: 重新运行下载命令即可，会自动跳过已下载的股票：

```bash
python3 scripts/download_daily_prices.py
```

### Q2: 如何查看还剩多少股票没下载？

A: 使用进度检查脚本：

```bash
python3 scripts/check_download_progress.py
```

### Q3: 下载速度太慢怎么办？

A: 可以调整批次大小（修改脚本配置）：

```python
BATCH_SIZE = 200    # 增大批次（可能增加失败率）
BATCH_SLEEP = 1     # 减少暂停时间
```

### Q4: 某些股票一直失败怎么办？

A: 可能是停牌或退市股票，不影响整体使用。失败股票会在统计中显示。

### Q5: 数据库文件太大怎么办？

A: 可以定期清理：

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('database/quant.db')
conn.execute('VACUUM')
conn.close()
"
```

---

## 6. 数据验证

### 检查数据完整性

```bash
python3 scripts/check_download_progress.py
```

### 手动查询验证

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('database/quant.db')
cursor = conn.cursor()

# 总记录数
cursor.execute('SELECT COUNT(*) FROM daily_prices')
print(f'总记录数：{cursor.fetchone()[0]:,}')

# 股票数量
cursor.execute('SELECT COUNT(DISTINCT ts_code) FROM daily_prices')
print(f'股票数量：{cursor.fetchone()[0]:,}')

# 日期范围
cursor.execute('SELECT MIN(trade_date), MAX(trade_date) FROM daily_prices')
row = cursor.fetchone()
print(f'日期范围：{row[0]} 至 {row[1]}')

conn.close()
"
```

---

## 7. 预计完成时间

| 场景 | 股票数 | 预计时间 |
|------|-------|---------|
| 首次全量下载 | 5,489 | 45-60 分钟 |
| 下载 50% 数据 | 2,745 | 25-30 分钟 |
| 每日增量更新 | 5,489 | 15-30 分钟 |

---

## 8. 日志文件

下载日志保存在：

```
logs/download_daily.log
logs/daily_update.log
```

查看日志：

```bash
tail -f logs/download_daily.log
```
