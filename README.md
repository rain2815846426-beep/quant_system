# Personal Quant Research Platform – A 股量化研究平台

一个轻量级的个人 A 股量化研究系统，专注于**核心指数成分股**（沪深 300 + 中证 500 + 中证 1000）的数据管理、因子研究、策略回测和机器学习增强。

---

## 🎯 系统定位

**个人 A 股量化研究平台（Quant Research Platform Lite）**

- **数据范围**: 沪深 300 + 中证 500 + 中证 1000 成分股（约 1300 只）
- **时间跨度**: 2018 年至今
- **核心功能**: 数据管理、因子研究、策略回测、机器学习增强
- **技术栈**: Python + SQLite + Akshare + Streamlit

---

## 📁 项目结构

```
quant_system/
├── config/                 # 配置文件
│   └── settings.py
├── src/                    # 核心模块
│   ├── data_fetch/        # 数据抓取
│   ├── data_process/      # 数据处理
│   ├── factors/           # 因子计算（开发中）
│   ├── models/            # 机器学习（开发中）
│   ├── strategy/          # 策略构建（开发中）
│   ├── backtest/          # 回测引擎（开发中）
│   └── utils/             # 工具函数
├── scripts/               # 实用脚本
│   ├── download_index_stocks.py   # 下载成分股数据
│   ├── update_daily.py            # 每日更新
│   └── check_download_progress.py # 进度检查
├── dashboard/             # Streamlit 界面（开发中）
├── tests/                 # 单元测试
├── docs/                  # 文档
├── database/              # SQLite 数据库
├── logs/                  # 日志文件
└── notebooks/             # Jupyter 研究笔记
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 下载数据

```bash
# 下载核心指数成分股数据（沪深 300 + 中证 500 + 中证 1000）
# 时间范围：2018 年至今
# 预计时间：10-15 分钟
python3 scripts/download_index_stocks.py
```

### 3. 查看进度

```bash
# 随时查看下载进度
python3 scripts/check_download_progress.py
```

### 4. 每日更新

```bash
# 每日收盘后执行（建议 18:00 后）
python3 scripts/update_daily.py
```

---

## 📊 数据说明

### 数据范围

| 项目 | 说明 |
|------|------|
| **股票池** | 沪深 300 + 中证 500 + 中证 1000 成分股（约 1300 只） |
| **时间跨度** | 2018-01-01 至今 |
| **数据字段** | 开盘价、最高价、最低价、收盘价、成交量、成交额、复权因子 |
| **数据源** | Akshare（东方财富） |

### 数据库表

| 表名 | 说明 |
|------|------|
| `daily_prices` | A 股日线行情 |
| `stock_list` | 股票列表 |
| `index_prices` | 指数行情 |
| `index_components` | 指数成分股 |
| `financial_data` | 财务数据 |
| `factor_values` | 因子值 |
| `industry_classification` | 行业分类 |
| `predictions` | 模型预测结果 |

---

## 🛠️ 核心功能

### 已实现 ✅

- [x] 数据抓取（Akshare）
- [x] SQLite 数据库存储
- [x] 断点续传下载
- [x] 分批下载优化
- [x] 进度检查工具
- [x] 每日增量更新

### 开发中 🚧

- [ ] 因子计算模块（Phase 2）
- [ ] 机器学习模型（Phase 3）
- [ ] 策略回测引擎（Phase 4）
- [ ] Streamlit 可视化界面（Phase 5）

---

## 📝 使用示例

### 查询数据库

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('database/quant.db')
cursor = conn.cursor()

# 查看数据总量
cursor.execute('SELECT COUNT(*) FROM daily_prices')
print(f'总记录数：{cursor.fetchone()[0]:,}条')

# 查看日期范围
cursor.execute('SELECT MIN(trade_date), MAX(trade_date) FROM daily_prices')
row = cursor.fetchone()
print(f'日期范围：{row[0]} 至 {row[1]}')

conn.close()
"
```

### 查看下载进度

```bash
python3 scripts/check_download_progress.py
```

输出示例：
```
📊 股票统计
  总股票数：     5,489 只
  已下载：       1,300 只
  下载进度：     23.7%

📈 数据量统计
  总记录数：     5,000,000 条
```

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| [docs/scripts_usage.md](docs/scripts_usage.md) | 脚本使用说明 |
| [docs/performance_estimation.md](docs/performance_estimation.md) | 性能评估 |
| [docs/dev_log.md](docs/dev_log.md) | 开发日志 |

---

## 🔧 配置说明

在 `config/settings.py` 中修改配置：

```python
# 数据范围
START_DATE = "20180101"  # 从 2018 年开始

# 下载配置
BATCH_SIZE = 100    # 每批下载股票数量
BATCH_SLEEP = 2     # 批次间暂停秒数
MAX_RETRIES = 2     # 失败重试次数

# 指数代码
INDEX_CODES = {
    "HS300": "000300",      # 沪深 300
    "CSI500": "000905",     # 中证 500
    "CSI1000": "000852",    # 中证 1000
}
```

---

## 💡 优化建议

### 为什么只下载成分股？

1. **代表性强**: 1300 只成分股覆盖 A 股约 70% 市值
2. **流动性好**: 成分股通常是流动性较好的股票
3. **数据质量高**: 大盘股数据更可靠，异常值少
4. **研究效率高**: 数据量小，因子计算和回测速度快
5. **适合个人研究**: 无需全市场数据，聚焦核心股票

### 数据规模对比

| 方案 | 股票数 | 数据量 | 下载时间 | 数据库 |
|------|-------|--------|---------|--------|
| **成分股方案** | ~1,300 只 | ~5M 条 | 10-15 分钟 | ~2-3 GB |
| 全市场方案 | 5,489 只 | ~21M 条 | 45-60 分钟 | ~13 GB |

---

## 📅 开发路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 1** | 数据层（下载 + 存储） | ✅ 完成 |
| **Phase 2** | 因子系统（动量 + 波动率 + 技术指标） | 🚧 进行中 |
| **Phase 3** | 机器学习模型（LightGBM/XGBoost） | ⏳ 待开发 |
| **Phase 4** | 策略回测引擎 | ⏳ 待开发 |
| **Phase 5** | Streamlit 可视化界面 | ⏳ 待开发 |

---

## 🤝 贡献

这是一个个人量化研究项目，主要用于学习和研究。

---

## 📄 License

MIT License

---

## 📧 联系方式

如有问题或建议，欢迎通过 Issue 反馈。
