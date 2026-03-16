#!/bin/bash
# Dashboard 快速启动脚本

echo "======================================"
echo "A 股量化选股系统 Dashboard"
echo "======================================"
echo ""

# 检查依赖
echo "检查依赖..."
python3 -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装 Streamlit..."
    pip3 install streamlit plotly
fi

echo ""
echo "启动 Dashboard..."
echo "浏览器会自动打开 http://localhost:8501"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd "$(dirname "$0")"
streamlit run dashboard/app.py --server.address localhost --server.port 8501
