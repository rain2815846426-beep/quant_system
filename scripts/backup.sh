#!/bin/bash
# 项目备份脚本

PROJECT_ROOT="/Users/yuanxiaoyu/Downloads/quant_system"
BACKUP_DIR="/Users/yuanxiaoyu/Backups/quant_system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "============================================================"
echo "量化系统备份脚本"
echo "============================================================"
echo ""
echo "项目目录：$PROJECT_ROOT"
echo "备份目录：$BACKUP_DIR"
echo ""

# 1. 代码和文档备份（不含数据库）
echo "[1/3] 备份代码和文档..."
CODE_SIZE=$(du -sh $PROJECT_ROOT --exclude='database' --exclude='logs' 2>/dev/null | awk '{print $1}')
tar --exclude='database/*.db' \
    --exclude='logs/*' \
    --exclude='__pycache__' \
    --exclude='.git' \
    -czf $BACKUP_DIR/quant_code_$DATE.tar.gz \
    -C $PROJECT_ROOT .
CODE_BACKUP_SIZE=$(ls -lh $BACKUP_DIR/quant_code_$DATE.tar.gz | awk '{print $5}')
echo "  ✓ 代码备份完成：$BACKUP_DIR/quant_code_$DATE.tar.gz ($CODE_BACKUP_SIZE)"

# 2. 数据库备份（可选）
echo ""
echo "[2/3] 备份数据库..."
if [ -f "$PROJECT_ROOT/database/quant.db" ]; then
    DB_SIZE=$(ls -lh $PROJECT_ROOT/database/quant.db | awk '{print $5}')
    echo "  数据库大小：$DB_SIZE"
    echo "  是否备份数据库？(y/n/skip)"
    read -t 10 -p "  输入 (y/n/skip，10 秒后自动跳过): " choice
    
    case $choice in
        y|Y)
            cp $PROJECT_ROOT/database/quant.db $BACKUP_DIR/quant_db_$DATE.db
            echo "  ✓ 数据库备份完成：$BACKUP_DIR/quant_db_$DATE.db"
            ;;
        n|N)
            echo "  ✗ 跳过数据库备份"
            ;;
        *)
            echo "  ✗ 超时，跳过数据库备份"
            ;;
    esac
else
    echo "  数据库不存在，跳过"
fi

# 3. 研究结果备份
echo ""
echo "[3/3] 备份研究结果..."
if [ -d "$PROJECT_ROOT/research_results" ] && [ "$(ls -A $PROJECT_ROOT/research_results 2>/dev/null)" ]; then
    tar -czf $BACKUP_DIR/quant_results_$DATE.tar.gz -C $PROJECT_ROOT research_results/
    echo "  ✓ 研究结果备份完成：$BACKUP_DIR/quant_results_$DATE.tar.gz"
else
    echo "  研究结果为空，跳过"
fi

# 完成
echo ""
echo "============================================================"
echo "备份完成！"
echo "============================================================"
echo ""
echo "备份文件列表:"
ls -lh $BACKUP_DIR/quant_*_$DATE.* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "磁盘使用情况:"
df -h $BACKUP_DIR | tail -1 | awk '{print "  可用空间：" $4}'
echo ""
