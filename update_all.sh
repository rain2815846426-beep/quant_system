#!/bin/bash
# 一键更新所有数据（快速版）
# 只更新前 100 只股票，约 3-5 分钟

cd /Users/yuanxiaoyu/Downloads/quant_system

echo "======================================"
echo "一键更新所有数据（快速版）"
echo "======================================"
echo ""

# 更新日线数据（前 100 只）
echo "步骤 1/3: 更新日线数据..."
python3 scripts/update_batch.py --batch 1 --size 100 --delay 2

# 计算因子
echo ""
echo "步骤 2/3: 计算因子..."
python3 scripts/calculate_factors.py

# 更新情绪
echo ""
echo "步骤 3/3: 更新情绪数据..."
python3 scripts/update_news_factors.py

echo ""
echo "======================================"
echo "更新完成！"
echo "======================================"
