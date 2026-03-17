# 分批更新使用说明

## 问题原因

**Akshare 网络不稳定**

批量更新时会出现连接错误，原因是：
1. Akshare 服务器限流
2. 请求频率过高
3. 网络波动

## 解决方案：分批更新

### 方法 1: 更新指定批次（推荐）

```bash
# 更新第 1 批（前 100 只股票）
python3 scripts/update_batch.py --batch 1 --size 100 --delay 2

# 更新第 2 批（101-200 只）
python3 scripts/update_batch.py --batch 2 --size 100 --delay 2

# 以此类推...
```

**参数说明**:
- `--batch`: 批次号（从 1 开始）
- `--size`: 每批股票数量（建议 50-100）
- `--delay`: 每只股票间延迟（秒，建议 2-5 秒）

### 方法 2: 自动更新所有批次

```bash
# 更新所有批次（每批 50 只，股票间延迟 2 秒，批次间延迟 60 秒）
python3 scripts/update_batch.py --all --size 50 --delay 2 --batch-delay 60
```

**预计时间**:
- 5489 只股票 ÷ 50 = 110 批
- 每批约 2-3 分钟
- 总时间约 4-6 小时

**建议**: 后台运行，过夜更新

```bash
nohup python3 scripts/update_batch.py --all --size 50 --delay 2 --batch-delay 60 > logs/update_all.log 2>&1 &
```

### 方法 3: 只更新成分股（快速）

```bash
# 只更新沪深 300 成分股（约 300 只）
python3 scripts/update_batch.py --index HS300 --size 50 --delay 2
```

## 成功率优化

### 提高成功率的方法

1. **增加延迟**
   ```bash
   # 延迟 5 秒（更稳定，但更慢）
   python3 scripts/update_batch.py --batch 1 --size 50 --delay 5
   ```

2. **减小批次大小**
   ```bash
   # 每批 20 只（更稳定）
   python3 scripts/update_batch.py --batch 1 --size 20 --delay 2
   ```

3. **多次重试**
   ```bash
   # 失败后重新运行同一批
   python3 scripts/update_batch.py --batch 1 --size 50 --delay 2
   ```

4. **选择网络好的时段**
   - 早上 9-10 点
   - 晚上 8-10 点

## 查看进度

### 查看当前批次

```bash
tail -f logs/update_batch.log
```

### 查看数据库状态

```bash
python3 -c "
from src.utils import get_db_connection
from config.settings import DATABASE_PATH

with get_db_connection(DATABASE_PATH) as conn:
    cursor = conn.cursor()
    
    # 最新日期
    cursor.execute('SELECT MAX(trade_date) FROM daily_prices')
    latest = cursor.fetchone()[0]
    print(f'最新日期：{latest}')
    
    # 该日期的股票数量
    cursor.execute('SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?', (latest,))
    count = cursor.fetchone()[0]
    print(f'{latest} 的股票数量：{count} 只')
"
```

## 失败处理

### 查看失败的股票

```bash
grep "失败" logs/update_batch.log | head -20
```

### 重新更新失败的股票

```bash
# 重新运行同一批（会自动跳过已更新的）
python3 scripts/update_batch.py --batch 1 --size 50 --delay 2
```

## 预计时间

| 批次大小 | 延迟 | 每批时间 | 总批次 | 总时间 |
|---------|------|---------|-------|-------|
| 100 只 | 2 秒 | 3-4 分钟 | 55 批 | 3-4 小时 |
| 50 只 | 2 秒 | 2-3 分钟 | 110 批 | 4-6 小时 |
| 20 只 | 5 秒 | 2-3 分钟 | 275 批 | 9-14 小时 |

## 成功率统计

根据测试：

| 延迟 | 成功率 | 说明 |
|------|-------|------|
| 0 秒 | 30-40% | 不推荐 |
| 2 秒 | 60-70% | 推荐 |
| 5 秒 | 80-90% | 最稳定 |

## 最佳实践

### 日常更新（推荐配置）

```bash
# 每批 100 只，延迟 2 秒
python3 scripts/update_batch.py --batch 1 --size 100 --delay 2
```

### 网络不好时

```bash
# 每批 50 只，延迟 5 秒
python3 scripts/update_batch.py --batch 1 --size 50 --delay 5
```

### 过夜全量更新

```bash
# 后台运行，每批 50 只，延迟 2 秒，批次间延迟 60 秒
nohup python3 scripts/update_batch.py --all --size 50 --delay 2 --batch-delay 60 > logs/update_all.log 2>&1 &
```

## 监控脚本

创建监控脚本 `check_update.sh`:

```bash
#!/bin/bash
echo "=== 数据更新进度 ==="
python3 -c "
from src.utils import get_db_connection
with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(trade_date) FROM daily_prices')
    latest = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM daily_prices WHERE trade_date = ?', (latest,))
    count = cursor.fetchone()[0]
    print(f'最新日期：{latest}')
    print(f'{latest} 的股票数量：{count} 只')
"
```

使用：
```bash
chmod +x check_update.sh
./check_update.sh
```

---

**更新时间**: 2026-03-17  
**状态**: 分批更新可用，建议延迟 2-5 秒
