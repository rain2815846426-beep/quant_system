#!/bin/bash
# GitHub 推送脚本

echo "======================================"
echo "推送到 GitHub"
echo "======================================"
echo ""

# 检查是否配置了远程仓库
REMOTE_URL=$(git remote get-url origin 2>/dev/null)

if [ -z "$REMOTE_URL" ]; then
    echo "❌ 未配置远程仓库"
    echo ""
    echo "请先在 GitHub 创建仓库，然后运行:"
    echo "  git remote add origin https://github.com/你的用户名/quant_system.git"
    echo ""
    exit 1
fi

echo "✅ 远程仓库：$REMOTE_URL"
echo ""

# 提交更改
echo "正在提交更改..."
git add -A
git commit -m "自动提交：$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 推送
echo "正在推送到 GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo ""
    echo "查看仓库："
    echo "  $REMOTE_URL"
else
    echo ""
    echo "❌ 推送失败"
    echo ""
    echo "可能原因:"
    echo "1. 网络连接问题"
    echo "2. GitHub 认证失败（需要配置 SSH 或 Token）"
    echo "3. 仓库不存在"
fi

echo ""
echo "======================================"
