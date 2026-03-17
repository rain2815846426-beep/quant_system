# GitHub 推送 - 手动操作步骤

## ✅ 已完成的配置

远程仓库已配置为：
```
origin  git@github.com:rain2815846426-beep/quant_system.git
```

---

## 📋 第一步：确认 SSH 连接

在终端运行：

```bash
ssh -T git@github.com
```

会看到提示：
```
The authenticity of host 'github.com' can't be established.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

**输入**: `yes` 然后按回车

如果看到：
```
Hi rain2815846426-beep! You've successfully authenticated...
```

说明 SSH 配置成功！✅

---

## 📋 第二步：推送到 GitHub

在终端运行：

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system
git push -u origin main
```

**第一次推送可能需要输入**:
- Passphrase: 输入你的 SSH Key 密码（如果设置了）
- 或者直接推送（如果没设置密码）

---

## 📋 第三步：验证推送

推送成功后，访问：
https://github.com/rain2815846426-beep/quant_system

应该能看到你的代码！

---

## 🔧 如果 SSH 有问题

### 方法 1: 生成 SSH Key

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

一直按回车（使用默认设置）

### 方法 2: 添加 SSH Key 到 GitHub

```bash
cat ~/.ssh/id_ed25519.pub
```

复制输出内容（以 `ssh-ed25519` 开头的一长串）

然后：
1. 访问：https://github.com/settings/keys
2. 点击 **New SSH key**
3. Title: `My Mac`
4. Key: 粘贴刚才复制的内容
5. 点击 **Add SSH key**

### 方法 3: 再次测试

```bash
ssh -T git@github.com
```

应该看到：
```
Hi rain2815846426-beep! You've successfully authenticated...
```

---

## 🚀 快速推送（如果 SSH 已配置好）

```bash
cd /Users/yuanxiaoyu/Downloads/quant_system
git push -u origin main
```

---

## 📊 查看推送状态

```bash
# 查看远程仓库
git remote -v

# 查看提交历史
git log --oneline -5

# 查看推送状态
git status
```

---

## ⚠️ 常见问题

### Q: 提示 "Permission denied (publickey)"

A: SSH Key 没配置好
```bash
# 重新生成 SSH Key
ssh-keygen -t ed25519 -C "your_email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 复制到 GitHub: https://github.com/settings/keys
```

### Q: 推送失败 "remote: Repository not found"

A: 检查仓库 URL 是否正确
```bash
git remote -v
# 应该是：git@github.com:rain2815846426-beep/quant_system.git

# 如果不对，重新配置
git remote set-url origin git@github.com:rain2815846426-beep/quant_system.git
```

### Q: 推送大文件失败

A: 数据库文件太大，已在 .gitignore 中排除
```bash
# 如果误加了大文件
git rm --cached database/quant.db
git commit -m "移除大文件"
git push
```

---

## 🎯 完整命令清单

```bash
# 1. 确认 SSH（第一次需要）
ssh -T git@github.com
# 输入 yes

# 2. 进入项目目录
cd /Users/yuanxiaoyu/Downloads/quant_system

# 3. 推送
git push -u origin main

# 4. 验证
git remote -v
git log --oneline -5
```

---

## 🎉 完成！

推送成功后：
1. 访问：https://github.com/rain2815846426-beep/quant_system
2. 查看代码和提交历史
3. 可以分享给其他人！

---

**更新时间**: 2026-03-17
