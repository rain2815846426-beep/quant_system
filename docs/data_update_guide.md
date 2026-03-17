# 数据更新说明

## 当前状态

**数据库最新日期**: 2026-03-17

**数据分布**:
- 2026-03-17: 29 只股票（部分更新）
- 2026-03-16: 29 只股票（部分更新）
- 2026-03-13: 2,943 只股票（完整）
- 2026-03-12: 2,944 只股票（完整）

## 问题原因

**Akshare 网络不稳定**

批量更新时出现大量连接错误：
```
('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**原因**:
1. Akshare 服务器限流
2. 请求频率过高
3. 网络波动

## 解决方案

### 方案 1: 分批次更新（推荐）

将股票分成小批次，每批 50-100 只，批次间暂停：

```bash
# 更新批次 1（前 100 只）
python3 scripts/update_daily_prices.py --batch 1 --batch-size 100

# 等待 5 分钟

# 更新批次 2（101-200 只）
python3 scripts/update_daily_prices.py --batch 2 --batch-size 100
```

### 方案 2: 手动更新重点股票

优先更新成分股和关注的股票：

```bash
# 更新沪深 300 成分股
python3 scripts/update_index_components.py --index HS300
```

### 方案 3: 等待网络恢复

Akshare 网络问题通常是暂时的，可以：
1. 等待 10-30 分钟
2. 重新运行更新脚本
3. 已更新的数据会自动跳过

### 方案 4: 使用其他数据源

如果 Akshare 持续不稳定，可以考虑：
- Tushare（需要 API key）
- 东方财富 API
- 新浪财经 API

## 当前可用功能

虽然批量更新有问题，但以下功能仍然可用：

### ✅ Dashboard 功能
- 系统概览
- 选股推荐
- 模型预测
- 参数分析
- 数据查询
- 消息情绪

### ✅ 已有数据
- 3 月 13 日之前的完整数据（2,943 只股票）
- 3 月 16-17 日的部分数据（29 只股票）

### ✅ 情绪数据
- 情绪指数
- 主题热度
- 新闻明细（最近 7 天）

## 建议操作流程

### 每日例行（推荐）

1. **启动 Dashboard**
   ```bash
   ./start_dashboard.sh
   ```

2. **查看已有数据**
   - Dashboard → 📊 系统概览
   - 查看最新日期和数据量

3. **获取选股推荐**
   - Dashboard → 📈 选股推荐
   - 使用 3 月 13 日数据即可

4. **查看情绪指标**
   - Dashboard → 📰 消息情绪
   - 情绪指数每日更新

### 定期更新（每周一次）

1. **尝试批量更新**
   ```bash
   python3 scripts/update_daily_prices.py
   ```

2. **如果失败，分批次更新**
   ```bash
   # 更新前 100 只
   python3 scripts/update_daily_prices.py --batch 1 --batch-size 100
   
   # 等待 5 分钟，更新下一批
   python3 scripts/update_daily_prices.py --batch 2 --batch-size 100
   ```

3. **更新情绪数据**（这个通常成功）
   ```bash
   python3 scripts/update_news_factors.py
   ```

## 监控网络状态

检查 Akshare 是否可用：

```bash
python3 -c "
import akshare as ak
try:
    df = ak.stock_zh_a_hist(symbol='600519', period='daily', start_date='20260317')
    print(f'✅ Akshare 可用，获取到 {len(df)} 条数据')
except Exception as e:
    print(f'❌ Akshare 不可用：{e}')
"
```

## 数据更新优先级

**优先级 1**（必须更新）:
- 情绪数据（每日）
- 指数数据（每日）

**优先级 2**（建议更新）:
- 沪深 300 成分股
- 中证 500 成分股

**优先级 3**（可选更新）:
- 全市场股票

## 联系支持

如果问题持续，请查看：
- Akshare GitHub: https://github.com/akfamily/akshare
- Akshare 文档：https://akshare.akfamily.xyz/

---

**更新时间**: 2026-03-17  
**状态**: Akshare 网络不稳定，建议分批更新或等待恢复
