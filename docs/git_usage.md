# Git 版本控制使用说明

## ✅ Git 仓库已创建

**仓库位置**: `/Users/yuanxiaoyu/Downloads/quant_system`  
**当前分支**: `main`  
**提交数量**: 1  
**提交 ID**: `d27cfb2`

---

## 查看状态

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 查看当前状态
git status

# 查看提交历史
git log --oneline

# 查看变更
git diff HEAD
```

---

## 日常使用

### 1. 修改后提交

```bash
# 查看变更
git status

# 添加所有变更
git add -A

# 或者只添加特定文件
git add src/factors/momentum_factor.py
git add docs/dev_log.md

# 提交
git commit -m "描述你的修改"
```

### 2. 查看历史

```bash
# 简洁日志
git log --oneline

# 详细日志
git log --pretty=format:"%h - %an, %ar : %s"

# 查看某次提交
git show d27cfb2
```

### 3. 撤销修改

```bash
# 撤销工作区修改（未 add）
git checkout -- filename.py

# 撤销已 add 的文件
git reset HEAD filename.py

# 撤销最近一次提交（保留修改）
git reset --soft HEAD~1
```

---

## 推送到远程仓库（可选）

### GitHub

```bash
# 1. 在 GitHub 创建新仓库（不要勾选 README）

# 2. 关联远程仓库
git remote add origin https://github.com/YOUR_USERNAME/quant_system.git

# 3. 推送
git branch -M main
git push -u origin main

# 后续推送
git push
```

### Gitee（国内）

```bash
# 1. 在 Gitee 创建仓库

# 2. 关联远程仓库
git remote add origin https://gitee.com/YOUR_USERNAME/quant_system.git

# 3. 推送
git push -u origin main
```

---

## 分支管理

```bash
# 创建新分支
git branch feature-ml-model

# 切换分支
git checkout feature-ml-model

# 创建并切换
git checkout -b feature-ml-model

# 合并分支
git checkout main
git merge feature-ml-model

# 删除分支
git branch -d feature-ml-model
```

---

## .gitignore 说明

以下文件**不会**被 Git 跟踪：

| 文件/目录 | 原因 |
|----------|------|
| `database/*.db` | 数据库文件（8.5 GB，可重新下载） |
| `logs/*.log` | 日志文件（可删除） |
| `__pycache__/` | Python 缓存 |
| `*.pyc` | Python 编译文件 |
| `.DS_Store` | Mac 系统文件 |
| `venv/` | 虚拟环境 |

---

## 恢复项目

如果需要在其他机器恢复项目：

### 从本地备份恢复

```bash
# 1. 复制代码
cp -r /path/to/backup/quant_system /new/location/

# 2. 重新下载数据
cd /new/location/quant_system
pip3 install -r requirements.txt
python3 scripts/download_index_stocks.py
python3 scripts/calculate_factors.py
```

### 从 Git 仓库恢复

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/quant_system.git

# 2. 安装依赖
cd quant_system
pip3 install -r requirements.txt

# 3. 下载数据
python3 scripts/download_index_stocks.py
python3 scripts/calculate_factors.py
```

---

## 标签管理

```bash
# 创建标签
git tag -a v1.0.0 -m "Phase 2.5 complete"

# 查看标签
git tag

# 推送标签
git push origin v1.0.0

# 推送所有标签
git push --tags
```

---

## 常用 Git 命令速查

| 命令 | 说明 |
|------|------|
| `git status` | 查看状态 |
| `git add <file>` | 添加文件 |
| `git commit -m "msg"` | 提交 |
| `git log --oneline` | 查看日志 |
| `git diff` | 查看差异 |
| `git checkout -- <file>` | 撤销修改 |
| `git branch` | 查看分支 |
| `git push` | 推送 |
| `git pull` | 拉取 |
| `git merge <branch>` | 合并分支 |

---

## 当前仓库统计

```bash
# 查看仓库大小
git count-objects -vH

# 查看文件统计
git ls-files | wc -l

# 查看贡献者
git shortlog -sn
```

---

## 下一步

1. **配置 Git 用户信息**（可选）:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

2. **推送到远程仓库**（可选）:
   - GitHub: https://github.com
   - Gitee: https://gitee.com

3. **继续开发**:
   - Phase 3: 机器学习模型
   - 每次完成后记得 `git add` 和 `git commit`

---

**Git 仓库创建时间**: 2026-03-13  
**首次提交**: d27cfb2  
**文件数**: 49 个
