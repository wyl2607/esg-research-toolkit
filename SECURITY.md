# 安全策略 — ESG Research Toolkit

**最后更新**: 2026-04-12

---

## 🔒 核心原则

**只上传项目相关代码，绝不上传个人信息和敏感数据。**

---

## ✅ 允许上传的内容

### 1. 项目代码
- Python 源代码（`*.py`）
- 配置文件模板（`.env.example`）
- 文档（`*.md`）
- 测试文件（`tests/`）
- 脚本（`scripts/`）

### 2. 项目文档
- README（三语言版本）
- 用户手册
- API 文档
- 开发指南

### 3. 示例数据（脱敏后）
- `examples/mock_esg_data.json` — 虚构企业数据
- 不包含真实企业信息

---

## ❌ 禁止上传的内容

### 1. 敏感信息
- `.env` — 环境变量（包含 API key）
- `*.key`, `*.pem` — 密钥文件
- `credentials.json`, `secrets.json` — 凭证文件
- 任何包含 API key、token、密码的文件

### 2. 个人配置
- `.omx/` — oh-my-codex 个人配置
- `.codex/` — Codex CLI 配置
- `.claude/` — Claude Code 配置
- `.cursor/`, `.gemini/` — 其他 AI 工具配置

### 3. 个人数据
- `logs/` — 执行日志（可能包含路径、用户名）
- `data/` — 本地数据库
- `reports/` — 生成的报告（可能包含真实企业信息）
- 任何包含真实企业、个人信息的文件

### 4. 临时文件
- `*.db`, `*.sqlite` — 数据库文件
- `*.log` — 日志文件
- `.pytest_cache/` — 测试缓存
- `__pycache__/` — Python 缓存

---

## 🛡️ 自动保护机制

### 1. `.gitignore`
已配置忽略所有敏感文件类型：
```
.env
*.key
*.pem
.omx/
.codex/
.claude/
logs/
data/
reports/
PERSONAL_*
PRIVATE_*
```

### 2. Pre-commit Hook
每次 `git commit` 前自动运行安全检查：
- 检测敏感文件
- 检测 API key 硬编码
- 检测邮箱地址
- 检测内网 IP
- 检测绝对路径

### 3. 安全检查脚本
手动运行：
```bash
./scripts/security_check.sh
```

---

## 📋 提交前检查清单

每次提交前确认：

- [ ] 没有 `.env` 文件
- [ ] 没有 API key 硬编码
- [ ] 没有个人配置目录（`.omx/`, `.codex/` 等）
- [ ] 没有真实企业数据
- [ ] 没有日志文件
- [ ] 没有数据库文件
- [ ] 示例数据已脱敏

---

## 🚨 如果不小心上传了敏感信息

### 立即操作

1. **从 Git 历史中移除**
```bash
# 移除文件
git rm --cached <sensitive_file>

# 从历史中彻底删除
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch <sensitive_file>" \
  --prune-empty --tag-name-filter cat -- --all

# 强制推送
git push origin --force --all
```

2. **撤销 API key**
- 如果上传了 OpenAI API key，立即在 OpenAI 控制台撤销
- 生成新的 API key

3. **通知相关方**
- 如果泄露了企业数据，通知相关企业
- 如果泄露了个人信息，通知相关人员

---

## 🔐 API Key 管理

### 正确做法

1. **使用 `.env` 文件**
```bash
# .env（不提交到 git）
OPENAI_API_KEY=sk-...
```

2. **代码中读取环境变量**
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
```

3. **提供 `.env.example` 模板**
```bash
# .env.example（可以提交）
OPENAI_API_KEY=your_key_here
```

### 错误做法

❌ 硬编码在代码中
```python
api_key = "sk-proj-abc123..."  # 永远不要这样做！
```

❌ 提交 `.env` 文件到 git

---

## 📝 脱敏处理指南

### 企业数据脱敏

真实数据：
```json
{
  "company_name": "Siemens AG",
  "revenue": 77800000000
}
```

脱敏后：
```json
{
  "company_name": "GreenTech Solutions GmbH",
  "revenue": 50000000
}
```

### 个人信息脱敏

- 真实邮箱 → `example@example.com`
- 真实姓名 → `John Doe`
- 内网 IP → `192.168.1.100` → `192.168.x.x`
- 绝对路径 → `/Users/realname/` → `/path/to/`

---

## 🔍 定期审计

每月检查：

```bash
# 检查是否有敏感文件被追踪
git ls-files | grep -E "(\.env|\.key|\.omx|\.codex)"

# 检查历史提交中的敏感信息
git log --all --full-history -- .env

# 检查代码中的 API key
git grep -i "api[_-]key" | grep -v "\.example"
```

---

## 📞 联系方式

如果发现安全问题：
- GitHub Issues: https://github.com/wyl2607/esg-research-toolkit/issues
- Email: wyl2607@gmail.com（标题加 [SECURITY]）

---

## 📚 参考资源

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [OWASP: Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
