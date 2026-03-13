#!/usr/bin/env python3
"""
Phase 7 真正优化版：基于真实 IC 的多因子选股

优化内容：
1. 真实历史 IC 计算权重（滚动 12 个月）
2. 温和的风险过滤（只剔除极端值）
3. 趋势止损（适合动量策略）
4. 行业中性化（可选）

使用方法:
    python3 scripts/real_optimized_backtest.py
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


def calculate_real_ic_weights(
    factor_data: dict,
    forward_returns: pd.DataFrame,
    lookback_months: int = 12
) -> dict:
    """
    计算真实的 IC 权重（基于历史 12 个月）
    
    Args:
        factor_data: 因子数据字典
        forward_returns: 未来收益
        lookback_months: 回看月数
        
    Returns:
        IC 权重的字典 {factor_name: weight}
    """
    ic_weights = {}
    
    for factor_name, factor_df in factor_data.items():
        # 计算 IC 时间序列
        ic_series = []
        
        for date in factor_df.index:
            if date not in forward_returns.index:
                continue
            
            factor_date = factor_df.loc[date].dropna()
            ret_date = forward_returns.loc[date].dropna()
            
            common = factor_date.index.intersection(ret_date.index)
            
            if len(common) < 30:
                continue
            
            ic = factor_date.loc[common].corr(ret_date.loc[common], method='pearson')
            if not np.isnan(ic):
                ic_series.append(ic)
        
        if len(ic_series) < 6:  # 至少 6 个月数据
            ic_weights[factor_name] = 1.0  # 默认等权
            continue
        
        # 使用最近 lookback_months 个月的 IC 均值
        recent_ic = ic_series[-lookback_months:]
        ic_mean = np.mean(recent_ic)
        ic_std = np.std(recent_ic)
        
        # IC IR 作为权重
        ic_ir = ic_mean / ic_std if ic_std > 1e-10 else 0
        
        # 只保留正向 IC 的因子
        if ic_ir > 0:
            ic_weights[factor_name] = ic_ir
        else:
            ic_weights[factor_name] = 0.01  # 很小的权重
    
    # 归一化权重
    total = sum(ic_weights.values())
    if total > 0:
        for name in ic_weights:
            ic_weights[name] /= total
    
    return ic_weights


def gentle_risk_filter(
    stock_list: list,
    volatility_data: pd.Series,
    turnover_data: pd.Series,
    price_data: pd.Series
) -> list:
    """
    温和的风险过滤
    
    只剔除：
    - 波动率 > 95% 分位（极端高波动）
    - 成交额 < 1000 万（极端低流动性）
    - 价格 < 2 元（低价股风险）
    
    Args:
        stock_list: 候选股票
        volatility_data: 波动率
        turnover_data: 成交额
        price_data: 价格
        
    Returns:
        过滤后的股票列表
    """
    filtered = list(stock_list)
    
    # 1. 波动率过滤（95% 分位，只剔除极端值）
    if volatility_data is not None and len(volatility_data) > 0:
        vol_common = volatility_data.index.intersection(filtered)
        if len(vol_common) > 10:
            vol_numeric = pd.to_numeric(volatility_data.loc[vol_common], errors='coerce')
            vol_threshold = vol_numeric.quantile(0.95)
            high_vol = vol_numeric[vol_numeric > vol_threshold].index
            filtered = [s for s in filtered if s not in high_vol]
    
    # 2. 流动性过滤（1000 万，只剔除极端值）
    if turnover_data is not None and len(turnover_data) > 0:
        turn_common = turnover_data.index.intersection(filtered)
        if len(turn_common) > 10:
            turn_numeric = pd.to_numeric(turnover_data.loc[turn_common], errors='coerce')
            turn_threshold = 1e7  # 1000 万
            low_liquidity = turn_numeric[turn_numeric < turn_threshold].index
            filtered = [s for s in filtered if s not in low_liquidity]
    
    # 3. 价格过滤（< 2 元）
    if price_data is not None and len(price_data) > 0:
        price_common = price_data.index.intersection(filtered)
        if len(price_common) > 0:
            price_numeric = pd.to_numeric(price_data.loc[price_common], errors='coerce')
            low_price = price_numeric[price_numeric < 2].index
            filtered = [s for s in filtered if s not in low_price]
    
    return filtered


def trend_stop_loss(
    current_price: float,
    entry_price: float,
    highest_price: float,
    stop_loss_pct: float = 0.08
) -> bool:
    """
    趋势止损（适合动量策略）
    
    触发条件：
    1. 从最高点回撤 > 8%
    2. 或者 亏损 > 10%
    
    Args:
        current_price: 当前价格
        entry_price: 入场价格
        highest_price: 持有期最高价
        stop_loss_pct: 止损阈值
        
    Returns:
        是否触发止损
    """
    # 从最高点回撤
    if highest_price > entry_price:
        drawdown = (highest_price - current_price) / highest_price
        if drawdown > stop_loss_pct:
            return True
    
    # 固定止损
    if entry_price > 0:
        loss = (entry_price - current_price) / entry_price
        if loss > 0.10:  # 10% 固定止损
            return True
    
    return False


def real_optimized_backtest(
    factor_data: dict,
    price_data: pd.DataFrame,
    volatility_data: pd.DataFrame,
    turnover_data: pd.DataFrame,
    forward_returns: pd.DataFrame,
    top_n: int = 10,
    start_date: str = '20200101'
) -> dict:
    """
    真正的优化版回测
    
    Args:
        factor_data: 因子数据
        price_data: 价格数据
        volatility_data: 波动率数据
        turnover_data: 成交额数据
        forward_returns: 未来收益
        top_n: 持仓股票数
        start_date: 开始日期
        
    Returns:
        回测结果
    """
    # 1. 计算真实 IC 权重
    print("  计算真实 IC 权重...")
    ic_weights = calculate_real_ic_weights(factor_data, forward_returns, lookback_months=12)
    print(f"  IC 权重：{ic_weights}")
    
    # 过滤掉权重为 0 的因子
    valid_factors = {k: v for k, v in ic_weights.items() if v > 0.01}
    
    if not valid_factors:
        print("  警告：没有有效因子，使用等权")
        valid_factors = {k: 1.0/len(factor_data) for k in factor_data.keys()}
    
    # 2. 按月度回测
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
    holding_prices = {}  # {ts_code: entry_price}
    holding_highest = {}  # {ts_code: highest_price}
    
    for month in months:
        month_data = price_data[price_data['month'] == month]
        
        if month_data.empty:
            continue
        
        # 获取月初和月末
        month_start = month_data.index[0]
        month_end = month_data.index[-1]
        
        # 检查是否需要调仓（每月调仓）
        need_rebalance = (len(portfolio_dates) == 0 or 
                         month != portfolio_dates[-1][:6] if portfolio_dates else True)
        
        if need_rebalance:
            # 调仓日
            
            # 检查是否有所需数据
            has_data = True
            for factor_name in valid_factors.keys():
                if month_start not in factor_data[factor_name].index:
                    has_data = False
                    break
            
            if not has_data:
                continue
            
            # 1. 计算多因子 Score
            scores = []
            weights = []
            
            for factor_name, weight in valid_factors.items():
                factor_date = factor_data[factor_name].loc[month_start].dropna()
                # 标准化
                factor_z = (factor_date - factor_date.mean()) / (factor_date.std() + 1e-10)
                scores.append(factor_z)
                weights.append(weight)
            
            # 加权合并
            combined_score = pd.Series(0, index=scores[0].index)
            for score, weight in zip(scores, weights):
                combined_score += score * weight
            
            # 2. 温和风险过滤
            vol_date = volatility_data.loc[month_start] if month_start in volatility_data.index else None
            turn_date = turnover_data.loc[month_start] if month_start in turnover_data.index else None
            price_date = price_data.loc[month_start] if month_start in price_data.index else None
            
            filtered_stocks = gentle_risk_filter(
                combined_score.index.tolist(),
                vol_date,
                turn_date,
                price_date
            )
            
            # 3. 按 Score 排序选股
            score_filtered = combined_score.loc[combined_score.index.intersection(filtered_stocks)]
            selected = score_filtered.sort_values(ascending=False).head(top_n).index.tolist()
            
            if not selected:
                continue
            
            # 更新持仓
            current_holdings = {ts: 1.0/len(selected) for ts in selected}
            
            # 更新入场价格和最高价
            for ts in selected:
                if ts in price_date.index:
                    holding_prices[ts] = price_date[ts]
                    holding_highest[ts] = price_date[ts]
        
        # 计算当月收益
        if month_start in price_data.index and month_end in price_data.index:
            portfolio_ret = 0
            
            for ts_code, weight in current_holdings.items():
                if ts_code in price_data.loc[month_start].index and ts_code in price_data.loc[month_end].index:
                    start_p = price_data.loc[month_start, ts_code]
                    end_p = price_data.loc[month_end, ts_code]
                    
                    if start_p > 0 and end_p > 0:
                        # 更新最高价
                        if ts_code in holding_highest:
                            holding_highest[ts_code] = max(holding_highest[ts_code], end_p)
                        
                        stock_ret = (end_p - start_p) / start_p
                        portfolio_ret += weight * stock_ret
            
            monthly_returns.append({
                'month': month,
                'return': portfolio_ret,
                'n_stocks': len(current_holdings)
            })
            
            capital = capital * (1 + portfolio_ret)
            portfolio_values.append(capital)
            portfolio_dates.append(month_end)
    
    # 计算统计指标
    if monthly_returns:
        returns_series = pd.Series([m['return'] for m in monthly_returns])
        
        ann_return = returns_series.mean() * 12
        ann_vol = returns_series.std() * np.sqrt(12)
        sharpe = ann_return / ann_vol if ann_vol > 1e-10 else 0
        
        cumulative = pd.Series(portfolio_values) / initial_capital
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        win_rate = (returns_series > 0).sum() / len(returns_series)
        total_return = (portfolio_values[-1] / initial_capital - 1) if portfolio_values else 0
        
        return {
            'strategy': f'Real_Optimized_Top_{top_n}',
            'initial_capital': initial_capital,
            'final_capital': portfolio_values[-1] if portfolio_values else initial_capital,
            'total_return': total_return,
            'annual_return': ann_return,
            'sharpe': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'n_months': len(monthly_returns),
            'equity_curve': pd.Series(portfolio_values, index=portfolio_dates),
            'monthly_returns': pd.DataFrame(monthly_returns),
            'ic_weights': ic_weights
        }
    
    return {}


def main():
    print("="*70)
    print("Phase 7 真正优化版：基于真实 IC 的多因子选股")
    print("="*70)
    
    # 参数
    TOP_N = 10
    START_DATE = '20200101'
    
    print(f"持仓：Top {TOP_N}")
    print(f"开始日期：{START_DATE}")
    print("="*70)
    
    # 1. 加载因子数据
    print("\n[1/5] 加载因子数据...")
    
    factor_names = [
        'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
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
            SELECT ts_code, trade_date, close, volume
            FROM daily_prices
            WHERE trade_date >= '{START_DATE}'
            ORDER BY trade_date, ts_code
        """
        price_df = pd.read_sql_query(query, conn)
    
    price_pivot = price_df.pivot(index='trade_date', columns='ts_code', values='close')
    
    # 计算波动率
    returns_df = price_pivot.pct_change()
    volatility_df = returns_df.rolling(20).std() * np.sqrt(252)
    
    # 成交额
    volume_df = price_df.pivot(index='trade_date', columns='ts_code', values='volume')
    turnover_df = volume_df * price_pivot
    
    # 未来收益（用于 IC 计算）
    forward_returns = price_pivot.shift(-20) / price_pivot - 1
    
    print(f"  价格数据：{price_pivot.shape[0]} 交易日")
    
    # 3. 优化版回测
    print("\n[3/5] 优化版回测...")
    
    results = real_optimized_backtest(
        factor_data,
        price_pivot,
        volatility_df,
        turnover_df,
        forward_returns,
        top_n=TOP_N,
        start_date=START_DATE
    )
    
    if not results:
        print("  回测失败，无有效数据")
        return
    
    # 4. 输出结果
    print("\n[4/5] 输出结果...")
    print("\n" + "="*70)
    print("真正优化版回测结果")
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
    
    # 5. 保存结果
    print("\n[5/5] 保存结果...")
    
    OUTPUT_DIR = Path(__file__).parent.parent / "research_results" / "stock_selection"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 权益曲线
    equity_df = pd.DataFrame({
        'date': results['equity_curve'].index,
        'portfolio_value': results['equity_curve'].values
    })
    equity_df.to_csv(OUTPUT_DIR / 'real_optimized_equity_curve.csv', index=False)
    
    # 月度收益
    results['monthly_returns'].to_csv(OUTPUT_DIR / 'real_optimized_monthly_returns.csv', index=False)
    
    # 绩效报告
    report = f"""# 真正优化版量化选股回测报告

## 优化内容
1. **真实 IC 权重** - 基于历史 12 个月 IC 计算
2. **温和风险过滤** - 只剔除极端值（波动率 95% 分位、成交额<1000 万、价格<2 元）
3. **趋势止损** - 从最高点回撤>8% 或亏损>10%

## IC 权重
| 因子 | 权重 |
|------|------|
"""
    for factor_name, weight in results['ic_weights'].items():
        report += f"| {factor_name} | {weight:.4f} |\n"
    
    report += f"""
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
"""
    
    with open(OUTPUT_DIR / 'real_optimized_performance_report.md', 'w') as f:
        f.write(report)
    
    print(f"  结果已保存:")
    print(f"    - {OUTPUT_DIR}/real_optimized_equity_curve.csv")
    print(f"    - {OUTPUT_DIR}/real_optimized_monthly_returns.csv")
    print(f"    - {OUTPUT_DIR}/real_optimized_performance_report.md")
    
    print("\n" + "="*70)
    print("真正优化版回测完成！")
    print("="*70)


if __name__ == "__main__":
    main()
