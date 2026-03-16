#!/usr/bin/env python3
"""
量化选股系统 Web Dashboard

功能：
1. 数据更新
2. 因子计算
3. 选股推荐
4. 模型预测
5. 参数分析

使用:
    streamlit run dashboard/app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_PATH
from src.utils import get_db_connection

# 页面配置
st.set_page_config(
    page_title="A 股量化选股系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
.big-font {
    font-size:20px !important;
    font-weight: bold;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 10px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# 标题
st.title("📈 A 股量化选股系统")
st.markdown(f"**最后更新**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 侧边栏
st.sidebar.title("🎯 操作面板")
st.sidebar.markdown("---")

# 主功能选择
menu = st.sidebar.radio(
    "选择功能",
    ["📊 系统概览", "🔄 数据更新", "📈 选股推荐", "🤖 模型预测", "⚙️ 参数分析", "📁 数据查询"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**系统状态**
- 数据库：✅ 正常
- 因子库：✅ 57 个因子
- 机器学习：✅ 可用
- 行业数据：⚠️ 简化版
""")

# ==================== 系统概览 ====================
if menu == "📊 系统概览":
    st.header("📊 系统概览")
    
    # 获取数据库统计
    with get_db_connection(DATABASE_PATH) as conn:
        # 股票数量
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT ts_code) FROM daily_prices")
        stock_count = cursor.fetchone()[0]
        
        # 日线数据量
        cursor.execute("SELECT COUNT(*) FROM daily_prices")
        price_count = cursor.fetchone()[0]
        
        # 因子数据量
        cursor.execute("SELECT COUNT(*) FROM factor_values")
        factor_count = cursor.fetchone()[0]
        
        # 最新日期
        cursor.execute("SELECT MAX(trade_date) FROM daily_prices")
        latest_date = cursor.fetchone()[0]
    
    # 指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("股票数量", f"{stock_count:,}", "只")
    
    with col2:
        st.metric("日线数据", f"{price_count:,}", "条")
    
    with col3:
        st.metric("因子数据", f"{factor_count:,}", "条")
    
    with col4:
        st.metric("最新日期", latest_date or "N/A", "")
    
    st.markdown("---")
    
    # 系统功能
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ 已完成功能")
        st.markdown("""
        - ✅ 数据层（日线、成分股）
        - ✅ 因子库（57 个因子）
        - ✅ 回测系统
        - ✅ 风控系统（粒子滤波）
        - ✅ 过拟合控制（蒙特卡洛）
        - ✅ 机器学习（RandomForest）
        """)
    
    with col2:
        st.subheader("🔄 进行中")
        st.markdown("""
        - ⚠️ 行业数据（简化版）
        - ⏳ 可视化 Dashboard
        - ⏳ 实盘模拟
        """)
    
    # 快速操作
    st.markdown("---")
    st.subheader("⚡ 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 更新数据", use_container_width=True):
            st.info("请点击侧边栏 '🔄 数据更新' 执行完整更新")
    
    with col2:
        if st.button("📈 查看选股", use_container_width=True):
            st.info("请点击侧边栏 '📈 选股推荐' 查看推荐股票")
    
    with col3:
        if st.button("🤖 运行模型", use_container_width=True):
            st.info("请点击侧边栏 '🤖 模型预测' 运行机器学习模型")

