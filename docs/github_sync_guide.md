# GitHub 同步指南

## 📋 步骤 1: 在 GitHub 创建仓库

### 1.1 访问 GitHub

打开：https://github.com/new

### 1.2 填写信息

- **Repository name**: `quant_system`（或你喜欢的名字）
- **Description**: A 股量化选股系统
- **Public/Private**: 
  - Public: 公开可见（推荐，可以分享）
  - Private: 只有你可见
- **Initialize this repository with**: 
  - ❌ 不要勾选 README
  - ❌ 不要勾选 .gitignore
  - ❌ 不要勾选 license

### 1.3 创建仓库

点击 **Create repository**

创建后，GitHub 会显示仓库 URL，例如：
```
https://github.com/你的用户名/quant_system.git
```

---

## 📋 步骤 2: 配置远程仓库

### 2.1 添加远程仓库

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system

# 替换为你的仓库 URL
git remote add origin https://github.com/你的用户名/quant_system.git
```

### 2.2 验证配置

```bash
git remote -v
```

应该看到：
```
origin  https://github.com/你的用户名/quant_system.git (fetch)
origin  https://github.com/你的用户名/quant_system.git (push)
```

---

## 📋 步骤 3: 推送代码

### 方法 1: 使用推送脚本（推荐）

```bash
./push_to_github.sh
```

### 方法 2: 手动推送

```bash
# 提交更改
git add -A
git commit -m "推送到 GitHub"

# 推送
git push -u origin main
```

---

## 🔐 GitHub 认证

### 使用 HTTPS（需要 Token）

**问题**: GitHub 不再支持密码认证

**解决**: 使用 Personal Access Token

#### 创建 Token

1. 访问：https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 填写：
   - Note: `quant_system`
   - Expiration: `No expiration`
   - Select scopes: 勾选 `repo` (Full control of private repositories)
4. 点击 **Generate token**
5. **复制 Token**（只显示一次！）

#### 使用 Token

推送时会提示输入用户名和密码：
- Username: 你的 GitHub 用户名
- Password: 粘贴刚才复制的 Token

---

### 使用 SSH（推荐，更方便）

#### 1. 生成 SSH Key

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

按回车接受默认位置

#### 2. 添加 SSH Key 到 GitHub

```bash
cat ~/.ssh/id_ed25519.pub
```

复制输出内容，然后：

1. 访问：https://github.com/settings/keys
2. 点击 **New SSH key**
3. Title: `My Mac`
4. Key: 粘贴刚才复制的内容
5. 点击 **Add SSH key**

#### 3. 使用 SSH URL

```bash
# 修改远程仓库 URL
git remote set-url origin git@github.com:你的用户名/quant_system.git

# 推送
git push -u origin main
```

---

## 📊 查看推送状态

### 查看提交历史

```bash
git log --oneline -10
```

### 查看远程状态

```bash
git status
```

### 查看远程仓库

```bash
git remote -v
```

---

## 🔄 后续同步

### 本地修改后推送

```bash
# 方法 1: 使用脚本
./push_to_github.sh

# 方法 2: 手动
git add -A
git commit -m "更新内容"
git push
```

### 从 GitHub 拉取

```bash
git pull origin main
```

---

## ⚠️ 注意事项

### 不上传的文件

以下文件已在 `.gitignore` 中配置，**不会上传**：

- `database/*.db` - 数据库文件（8GB+）
- `logs/*.log` - 日志文件
- `config/config.ini` - 配置文件（包含 Token）
- `__pycache__/` - Python 缓存
- `.DS_Store` - Mac 系统文件

### 大文件处理

如果误传了大文件：

```bash
# 从 Git 历史中移除大文件
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch database/*.db' \
  --prune-empty --tag-name-filter cat -- --all

# 强制推送
git push origin main --force
```

---

## 🎯 快速参考

### 首次推送

```bash
# 1. 创建仓库（GitHub 网页）
# 2. 添加远程仓库
git remote add origin https://github.com/用户名/quant_system.git

# 3. 推送
git push -u origin main
```

### 日常推送

```bash
# 提交并推送
git add -A
git commit -m "更新说明"
git push
```

### 使用脚本

```bash
./push_to_github.sh
```

---

## 📖 常见问题

### Q: 推送失败怎么办？

A: 
1. 检查网络连接
2. 检查远程仓库 URL 是否正确
3. 检查认证（Token 或 SSH）

### Q: 如何修改远程仓库 URL？

A:
```bash
git remote set-url origin https://github.com/新用户名/新仓库名.git
```

### Q: 如何删除远程仓库？

A:
```bash
git remote remove origin
```

### Q: 如何切换到 Private 仓库？

A:
1. GitHub 仓库页面 → Settings
2. 滚动到底部 → Danger Zone
3. Change visibility → Change to private

---

## 🎉 完成！

推送成功后：

1. 访问你的 GitHub 仓库页面
2. 查看代码和提交历史
3. 可以分享给其他人

**仓库 URL**: `https://github.com/你的用户名/quant_system`

---

**更新时间**: 2026-03-17
