# 项目保存和备份指南

## 当前项目状态

### 文件统计
- **Python 脚本**: 30 个
- **文档**: 13 个
- **CSV 结果**: 1 个
- **数据库**: 8.5 GB

### 目录结构
```
quant_system/
├── config/              # 配置文件 (~1 KB)
├── src/                 # 源代码 (~50 KB)
│   ├── data_fetch/     # 数据抓取
│   ├── factors/        # 因子计算
│   ├── research/       # 因子研究
│   └── utils/          # 工具函数
├── scripts/             # 实用脚本 (~30 KB)
├── docs/                # 文档 (~100 KB)
├── database/            # 数据库 (8.5 GB) ⚠️
├── research_results/    # 研究结果 (~1 KB)
├── logs/                # 日志文件 (~10 MB)
└── requirements.txt     # 依赖列表
```

---

## 保存方案

### 方案 1：Git 版本控制（推荐）⭐

适合保存代码和文档，**不保存数据库**。

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 1. 初始化 Git 仓库
git init

# 2. 添加所有文件（数据库除外）
git add -A

# 3. 提交
git commit -m "Initial commit: Quant system Phase 2.5"

# 4. 关联远程仓库（可选）
git remote add origin https://github.com/yourname/quant_system.git
git push -u origin main
```

**.gitignore 已配置**：
- `database/*.db` - 不保存数据库
- `logs/*.log` - 不保存日志
- `__pycache__/` - 不保存 Python 缓存

---

### 方案 2：完整备份（包含数据库）

适合完整保存整个项目。

#### 2.1 压缩备份

```bash
cd /Users/yuanxiaoyu/Downloads

# 压缩整个项目（约 8.5 GB）
tar -czf quant_system_backup_$(date +%Y%m%d).tar.gz quant_system/

# 解压
tar -xzf quant_system_backup_20260313.tar.gz
```

#### 2.2 数据库单独备份

```bash
# 复制数据库
cp database/quant.db database/quant_backup_$(date +%Y%m%d).db

# 或使用 SQLite 导出
sqlite3 database/quant.db ".dump" > database_backup.sql
```

#### 2.3 使用 rsync 增量备份

```bash
# 备份到外部硬盘
rsync -av --progress \
  /Users/yuanxiaoyu/Downloads/quant_system/ \
  /Volumes/ExternalDrive/Backups/quant_system/
```

---

### 方案 3：云存储备份

#### 3.1 iCloud（Mac 用户）

```bash
# 将项目移动到 iCloud
mv /Users/yuanxiaoyu/Downloads/quant_system \
   /Users/yuanxiaoyu/Library/Mobile\ Documents/com~apple~CloudDocs/
```

#### 3.2 其他云服务

- **Google Drive**: 使用 Backup and Sync
- **Dropbox**: 自动同步文件夹
- **OneDrive**: 文件夹保护

⚠️ **注意**: 8.5 GB 数据库上传可能需要较长时间

---

## 精简保存方案（推荐）

如果磁盘空间有限，可以只保存核心内容：

### 1. 保存代码和文档

```bash
# 创建精简版备份
cd /Users/yuanxiaoyu/Downloads/quant_system

# 排除数据库和日志
tar --exclude='database/*.db' \
    --exclude='logs/*' \
    --exclude='__pycache__' \
    -czf quant_system_lite_$(date +%Y%m%d).tar.gz .
```

**大小**: 约 100-200 KB

### 2. 数据库可以重新下载

```bash
# 有代码就可以重新下载数据
python3 scripts/download_index_stocks.py
python3 scripts/calculate_factors.py
```

---

## 快速恢复指南

### 场景 1：只有代码备份

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 下载数据
python3 scripts/download_index_stocks.py

# 3. 计算因子
python3 scripts/calculate_factors.py
```

### 场景 2：有完整备份

```bash
# 1. 解压备份
tar -xzf quant_system_backup_20260313.tar.gz

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 直接使用
python3 scripts/analyze_factors.py
```

---

## 定期备份建议

### 每日（可选）
```bash
# 备份研究结果
cp research_results/*.csv research_results/backup_$(date +%Y%m%d)/
```

### 每周
```bash
# 备份数据库（如果数据有更新）
cp database/quant.db database/weekly_backup_$(date +%Y%m%d).db
```

### 每月
```bash
# 完整压缩备份
tar -czf quant_system_monthly_$(date +%Y%m).tar.gz quant_system/
```

---

## 当前项目内容清单

### 核心代码（必须保存）
- [x] `config/settings.py` - 配置
- [x] `src/data_fetch/` - 数据抓取模块
- [x] `src/factors/` - 因子计算模块
- [x] `src/research/` - 因子研究模块
- [x] `scripts/` - 所有脚本

### 文档（建议保存）
- [x] `README.md` - 项目说明
- [x] `docs/dev_log.md` - 开发日志
- [x] `docs/factor_system.md` - 因子系统说明
- [x] `docs/factor_research.md` - 因子研究说明

### 数据（可选保存）
- [ ] `database/quant.db` - 8.5 GB（可重新下载）
- [ ] `logs/` - 日志文件（可删除）
- [ ] `research_results/` - 研究结果（建议保存）

---

## 一键备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash
# 一键备份脚本

PROJECT_ROOT="/Users/yuanxiaoyu/Downloads/quant_system"
BACKUP_DIR="/Users/yuanxiaoyu/Backups/quant_system"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

echo "开始备份..."

# 1. 代码和文档（不含数据库）
echo "备份代码和文档..."
tar --exclude='database/*.db' \
    --exclude='logs/*' \
    --exclude='__pycache__' \
    -czf $BACKUP_DIR/quant_code_$DATE.tar.gz \
    -C $PROJECT_ROOT .

# 2. 数据库单独备份
echo "备份数据库..."
cp $PROJECT_ROOT/database/quant.db $BACKUP_DIR/quant_db_$DATE.db

echo "备份完成！"
echo "代码备份：$BACKUP_DIR/quant_code_$DATE.tar.gz"
echo "数据库备份：$BACKUP_DIR/quant_db_$DATE.db"
```

使用：
```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```

---

## 推荐方案总结

**最佳实践**：

1. **代码和文档** → Git 版本控制（GitHub/GitLab）
2. **数据库** → 本地保存，定期压缩备份
3. **研究结果** → CSV 文件，Git 跟踪

**最小保存**：
```bash
# 只保存代码（约 200 KB）
tar --exclude='database' --exclude='logs' -czf quant_minimal.tar.gz quant_system/
```

**完整保存**：
```bash
# 完整备份（约 8.5 GB）
tar -czf quant_full.tar.gz quant_system/
```