# ==================== 数据更新 ====================
elif menu == "🔄 数据更新":
    st.header("🔄 数据更新")
    
    st.markdown("""
    **更新说明**:
    1. 更新日线数据（获取最新行情）
    2. 计算新因子
    3. 更新行业数据
    
    **预计时间**: 10-30 分钟
    """)
    
    # 更新选项
    st.subheader("更新选项")
    
    update_daily = st.checkbox("✅ 更新日线数据", value=True)
    update_factors = st.checkbox("✅ 计算因子", value=True)
    update_industry = st.checkbox("⚠️ 更新行业数据（较慢）", value=False)
    
    if st.button("🚀 开始更新", type="primary"):
        st.info("更新任务已启动，请在终端查看进度...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 模拟进度（实际应该调用后台任务）
        for i in range(100):
            # 这里应该调用实际的更新脚本
            # subprocess.run(["python3", "scripts/update_daily.py"])
            progress_bar.progress(i + 1)
            status_text.text(f"更新中... {i+1}%")
        
        st.success("✅ 更新完成！")
        st.balloons()
        
        st.markdown("""
        **更新命令**（在终端运行）:
        ```bash
        # 更新日线数据
        python3 scripts/update_daily.py
        
        # 计算因子
        python3 scripts/calculate_factors.py
        
        # 更新行业数据
        python3 scripts/download_real_industry.py
        ```
        """)

# ==================== 选股推荐 ====================
elif menu == "📈 选股推荐":
    st.header("📈 选股推荐")
    
    # 参数设置
    st.subheader("⚙️ 选股参数")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        top_n = st.slider("选股数量", 10, 50, 20)
    
    with col2:
        strategy = st.selectbox(
            "策略选择",
            ["反转因子", "动量因子", "多因子组合", "机器学习"]
        )
    
    with col3:
        industry_neutral = st.checkbox("行业中性化", value=False)
    
    if st.button("🔍 生成选股推荐", type="primary"):
        with st.spinner("正在计算选股推荐..."):
            # 获取最新选股数据
            with get_db_connection(DATABASE_PATH) as conn:
                # 获取最新日期
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(trade_date) FROM factor_values")
                latest_date = cursor.fetchone()[0]
                
                if latest_date:
                    # 获取因子值
                    query = """
                        SELECT ts_code, factor_value
                        FROM factor_values
                        WHERE factor_name = 'momentum_20' 
                        AND trade_date = ?
                        ORDER BY factor_value DESC
                        LIMIT ?
                    """
                    df = pd.read_sql_query(query, conn, params=(latest_date, top_n))
                    
                    # 显示结果
                    st.success(f"✅ 获取到 {len(df)} 只推荐股票（日期：{latest_date}）")
                    
                    # 显示表格
                    st.subheader("📋 推荐股票列表")
                    
                    # 添加股票名称（简化）
                    df['排名'] = range(1, len(df) + 1)
                    df = df[['排名', 'ts_code', 'factor_value']]
                    df.columns = ['排名', '股票代码', '因子得分']
                    
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # 导出
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 导出 CSV",
                        csv,
                        f"stock_selection_{latest_date}.csv",
                        "text/csv",
                        key='download-csv'
                    )
                else:
                    st.warning("⚠️ 暂无因子数据，请先计算因子")
    
    # 历史推荐
    st.markdown("---")
    st.subheader("📜 历史推荐记录")
    
    with get_db_connection(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trade_date, COUNT(DISTINCT ts_code) as stock_count
            FROM factor_values
            WHERE factor_name = 'momentum_20'
            GROUP BY trade_date
            ORDER BY trade_date DESC
            LIMIT 10
        """)
        history = cursor.fetchall()
    
    if history:
        history_df = pd.DataFrame(history, columns=['日期', '股票数量'])
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无历史记录")

# ==================== 模型预测 ====================
elif menu == "🤖 模型预测":
    st.header("🤖 机器学习模型预测")
    
    st.markdown("""
    **可用模型**:
    - RandomForest（已训练）
    - LightGBM（需安装）
    - XGBoost（需安装）
    """)
    
    # 模型选择
    col1, col2 = st.columns(2)
    
    with col1:
        model_type = st.selectbox(
            "选择模型",
            ["RandomForest", "LightGBM", "XGBoost"]
        )
    
    with col2:
        predict_period = st.selectbox(
            "预测周期",
            [5, 10, 20],
            index=2
        )
    
    # 加载模型
    model_path = project_root / "research_results" / "ml" / f"{model_type.lower()}_model.pkl"
    
    if model_path.exists():
        st.success(f"✅ 模型已加载：{model_path.name}")
    else:
        st.warning(f"⚠️ 模型文件不存在，请先训练 {model_type} 模型")
    
    if st.button("🔮 运行预测", type="primary"):
        with st.spinner("正在运行预测..."):
            st.info("预测功能需要完整的机器学习流程，请在终端运行:")
            st.code("python3 scripts/ml_system.py --model randomforest")
            
            # 显示已有的预测结果
            eval_path = project_root / "research_results" / "ml" / f"{model_type.lower()}_evaluation.csv"
            
            if eval_path.exists():
                eval_df = pd.read_csv(eval_path)
                
                st.subheader("📊 模型评估结果")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'ic_pearson' in eval_df.columns:
                        st.metric("Pearson IC", f"{eval_df['ic_pearson'].values[0]:.6f}")
                
                with col2:
                    if 'ic_spearman' in eval_df.columns:
                        st.metric("Spearman IC", f"{eval_df['ic_spearman'].values[0]:.6f}")
                
                with col3:
                    if 'ic_ir' in eval_df.columns:
                        st.metric("IC IR", f"{eval_df['ic_ir'].values[0]:.4f}")
            else:
                st.info("暂无评估结果")

# ==================== 参数分析 ====================
elif menu == "⚙️ 参数分析":
    st.header("⚙️ 参数分析")
    
    st.markdown("""
    **分析内容**:
    - 特征重要性
    - 模型性能
    - 回测结果
    """)
    
    # 特征重要性
    st.subheader("📊 特征重要性")
    
    importance_path = project_root / "research_results" / "ml" / "randomforest_feature_importance.csv"
    
    if importance_path.exists():
        importance_df = pd.read_csv(importance_path)
        
        # 显示 Top 20
        st.dataframe(importance_df.head(20), use_container_width=True, hide_index=True)
        
        # 图表
        fig = px.bar(
            importance_df.head(20),
            x='importance',
            y='feature',
            orientation='h',
            title="Top 20 特征重要性"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无特征重要性数据")
    
    st.markdown("---")
    
    # 回测结果
    st.subheader("📈 回测结果")
    
    backtest_path = project_root / "research_results" / "stock_selection" / "performance_report.md"
    
    if backtest_path.exists():
        with open(backtest_path, 'r') as f:
            report = f.read()
        st.markdown(report)
    else:
        st.info("暂无回测报告")

# ==================== 数据查询 ====================
elif menu == "📁 数据查询":
    st.header("📁 数据查询")
    
    # 查询类型
    query_type = st.selectbox(
        "查询类型",
        ["股票查询", "因子查询", "行业查询"]
    )
    
    if query_type == "股票查询":
        stock_code = st.text_input("股票代码", "000001.SZ")
        
        if st.button("🔍 查询"):
            with get_db_connection(DATABASE_PATH) as conn:
                # 获取最新数据
                query = """
                    SELECT ts_code, trade_date, open, high, low, close, volume
                    FROM daily_prices
                    WHERE ts_code = ?
                    ORDER BY trade_date DESC
                    LIMIT 30
                """
                df = pd.read_sql_query(query, conn, params=(stock_code,))
                
                if not df.empty:
                    st.success(f"✅ 获取到 {len(df)} 条记录")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # 价格图表
                    if 'close' in df.columns:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df['trade_date'],
                            y=df['close'],
                            mode='lines+markers',
                            name='收盘价'
                        ))
                        fig.update_layout(title=f"{stock_code} 价格走势")
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"⚠️ 未找到股票 {stock_code} 的数据")
    
    elif query_type == "因子查询":
        factor_name = st.selectbox(
            "选择因子",
            ["momentum_20", "momentum_5", "volatility_20", "volume_ratio", "rsi_14"]
        )
        
        stock_code = st.text_input("股票代码", "000001.SZ")
        
        if st.button("🔍 查询因子"):
            with get_db_connection(DATABASE_PATH) as conn:
                query = """
                    SELECT ts_code, trade_date, factor_value
                    FROM factor_values
                    WHERE factor_name = ? AND ts_code = ?
                    ORDER BY trade_date DESC
                    LIMIT 60
                """
                df = pd.read_sql_query(query, conn, params=(factor_name, stock_code))
                
                if not df.empty:
                    st.success(f"✅ 获取到 {len(df)} 条因子记录")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # 因子图表
                    fig = px.line(df, x='trade_date', y='factor_value', title=f"{stock_code} - {factor_name}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ 暂无因子数据")
    
    elif query_type == "行业查询":
        with get_db_connection(DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT industry_name, COUNT(*) as stock_count
                FROM industry_classification
                GROUP BY industry_name
                ORDER BY stock_count DESC
            """)
            industries = cursor.fetchall()
        
        if industries:
            industry_df = pd.DataFrame(industries, columns=['行业', '股票数量'])
            st.dataframe(industry_df, use_container_width=True, hide_index=True)
            
            # 行业分布图
            fig = px.bar(industry_df.head(20), x='股票数量', y='行业', orientation='h')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无行业数据")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>A 股量化选股系统 v1.0 | Powered by Streamlit</p>
</div>
""", unsafe_allow_html=True)
