# A 股量化选股系统

一个基于 Python 的 A 股量化研究平台，包含数据抓取、因子计算、策略回测、机器学习和 Dashboard 等功能。

## 🎯 系统特点

- **完整的数据层**: 支持 Akshare 和 Tushare 双数据源
- **57 个量化因子**: 动量、波动率、成交量、技术指标等
- **低回撤策略**: 最大回撤控制在 10% 以内
- **机器学习支持**: LightGBM/XGBoost/RandomForest
- **Web Dashboard**: Streamlit 可视化界面
- **消息情绪分析**: 财经新闻抓取和情绪分析

## 📊 当前状态

| 项目 | 状态 |
|------|------|
| 数据层 | ✅ 完成 |
| 因子库 | ✅ 57 个因子 |
| 回测系统 | ✅ 完成（回撤<10%） |
| 机器学习 | ✅ 完成 |
| Dashboard | ✅ 完成 |
| 情绪分析 | ✅ 完成 |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置 Tushare（可选）

```bash
python3 -c "from src.data_fetch.multi_source import set_tushare_token; set_tushare_token('你的 Token')"
```

### 3. 启动 Dashboard

```bash
./start_dashboard.sh
```

### 4. 更新数据

```bash
python3 scripts/update_all_stable.py
```

## 📁 项目结构

```
quant_system/
├── config/                 # 配置文件
├── src/
│   ├── data_fetch/        # 数据抓取
│   ├── factors/           # 因子计算
│   ├── ml/                # 机器学习
│   └── research/          # 因子研究
├── scripts/               # 实用脚本
├── dashboard/             # Dashboard
├── docs/                  # 文档
├── database/              # 数据库（不上传）
└── logs/                  # 日志（不上传）
```

## 📖 文档

- [系统架构](docs/01_system_architecture.md)
- [因子库](docs/02_factor_library.md)
- [Dashboard 使用](docs/dashboard_guide.md)
- [Tushare 配置](docs/tushare_config_guide.md)
- [回测说明](docs/backtest_guide.md)

## 🎯 核心功能

### 数据更新

```bash
# 稳定版更新（推荐）
python3 scripts/update_all_stable.py

# 分批更新
python3 scripts/update_batch.py --batch 1 --size 100
```

### 回测

```bash
# 使用优化参数（回撤<10%）
python3 scripts/backtest_strategy.py

# 自定义参数
python3 scripts/backtest_strategy.py --top_n 20 --position 0.6 --stoploss 0.10 --reverse
```

### 因子分析

```bash
python3 scripts/analyze_factors.py
```

### 机器学习

```bash
python3 scripts/ml_system.py
```

## 📊 策略表现

**低回撤版回测结果**（2020-2026）:

| 指标 | 数值 |
|------|------|
| 年化收益 | 13-15% |
| 最大回撤 | <-10% ✅ |
| 胜率 | 60-65% |
| 夏普比率 | 0.8-1.2 |

## ⚠️ 注意事项

1. **数据更新**: 当前 Akshare 网络不稳定，建议晚上或周末更新
2. **Tushare 积分**: 需要 120 积分才能访问日线接口（签到 12 天可获得）
3. **数据库**: 数据库文件较大（约 8GB），不包含在 Git 仓库中

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

## 📞 联系

如有问题，请通过 Issue 反馈。
