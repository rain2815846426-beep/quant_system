# 一键更新使用说明

## 当前状态

**数据更新策略**: 分批更新（避免网络错误）

**最新日期**: 2026-03-17（部分更新）

---

## 一键更新方法

### 方法 1: 使用更新脚本（推荐）

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 快速更新（前 100 只股票，3-5 分钟）
./update_all.sh
```

**适合**: 每日快速更新

---

### 方法 2: Python 一键更新

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 快速模式（只更新成分股，约 30 分钟）
python3 scripts/quick_update_all.py --fast

# 完整模式（更新全部股票，约 4-6 小时）
python3 scripts/quick_update_all.py --full

# 自定义模式
python3 scripts/quick_update_all.py --batch-size 50 --delay 2
```

**适合**: 
- 快速模式：每日更新
- 完整模式：周末全量更新

---

### 方法 3: Dashboard 一键更新

1. 打开 Dashboard
   ```bash
   ./start_dashboard.sh
   ```

2. 点击侧边栏 **🔄 数据更新**

3. 勾选更新选项：
   - ✅ 更新日线数据
   - ✅ 计算因子
   - ✅ 更新情绪数据

4. 点击 **🚀 开始更新**

5. 在终端运行：
   ```bash
   python3 scripts/quick_update_all.py --fast
   ```

---

## 更新策略说明

### 为什么用分批更新？

**问题**: Akshare 网络不稳定，批量更新会失败

**解决**: 分批更新，每批 50-100 只股票，批次间暂停

### 成功率对比

| 方法 | 成功率 | 时间 | 推荐 |
|------|-------|------|------|
| 全量一次性 | 10-20% | 快 | ❌ 不可用 |
| 分批（延迟 2 秒） | 60-70% | 中 | ✅ 推荐 |
| 分批（延迟 5 秒） | 80-90% | 慢 | ✅ 最稳定 |

---

## 更新频率建议

### 每日更新（推荐）

```bash
# 快速更新前 100 只
./update_all.sh
```

**时间**: 3-5 分钟

**更新内容**:
- 前 100 只股票的 3 月 16-17 日数据
- 最新情绪数据
- 因子计算

---

### 每周更新（周末）

```bash
# 完整更新所有股票
python3 scripts/quick_update_all.py --full --batch-size 50 --delay 2
```

**时间**: 4-6 小时（建议过夜运行）

**更新内容**:
- 全部股票的完整数据
- 所有因子重新计算
- 情绪数据

---

### 后台运行（过夜）

```bash
# 后台运行，日志保存到文件
nohup python3 scripts/quick_update_all.py --full --batch-size 50 --delay 2 > logs/update_all.log 2>&1 &
```

**查看进度**:
```bash
tail -f logs/update_all.log
```

---

## 查看更新进度

### 方法 1: Dashboard 查看

打开 Dashboard → 📊 系统概览 → 查看最新日期

### 方法 2: 命令行查看

```bash
python3 -c "
from src.utils import get_db_connection
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(trade_date) FROM daily_prices')
    latest = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?', (latest,))
    count = cursor.fetchone()[0]
    print(f'最新：{latest}, {count} 只股票')
"
```

### 方法 3: 查看日志

```bash
tail -f logs/update_batch.log
```

---

## 常见问题

### Q: 更新失败怎么办？

A: 重新运行同一批次（会自动跳过已更新的）
```bash
python3 scripts/update_batch.py --batch 1 --size 100 --delay 2
```

### Q: 如何查看哪些股票更新失败了？

A: 查看日志
```bash
grep "失败" logs/update_batch.log | head -20
```

### Q: 更新需要多长时间？

A: 根据模式不同：
- 快速模式（100 只）：3-5 分钟
- 成分股模式（300 只）：15-30 分钟
- 完整模式（5489 只）：4-6 小时

### Q: 可以中断吗？

A: 可以！下次运行会自动跳过已更新的股票

```bash
# 中断后重新运行
python3 scripts/update_batch.py --batch 1 --size 100 --delay 2
```

---

## 最佳实践

### 每日快速更新

```bash
# 早上 9 点前运行
./update_all.sh
```

### 周末完整更新

```bash
# 周六晚上运行（过夜）
nohup python3 scripts/quick_update_all.py --full --batch-size 50 --delay 2 > logs/update_all.log 2>&1 &
```

### 检查更新结果

```bash
# 第二天早上检查
python3 -c "
from src.utils import get_db_connection
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(trade_date) FROM daily_prices')
    latest = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?', (latest,))
    count = cursor.fetchone()[0]
    print(f'✅ 最新：{latest}, {count} 只股票')
"
```

---

## 更新内容说明

### 日线数据

- 开高低收价格
- 成交量/成交额
- 复权因子

### 因子数据

- 动量因子（5/10/20/60 日）
- 波动率因子
- 成交量因子
- RSI 指标

### 情绪数据

- 新闻抓取（东方财富 + 新浪）
- 情绪分析
- 主题识别
- 事件检测

---

## 文件位置

| 文件 | 功能 |
|------|------|
| `update_all.sh` | 一键更新脚本（快速） |
| `scripts/quick_update_all.py` | 一键更新脚本（Python） |
| `scripts/update_batch.py` | 分批更新脚本 |
| `docs/quick_update_guide.md` | 使用说明 |

---

**更新时间**: 2026-03-17  
**策略**: 分批更新（延迟 2 秒，成功率 60-70%）
