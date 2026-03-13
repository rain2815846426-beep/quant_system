# A 股量化研究系统 - 项目总结

**项目位置**: `/Users/yuanxiaoyu/Downloads/quant_system`  
**完成日期**: 2026-03-13  
**当前阶段**: Phase 2.5 - 因子研究系统完成

---

## 📊 项目统计

| 项目 | 数量/大小 |
|------|----------|
| Python 脚本 | 30 个 |
| 文档 | 13 个 |
| 数据库 | 8.5 GB |
| 因子记录 | 54,462,369 条 |
| 股票数量 | 2,945 只 |
| 日期范围 | 2010-01-11 至 2026-03-13 |

---

## ✅ 已完成功能

### Phase 1 - 数据层

**功能**:
- ✅ A 股日线数据下载（Akshare）
- ✅ 沪深 300 + 中证 500 + 中证 1000 成分股
- ✅ SQLite 数据库存储
- ✅ 断点续传、分批下载
- ✅ 每日增量更新

**数据**:
- 成分股：1,470 只
- 总股票：2,945 只（含历史数据）
- 日线记录：约 780 万条

**脚本**:
- `scripts/download_index_stocks.py` - 成分股下载
- `scripts/update_daily.py` - 每日更新
- `scripts/check_download_progress.py` - 进度检查

---

### Phase 2 - 因子系统

**功能**:
- ✅ 7 个基础因子计算
- ✅ 批量处理，内存优化
- ✅ 因子数据入库

**因子列表**:
| 类别 | 因子 |
|------|------|
| 动量 | momentum_5, momentum_20, momentum_60 |
| 波动率 | volatility_20 |
| 成交量 | volume_mean_20, volume_ratio |
| 技术指标 | rsi_14 |

**数据**:
- 因子记录：54,462,369 条
- 数据库：8.5 GB

**脚本**:
- `scripts/calculate_factors.py` - 因子计算

---

### Phase 2.5 - 因子研究

**功能**:
- ✅ IC 分析（Pearson 相关系数）
- ✅ RankIC 分析（Spearman 秩相关）
- ✅ 因子分层回测（5 组）
- ✅ 自动批量分析

**分析结果**（前 20 日收益预测）:
| 因子 | IC Mean | IC IR | RankIC IR |
|------|---------|-------|-----------|
| momentum_5 | -0.0114 | -0.0720 | -0.2643 |
| volume_ratio | -0.0280 | -0.4472 | -0.3720 |
| rsi_14 | -0.0198 | -0.1792 | -0.4022 |
| volatility_20 | -0.0254 | -0.0969 | -0.4192 |
| momentum_60 | -0.0239 | -0.1836 | -0.4210 |
| momentum_20 | -0.0308 | -0.2278 | -0.4813 |
| volume_mean_20 | -0.0319 | -0.4464 | -0.6289 |

**脚本**:
- `scripts/analyze_factors.py` - 因子分析
- `src/research/ic_analysis.py` - IC 计算
- `src/research/factor_group_backtest.py` - 分层回测

---

## 📁 目录结构

```
quant_system/
├── config/
│   └── settings.py              # 系统配置
├── src/
│   ├── data_fetch/              # 数据抓取
│   │   ├── daily_prices.py
│   │   ├── index_data.py
│   │   ├── financial_data.py
│   │   ├── index_components.py
│   │   └── industry.py
│   ├── factors/                 # 因子计算
│   │   ├── momentum_factor.py
│   │   ├── volatility_factor.py
│   │   ├── volume_factor.py
│   │   └── rsi_factor.py
│   ├── research/                # 因子研究
│   │   ├── ic_analysis.py
│   │   └── factor_group_backtest.py
│   └── utils/                   # 工具函数
├── scripts/
│   ├── download_index_stocks.py # 成分股下载
│   ├── update_daily.py          # 每日更新
│   ├── check_download_progress.py # 进度检查
│   ├── calculate_factors.py     # 因子计算
│   ├── analyze_factors.py       # 因子分析
│   └── backup.sh                # 备份脚本
├── docs/                        # 文档
│   ├── backup_guide.md          # 备份指南
│   ├── factor_research.md       # 因子研究说明
│   ├── factor_system.md         # 因子系统说明
│   └── dev_log.md               # 开发日志
├── database/
│   └── quant.db                 # SQLite 数据库 (8.5 GB)
├── research_results/
│   └── factor_ic_summary.csv    # IC 分析结果
├── logs/                        # 日志文件
└── requirements.txt             # Python 依赖
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 下载数据

```bash
# 下载成分股数据（2018 年至今）
python3 scripts/download_index_stocks.py
```

### 3. 计算因子

```bash
# 计算所有因子
python3 scripts/calculate_factors.py
```

### 4. 分析因子

```bash
# 分析所有因子 IC
python3 scripts/analyze_factors.py
```

### 5. 查看结果

```bash
cat research_results/factor_ic_summary.csv
```

---

## 💾 保存和备份

### 快速备份（代码 + 文档）

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system
./scripts/backup.sh
```

### Git 版本控制

```bash
git init
git add -A
git commit -m "Quant system Phase 2.5"
```

### 数据库备份

```bash
cp database/quant.db database/quant_backup_$(date +%Y%m%d).db
```

**详细备份指南**: `docs/backup_guide.md`

---

## 📈 核心数据

### 数据库表

| 表名 | 记录数 | 说明 |
|------|--------|------|
| daily_prices | ~7.8M | 日线行情 |
| factor_values | ~54.5M | 因子值 |
| stock_list | 5,489 | 股票列表 |
| index_components | 1,800 | 指数成分股 |

### 因子性能

- **最佳 IC IR**: momentum_5 (-0.07)
- **最佳 RankIC IR**: momentum_5 (-0.26)
- **所有因子 IC 为负** - 可能需要反向使用

---

## 🔧 常用命令

### 数据相关
```bash
# 更新日线数据
python3 scripts/update_daily.py

# 检查下载进度
python3 scripts/check_download_progress.py
```

### 因子相关
```bash
# 计算因子
python3 scripts/calculate_factors.py

# 分析因子
python3 scripts/analyze_factors.py

# 分析单因子
python3 scripts/analyze_factors.py --factor momentum_20
```

### 查询数据
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('database/quant.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM factor_values')
print(f'因子记录：{cursor.fetchone()[0]:,}条')
conn.close()
"
```

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| `README.md` | 项目总览 |
| `docs/backup_guide.md` | 备份指南 ⭐ |
| `docs/factor_research.md` | 因子研究说明 |
| `docs/factor_system.md` | 因子系统说明 |
| `docs/dev_log.md` | 开发日志 |
| `docs/performance_estimation.md` | 性能评估 |

---

## ⏭️ 下一步计划

### Phase 3 - 机器学习模型
- [ ] LightGBM/XGBoost模型
- [ ] 特征工程
- [ ] 预测未来收益
- [ ] 模型评估

### Phase 4 - 策略回测
- [ ] 回测引擎
- [ ] 交易成本模型
- [ ] 绩效评估

### Phase 5 - 可视化
- [ ] Streamlit 仪表盘
- [ ] 因子可视化
- [ ] 策略监控

---

## 📊 当前状态总结

✅ **数据层完成** - 8.5 GB 数据，2945 只股票  
✅ **因子系统完成** - 7 个因子，5400 万记录  
✅ **因子研究完成** - IC 分析工具  
⏳ **机器学习** - 待开发

---

**最后更新**: 2026-03-13  
**项目阶段**: Phase 2.5 完成
