# 🔒 安全保护已启用

**日期**: 2026-04-12  
**状态**: ✅ 已加强

---

## ✅ 已实施的保护措施

### 1. 增强的 .gitignore
自动忽略：
- ✅ 环境变量文件（`.env`, `*.env.local`）
- ✅ 密钥文件（`*.key`, `*.pem`, `*_secret`）
- ✅ 个人配置（`.omx/`, `.codex/`, `.claude/`）
- ✅ 日志文件（`logs/`, `*.log`）
- ✅ 数据库文件（`*.db`, `*.sqlite`）
- ✅ 个人标记文件（`PERSONAL_*`, `PRIVATE_*`）

### 2. Pre-commit Hook（自动检查）
每次 `git commit` 前自动运行，检测：
- ✅ 敏感文件（.env, *.key, credentials.json）
- ✅ API key 硬编码
- ✅ 邮箱地址（除了项目邮箱）
- ✅ 内网 IP 地址
- ✅ 绝对路径（可能泄露用户名）

### 3. 手动安全检查脚本
```bash
./scripts/security_check.sh
```

### 4. 已清理的敏感内容
- ✅ 从 git 历史移除 `.omx/` 目录
- ✅ 确认没有 API key 硬编码
- ✅ 确认没有真实企业数据

---

## 🛡️ 强约束保证

### 只上传项目相关内容
- ✅ Python 源代码
- ✅ 配置模板（`.env.example`）
- ✅ 文档（README, 用户手册）
- ✅ 测试文件
- ✅ 脚本（已脱敏）

### 绝不上传
- ❌ 个人配置（.omx/, .codex/, .claude/）
- ❌ API key 和密钥
- ❌ 日志文件（可能包含路径）
- ❌ 真实企业数据
- ❌ 数据库文件

---

## 🚨 如果提交被阻止

如果看到这个错误：
```
❌ 安全检查失败！发现敏感信息。
```

**正确做法**：
1. 查看错误提示，找到敏感文件
2. 从暂存区移除：`git reset HEAD <file>`
3. 确认文件已在 `.gitignore` 中
4. 重新提交

**错误做法**：
❌ 不要用 `git commit --no-verify` 跳过检查（除非你确定安全）

---

## 📋 提交前自检清单

每次提交前确认：
```bash
# 1. 查看要提交的文件
git status

# 2. 确认没有敏感文件
git diff --cached --name-only | grep -E "(\.env|\.key|\.omx)"

# 3. 运行安全检查
./scripts/security_check.sh

# 4. 提交
git commit -m "your message"
```

---

## 🔐 API Key 管理

### ✅ 正确做法
```bash
# 1. 创建 .env 文件（不提交）
echo "OPENAI_API_KEY=sk-..." > .env

# 2. 代码中读取
import os
api_key = os.getenv("OPENAI_API_KEY")
```

### ❌ 错误做法
```python
# 永远不要这样做！
api_key = "sk-proj-abc123..."
```

---

## 📝 脱敏处理示例

### 企业数据
```python
# ❌ 真实数据
{"company_name": "Siemens AG", "revenue": 77800000000}

# ✅ 脱敏后
{"company_name": "GreenTech Solutions GmbH", "revenue": 50000000}
```

### 路径
```python
# ❌ 绝对路径
"/Users/yumei/projects/esg-research-toolkit"

# ✅ 相对路径
"./esg-research-toolkit"
```

---

## 🔍 定期审计

每月运行：
```bash
# 检查是否有敏感文件被追踪
git ls-files | grep -E "(\.env|\.key|\.omx)"

# 检查代码中的 API key
git grep -i "api[_-]key" | grep -v "\.example"
```

---

## 📚 详细文档

完整安全策略：`SECURITY.md`

---

## ✅ 现在可以安全提交了

Pre-commit hook 已启用，每次提交都会自动检查。

如果需要临时跳过检查（确认安全后）：
```bash
git commit --no-verify -m "message"
```

---

**安全第一！🔒**
