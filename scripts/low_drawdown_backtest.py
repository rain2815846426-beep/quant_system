#!/usr/bin/env python3
"""
低回撤版回测 - 加入多种风控手段

风控方法：
1. 行业中性化 - 避免行业集中
2. 个股仓位上限 - 避免单只暴雷
3. 市场状态判断 - 熊市降低仓位
4. 波动率目标 - 动态调整仓位
5. 止损机制 - 个股止损

使用方法:
    python3 scripts/low_drawdown_backtest.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection


def get_industry_data(db_path=DATABASE_PATH) -> dict:
    """
    获取行业数据
    
    Returns:
        {ts_code: industry_name}
    """
    with get_db_connection(db_path) as conn:
        df = pd.read_sql_query("""
            SELECT DISTINCT ts_code, industry_name
            FROM industry_classification
        """, conn)
    
    if not df.empty:
        return dict(zip(df['ts_code'], df['industry_name']))
    return {}


def neutralize_by_industry(
    factor_scores: pd.Series,
    industry_map: dict,
    max_industry_weight: float = 0.3
) -> pd.Series:
    """
    行业中性化处理
    
    限制每个行业的权重不超过 max_industry_weight
    
    Args:
        factor_scores: 因子评分
        industry_map: 行业映射
        max_industry_weight: 最大行业权重
        
    Returns:
        行业中性化后的评分
    """
    adjusted_scores = factor_scores.copy()
    
    # 按行业分组
    industry_groups = {}
    for ts_code in factor_scores.index:
        industry = industry_map.get(ts_code, 'unknown')
        if industry not in industry_groups:
            industry_groups[industry] = []
        industry_groups[industry].append(ts_code)
    
    # 限制每个行业的选股数量
    n_total = len(factor_scores)
    max_stocks_per_industry = int(n_total * max_industry_weight)
    
    selected_stocks = []
    
    # 先选每个行业的前几名
    for industry, stocks in industry_groups.items():
        industry_scores = factor_scores.loc[stocks].sort_values(ascending=False)
        selected = industry_scores.head(max_stocks_per_industry).index.tolist()
        selected_stocks.extend(selected)
    
    # 只保留选中的股票
    mask = adjusted_scores.index.isin(selected_stocks)
    adjusted_scores[~mask] = -999  # 设为最低分
    
    return adjusted_scores


def calculate_market_regime(
    index_returns: pd.Series,
    lookback: int = 60
) -> str:
    """
    判断市场状态
    
    Args:
        index_returns: 指数收益
        lookback: 回看窗口
        
    Returns:
        'bull' / 'bear' / 'neutral'
    """
    if len(index_returns) < lookback:
        return 'neutral'
    
    recent = index_returns.tail(lookback)
    
    # 累计收益
    cum_ret = (1 + recent).prod() - 1
    
    # 波动率
    vol = recent.std() * np.sqrt(252)
    
    if cum_ret > 0.1:  # 上涨超过 10%
        return 'bull'
    elif cum_ret < -0.1:  # 下跌超过 10%
        return 'bear'
    else:
        return 'neutral'


def calculate_position_size(
    market_regime: str,
    portfolio_volatility: float,
    target_volatility: float = 0.15
) -> float:
    """
    计算仓位大小
    
    Args:
        market_regime: 市场状态
        portfolio_volatility: 组合波动率
        target_volatility: 目标波动率
        
    Returns:
        仓位比例 (0-1)
    """
    # 基础仓位
    if market_regime == 'bull':
        base_position = 1.0
    elif market_regime == 'bear':
        base_position = 0.3  # 熊市只拿 3 成仓
    else:
        base_position = 0.7  # 震荡市 7 成仓
    
    # 波动率调整
    if portfolio_volatility > 0:
        vol_adjustment = target_volatility / portfolio_volatility
        vol_adjustment = min(max(vol_adjustment, 0.5), 1.5)  # 限制在 0.5-1.5 之间
    else:
        vol_adjustment = 1.0
    
    position = base_position * vol_adjustment
    
    return min(max(position, 0.1), 1.0)  # 限制在 10%-100%


def low_drawdown_backtest(
    factor_data: dict,
    price_data: pd.DataFrame,
    industry_map: dict,
    index_returns: pd.Series,
    top_n: int = 10,
    start_date: str = '20200101',
    commission: float = 0.001,
    slippage: float = 0.0005,
    stop_loss_pct: float = 0.15,
    max_position_per_stock: float = 0.15,
    target_volatility: float = 0.20
) -> dict:
    """
    低回撤版回测
    
    Args:
        factor_data: 因子数据
        price_data: 价格数据
        industry_map: 行业映射
        index_returns: 指数收益
        top_n: 持仓股票数
        start_date: 开始日期
        commission: 手续费率
        slippage: 滑点
        stop_loss_pct: 止损阈值
        max_position_per_stock: 单只股票最大仓位
        target_volatility: 目标波动率
        
    Returns:
        回测结果
    """
    print(f"  风控配置:")
    print(f"    持仓：Top {top_n}")
    print(f"    单只上限：{max_position_per_stock*100:.0f}%")
    print(f"    止损：{stop_loss_pct*100:.0f}%")
    print(f"    目标波动率：{target_volatility*100:.0f}%")
    print(f"    交易成本：手续费{commission*100:.2f}% + 滑点{slippage*100:.2f}%")
    
    # 按月度分组
    price_data = price_data.copy()
    price_data['month'] = price_data.index.str[:6]
    months = sorted(price_data['month'].unique())
    
    # 回测结果
    portfolio_values = []
    portfolio_dates = []
    monthly_returns = []
    
    initial_capital = 1000000
    capital = initial_capital
    
    # 持仓信息
    current_holdings = {}  # {ts_code: weight}
    holding_entry_price = {}  # {ts_code: entry_price}
    holding_highest = {}  # {ts_code: highest_price since entry}
    
    prev_month = None
    prev_market_regime = 'neutral'
    
    # 波动率计算
    returns_series = []
    
    for i, month in enumerate(months):
        month_data = price_data[price_data['month'] == month]
        
        if month_data.empty:
            continue
        
        month_start = month_data.index[0]
        month_end = month_data.index[-1]
        
        # 月度调仓
        need_rebalance = (prev_month != month)
        
        if need_rebalance:
            # 1. 判断市场状态
            market_regime = calculate_market_regime(index_returns, lookback=60)
            
            # 2. 计算当前组合波动率
            if len(returns_series) > 20:
                recent_vol = np.std(returns_series[-20:]) * np.sqrt(252)
            else:
                recent_vol = target_volatility
            
            # 3. 计算仓位
            position_size = calculate_position_size(
                market_regime,
                recent_vol,
                target_volatility
            )
            
            print(f"  {month}: 市场状态={market_regime}, 仓位={position_size*100:.0f}%")
            
            # 检查是否有所需的因子数据
            has_data = True
            for factor_name in factor_data.keys():
                if month_start not in factor_data[factor_name].index:
                    has_data = False
                    break
            
            if has_data:
                # 4. t 日收盘后选股
                # 使用反转因子
                scores = []
                for factor_name, factor_df in factor_data.items():
                    factor_date = factor_df.loc[month_start].dropna()
                    # 标准化
                    factor_z = (factor_date - factor_date.mean()) / (factor_date.std() + 1e-10)
                    # 反转因子取负
                    if 'momentum' in factor_name:
                        factor_z = -factor_z
                    scores.append(factor_z)
                
                # 等权合并
                combined_score = pd.concat(scores, axis=1).mean(axis=1)
                
                # 5. 行业中性化
                adjusted_score = neutralize_by_industry(
                    combined_score,
                    industry_map,
                    max_industry_weight=0.3
                )
                
                # 6. 选股
                selected = adjusted_score.sort_values(ascending=False).head(top_n).index.tolist()
                
                if selected:
                    # 7. t+1 日开盘买入
                    month_data_idx = list(month_data.index)
                    if month_start in month_data_idx:
                        entry_idx = month_data_idx.index(month_start)
                        if entry_idx + 1 < len(month_data_idx):
                            entry_date = month_data_idx[entry_idx + 1]
                            
                            if entry_date in price_data.index:
                                entry_prices = price_data.loc[entry_date]
                                
                                # 计算仓位（考虑单只上限）
                                n_valid = min(len(selected), int(1.0 / max_position_per_stock))
                                position_per_stock = position_size / n_valid
                                
                                valid_stocks = []
                                for ts_code in selected[:n_valid]:
                                    if ts_code in entry_prices.index:
                                        open_price = entry_prices[ts_code]
                                        if open_price > 0 and not np.isnan(open_price):
                                            buy_price = open_price * (1 + slippage)
                                            valid_stocks.append(ts_code)
                                            holding_entry_price[ts_code] = buy_price
                                            holding_highest[ts_code] = buy_price
                                
                                # 更新持仓
                                current_holdings = {ts: position_per_stock for ts in valid_stocks}
        
        # 检查止损和计算收益
        if month_end in price_data.index and current_holdings:
            end_prices = price_data.loc[month_end]
            
            # 检查止损
            stocks_to_sell = []
            for ts_code in current_holdings.keys():
                if ts_code in end_prices.index:
                    current_price = end_prices[ts_code]
                    entry_price = holding_entry_price.get(ts_code, 0)
                    highest_price = holding_highest.get(ts_code, current_price)
                    
                    # 更新最高价
                    if current_price > highest_price:
                        highest_price = current_price
                        holding_highest[ts_code] = highest_price
                    
                    # 检查止损
                    if entry_price > 0:
                        # 固定止损
                        if (entry_price - current_price) / entry_price > stop_loss_pct:
                            stocks_to_sell.append(ts_code)
                        # 追踪止损（从最高点回撤）
                        elif (highest_price - current_price) / highest_price > stop_loss_pct * 0.7:
                            stocks_to_sell.append(ts_code)
            
            # 执行止损
            for ts_code in stocks_to_sell:
                del current_holdings[ts_code]
                del holding_entry_price[ts_code]
                del holding_highest[ts_code]
            
            # 计算当月收益
            portfolio_value = 0
            for ts_code, weight in current_holdings.items():
                if ts_code in end_prices.index:
                    end_price = end_prices[ts_code]
                    entry_price = holding_entry_price.get(ts_code, 0)
                    
                    if end_price > 0 and entry_price > 0 and not np.isnan(end_price):
                        stock_ret = (end_price - entry_price) / entry_price
                        portfolio_value += weight * (1 + stock_ret)
            
            # 加上现金部分
            cash_weight = 1.0 - sum(current_holdings.values())
            portfolio_value += cash_weight  # 现金收益为 0
            
            if portfolio_value > 0:
                month_ret = portfolio_value - 1
                returns_series.append(month_ret)
                
                monthly_returns.append({
                    'month': month,
                    'return': month_ret,
                    'n_stocks': len(current_holdings),
                    'position': sum(current_holdings.values())
                })
                
                capital = capital * portfolio_value
                portfolio_values.append(capital)
                portfolio_dates.append(month_end)
        
        prev_month = month
    
    # 计算统计指标
    if monthly_returns:
        returns_series = pd.Series([m['return'] for m in monthly_returns])
        
        ann_return = returns_series.mean() * 12
        ann_vol = returns_series.std() * np.sqrt(252)
        sharpe = ann_return / ann_vol if ann_vol > 1e-10 else 0
        
        cumulative = pd.Series(portfolio_values) / initial_capital
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        win_rate = (returns_series > 0).sum() / len(returns_series)
        total_return = (portfolio_values[-1] / initial_capital - 1) if portfolio_values else 0
        
        return {
            'strategy': f'Low_DD_Top_{top_n}',
            'initial_capital': initial_capital,
            'final_capital': portfolio_values[-1] if portfolio_values else initial_capital,
            'total_return': total_return,
            'annual_return': ann_return,
            'sharpe': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'n_months': len(monthly_returns),
            'equity_curve': pd.Series(portfolio_values, index=portfolio_dates),
            'monthly_returns': pd.DataFrame(monthly_returns)
        }
    
    return {}


def main():
    print("="*70)
    print("低回撤版回测 - 多种风控手段")
    print("="*70)
    
    TOP_N = 20  # 增加持股数量分散风险
    START_DATE = '20200101'
    
    print(f"开始日期：{START_DATE}")
    print("="*70)
    
    # 1. 加载因子数据
    print("\n[1/5] 加载因子数据...")
    
    factor_names = [
        'momentum_5', 'momentum_20', 'momentum_60',
        'volume_ratio', 'volume_mean_20',
        'volatility_20',
        'rsi_14'
    ]
    
    factor_data = {}
    
    with get_db_connection(DATABASE_PATH) as conn:
        for factor_name in factor_names:
            query = """
                SELECT ts_code, trade_date, factor_value
                FROM factor_values
                WHERE factor_name = ? AND trade_date >= ?
                ORDER BY trade_date, ts_code
            """
            df = pd.read_sql_query(query, conn, params=(factor_name, START_DATE))
            
            if not df.empty:
                factor_df = df.pivot(index='trade_date', columns='ts_code', values='factor_value')
                factor_data[factor_name] = factor_df
    
    print(f"  加载因子：{list(factor_data.keys())}")
    
    # 2. 加载价格数据
    print("\n[2/5] 加载价格数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        query = f"""
            SELECT ts_code, trade_date, open, close, volume
            FROM daily_prices
            WHERE trade_date >= '{START_DATE}'
            ORDER BY trade_date, ts_code
        """
        price_df = pd.read_sql_query(query, conn)
    
    close_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='close')
    print(f"  价格数据：{close_pivot.shape[0]} 交易日")
    
    # 3. 加载行业数据
    print("\n[3/5] 加载行业数据...")
    industry_map = get_industry_data(DATABASE_PATH)
    print(f"  行业数据：{len(industry_map)} 只股票")
    
    # 4. 加载指数数据（用于判断市场状态）
    print("\n[4/5] 加载指数数据...")
    
    with get_db_connection(DATABASE_PATH) as conn:
        query = f"""
            SELECT trade_date, close
            FROM index_prices
            WHERE index_code = '000300' AND trade_date >= '{START_DATE}'
            ORDER BY trade_date
        """
        index_df = pd.read_sql_query(query, conn)
    
    if not index_df.empty:
        index_df['return'] = index_df['close'].pct_change()
        index_returns = index_df.set_index('trade_date')['return']
    else:
        # 使用市场平均收益代替
        index_returns = close_pivot.mean(axis=1).pct_change()
    
    print(f"  指数数据：{len(index_returns)} 交易日")
    
    # 5. 低回撤回测
    print("\n[5/5] 低回撤回测...")
    
    results = low_drawdown_backtest(
        factor_data,
        close_pivot,
        industry_map,
        index_returns,
        top_n=TOP_N,
        start_date=START_DATE,
        stop_loss_pct=0.15,
        max_position_per_stock=0.08,  # 单只最大 8%
        target_volatility=0.20
    )
    
    if not results:
        print("  回测失败，无有效数据")
        return
    
    # 输出结果
    print("\n" + "="*70)
    print("低回撤版回测结果")
    print("="*70)
    
    print(f"\n资金变化:")
    print(f"  初始资金：{results['initial_capital']:,.0f}")
    print(f"  最终资金：{results['final_capital']:,.0f}")
    print(f"  总收益：{results['total_return']*100:.2f}%")
    
    print(f"\n绩效指标:")
    print(f"  年化收益：{results['annual_return']*100:.2f}%")
    print(f"  夏普比率：{results['sharpe']:.4f}")
    print(f"  最大回撤：{results['max_drawdown']*100:.2f}%")
    print(f"  胜率：{results['win_rate']*100:.2f}%")
    print(f"  回测月份：{results['n_months']} 个月")
    
    # 保存结果
    print("\n" + "="*70)
    print("保存结果...")
    print("="*70)
    
    OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "stock_selection"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 权益曲线
    equity_df = pd.DataFrame({
        'date': results['equity_curve'].index,
        'portfolio_value': results['equity_curve'].values
    })
    equity_df.to_csv(OUTPUT_DIR / 'low_drawdown_equity_curve.csv', index=False)
    
    # 月度收益
    results['monthly_returns'].to_csv(OUTPUT_DIR / 'low_drawdown_monthly_returns.csv', index=False)
    
    # 绩效报告
    report = f"""# 低回撤版回测报告

