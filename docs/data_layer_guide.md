# 数据层模块使用说明

## 目录结构

```
src/data_fetch/
├── __init__.py              # 模块导出
├── daily_prices.py          # A 股日线行情数据
├── index_data.py            # 指数行情数据
├── financial_data.py        # 财务数据
├── index_components.py      # 指数成分股
├── industry.py              # 行业分类
├── stock_list.py            # 股票列表
└── download_all.py          # 统一下载入口
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 下载全部数据

```bash
# 从项目根目录执行
python scripts/download_data.py
```

### 3. 更新数据

```bash
# 只获取新增数据（每日收盘后执行）
python scripts/download_data.py --action update
```

### 4. 指定日期范围下载

```bash
python scripts/download_data.py --start_date 20200101 --end_date 20231231
```

## 数据库结构

数据库文件位置：`database/quant.db`

### 表结构

| 表名 | 说明 |
|------|------|
| daily_prices | A 股日线行情 |
| financial_data | 财务指标数据 |
| factor_values | 因子计算结果 |
| predictions | 模型预测结果 |
| index_prices | 指数行情数据 |
| index_components | 指数成分股 |
| industry_classification | 行业分类 |
| stock_list | 股票列表 |

### 主要字段

**daily_prices**
- ts_code: 股票代码（格式：000001.SZ）
- trade_date: 交易日期（格式：20230101）
- open/high/low/close: 开高低收
- volume: 成交量
- turnover: 成交额
- adj_factor: 复权因子

**financial_data**
- ts_code: 股票代码
- report_date: 报告期
- pe/pb: 估值指标
- roe/roa: 盈利能力
- revenue/profit: 营收/利润
- debt_ratio: 资产负债率

## 单独调用 API

```python
from src.data_fetch import (
    fetch_all_daily_prices,
    fetch_index_prices,
    fetch_financial_data,
    fetch_index_components,
    fetch_industry_classification,
)

# 下载所有股票日线数据
fetch_all_daily_prices(start_date="20200101")

# 下载沪深 300 指数数据
fetch_index_prices("000300")

# 下载单只股票财务数据
fetch_financial_data("000001.SZ")

# 下载所有指数成分股
fetch_all_index_components()

# 下载行业分类
fetch_all_industry_classification()
```

## 注意事项

1. **首次下载时间较长**：全市场 5000+ 只股票，日线数据从 2010 年开始，可能需要 30-60 分钟

2. **网络稳定性**：Akshare 依赖网络请求，如遇失败可重新执行

3. **数据更新**：建议每日收盘后（18:00 后）执行更新

4. **磁盘空间**：完整数据约需 500MB-1GB SQLite 数据库文件

## 常见问题

**Q: 下载过程中中断了怎么办？**
A: 重新执行下载命令，已下载的数据会自动跳过

**Q: 某些股票数据获取失败？**
A: 可能是停牌或退市股票，不影响整体数据

**Q: 如何验证数据是否正确？**
A: 可使用 SQLite 工具查看数据库，或用以下代码：

```python
from src.utils import get_db_connection

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM daily_prices")
    print(f"日线数据总量：{cursor.fetchone()[0]}条")
```
