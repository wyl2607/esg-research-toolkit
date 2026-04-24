# API Provider 配置（GitHub 安全版）

本项目在 GitHub 上仅保留 **官方 OpenAI** 配置说明。

- 不提交任何中转站/代理站 URL
- 不提交第三方 provider 端点
- 不提交真实 API Key

---

## 推荐环境变量

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.3-codex
DATABASE_URL=sqlite:///./data/esg_toolkit.db
```

### 可选项

`OPENAI_BASE_URL` 通常无需设置。默认走官方 OpenAI 端点（由后端默认配置处理）。

---

## 部署原则

1. GitHub 仓库中只放占位符与说明，不放真实密钥。
2. 生产环境敏感配置仅在服务器 `.env.prod` 或 Secret Manager 中维护。
3. 若需自定义端点，仅在私有环境变量中设置，不写入仓库。

---

## 安全检查清单（提交前）

- [ ] 不含 `sk-` 等密钥字样
- [ ] 不含中转域名/第三方 API 端点
- [ ] `.env*` 文件仅保留示例或占位符
