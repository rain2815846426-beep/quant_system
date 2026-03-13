# 数据规模与性能评估

## 1. 数据规模估算

### A 股历史日线数据

**参数假设：**
- 股票数量：5,489 只
- 起始日期：2010-01-04
- 结束日期：2026-03-13
- 年数：约 16 年
- 每年交易日：约 240-250 天

**估算：**

| 项目 | 估算值 |
|------|--------|
| 每只股票记录数 | ~3,800 - 4,000 条 |
| 总记录数 | ~20,000,000 - 22,000,000 条 |
| 每条记录大小 | ~200 字节 |
| 日线数据表大小 | ~4 - 5 GB |

### 数据库总体积

| 表名 | 预估记录数 | 预估大小 |
|------|-----------|---------|
| daily_prices | 21,000,000 | 4.5 GB |
| stock_list | 5,489 | < 1 MB |
| financial_data | 50,000 | ~10 MB |
| factor_values | 100,000,000 | ~8 GB |
| index_prices | 50,000 | ~5 MB |
| index_components | 10,000 | ~1 MB |
| industry_classification | 5,489 | < 1 MB |
| predictions | 5,000,000 | ~500 MB |
| **总计** | - | **~13 GB** |

---

## 2. 索引优化

### 已创建的索引

```sql
-- 日线行情表索引
CREATE INDEX idx_prices_code_date ON daily_prices(ts_code, trade_date);

-- 因子值表索引
CREATE INDEX idx_factors_code_date ON factor_values(ts_code, trade_date);
CREATE INDEX idx_factors_name ON factor_values(factor_name);

-- 财务数据索引
CREATE INDEX idx_financial_code ON financial_data(ts_code);

-- 指数数据索引
CREATE INDEX idx_index_code_date ON index_prices(index_code, trade_date);

-- 成分股索引
CREATE INDEX idx_components_index ON index_components(index_code);
CREATE INDEX idx_components_stock ON index_components(ts_code);

-- 行业分类索引
CREATE INDEX idx_industry_code ON industry_classification(ts_code);
```

### 索引效果

| 查询类型 | 无索引 | 有索引 | 提升 |
|---------|-------|-------|------|
| 按股票代码查询 | 全表扫描 | 索引查找 | 100-1000x |
| 按日期范围查询 | 全表扫描 | 索引查找 | 50-100x |
| 代码 + 日期组合 | 全表扫描 | 复合索引 | 500-2000x |

### 建议

✅ 当前索引已足够，无需额外添加

---

## 3. 性能优化建议

### 下载性能

| 优化项 | 当前设置 | 建议 |
|-------|---------|------|
| 批次大小 | 100 只/批 | ✅ 合理 |
| 批次间隔 | 2 秒 | ✅ 合理 |
| 重试次数 | 2 次 | ✅ 合理 |
| 预计下载时间 | 30-60 分钟 | 正常 |

### 查询性能

```python
# ✅ 推荐：使用索引
cursor.execute("""
    SELECT * FROM daily_prices 
    WHERE ts_code = '600519.SH' AND trade_date >= '20250101'
""")

# ❌ 避免：函数操作导致索引失效
cursor.execute("""
    SELECT * FROM daily_prices 
    WHERE SUBSTR(ts_code, 1, 3) = '600'
""")
```

### 写入性能

```python
# ✅ 推荐：批量插入（已实现）
for row in df.iterrows():
    cursor.execute("INSERT ...")
conn.commit()

# ❌ 避免：每条记录都 commit
for row in df.iterrows():
    cursor.execute("INSERT ...")
    conn.commit()
```

---

## 4. 硬件要求

### 最低配置

| 组件 | 要求 |
|------|------|
| CPU | 双核 2.0 GHz |
| 内存 | 4 GB |
| 硬盘 | 20 GB 可用空间 |
| 网络 | 1 Mbps |

### 推荐配置

| 组件 | 要求 |
|------|------|
| CPU | 四核 2.5 GHz+ |
| 内存 | 8 GB+ |
| 硬盘 | 50 GB SSD |
| 网络 | 10 Mbps+ |

---

## 5. 下载时间估算

### 首次全量下载

- 股票数量：5,489 只
- 每只股票耗时：~0.5-1 秒
- 批次间隔：2 秒 × 55 批 = 110 秒
- **总耗时：约 45-60 分钟**

### 每日增量更新

- 更新股票数：5,489 只
- 每只股票新增：1 条记录
- 每只股票耗时：~0.2-0.5 秒
- **总耗时：约 15-30 分钟**

---

## 6. 数据库维护建议

### 定期优化

```bash
# 每月执行一次数据库整理
python3 -c "
import sqlite3
conn = sqlite3.connect('database/quant.db')
conn.execute('VACUUM')
conn.execute('ANALYZE')
conn.close()
"
```

### 数据备份

```bash
# 每周备份数据库
cp database/quant.db database/quant_backup_$(date +%Y%m%d).db
```

---

## 7. 监控指标

### 日常检查

```bash
python3 scripts/check_download_progress.py
```

**关注指标：**
- 下载进度百分比
- 每日新增记录数
- 数据库文件大小
- 查询响应时间

---

## 8. 扩展性考虑

### 未来扩展

如果数据量继续增长（>50 GB），考虑：

1. **数据分区**：按年份或股票代码分区
2. **升级数据库**：迁移到 PostgreSQL
3. **数据压缩**：对历史数据进行压缩存储
4. **缓存层**：添加 Redis 缓存热点数据

### 当前阶段

✅ 现有 SQLite 方案完全满足需求，无需过度设计

---

## 总结

| 项目 | 评估结果 |
|------|---------|
| 数据总量 | ~21,000,000 条日线记录 |
| 数据库体积 | ~13 GB（含因子） |
| 下载时间 | 45-60 分钟（首次） |
| 索引优化 | 已完成，查询性能良好 |
| 硬件要求 | 普通 PC 即可 |
| 扩展方案 | SQLite 足够，无需升级 |