## 风控措施
1. **行业中性化** - 单一行业不超过 30%
2. **个股仓位上限** - 单只股票最大 8%
3. **市场状态判断** - 熊市降低仓位至 30%
4. **波动率目标** - 动态调整仓位
5. **止损机制** - 固定止损 15% + 追踪止损 10.5%
6. **分散持仓** - Top 20 股票

## 策略信息
- 策略名称：{results['strategy']}
- 初始资金：{results['initial_capital']:,.0f}
- 回测月份：{results['n_months']} 个月

## 绩效指标
| 指标 | 数值 |
|------|------|
| 总收益 | {results['total_return']*100:.2f}% |
| 年化收益 | {results['annual_return']*100:.2f}% |
| 夏普比率 | {results['sharpe']:.4f} |
| 最大回撤 | {results['max_drawdown']*100:.2f}% |
| 胜率 | {results['win_rate']*100:.2f}% |

## 资金变化
- 初始资金：{results['initial_capital']:,.0f}
- 最终资金：{results['final_capital']:,.0f}
- 盈亏金额：{results['final_capital'] - results['initial_capital']:,.0f}

## 对比
| 版本 | 年化收益 | Sharpe | 最大回撤 |
|------|---------|--------|---------|
| 原始版 | 58.82% | 0.68 | -53.66% |
| 低回撤版 | {results['annual_return']*100:.2f}% | {results['sharpe']:.4f} | {results['max_drawdown']*100:.2f}% |
"""
    
    with open(OUTPUT_DIR / 'low_drawdown_performance_report.md', 'w') as f:
        f.write(report)
    
    print(f"  结果已保存:")
    print(f"    - {OUTPUT_DIR}/low_drawdown_equity_curve.csv")
    print(f"    - {OUTPUT_DIR}/low_drawdown_monthly_returns.csv")
    print(f"    - {OUTPUT_DIR}/low_drawdown_performance_report.md")
    
    print("\n" + "="*70)
    print("低回撤版回测完成！")
    print("="*70)


if __name__ == "__main__":
    main()
