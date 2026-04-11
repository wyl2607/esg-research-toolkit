# API Providers 配置参考

本文档记录各 API provider 的配置方式，供 Codex CLI 和自动化脚本使用。

## LongCat API（免费，每日限额）

### 基本信息
- **官网**: https://longcat.chat/platform/docs/
- **Base URL**: `https://api.longcat.chat/openai/v1`
- **认证方式**: `Authorization: Bearer <api_key>`
- **每日额度**: 北京时间 0 点重置
- **可用模型**:
  - `LongCat-Flash-Chat` - 标准对话模型（262k tokens）
  - `LongCat-Flash-Lite` - 轻量模型（327k tokens）
  - `LongCat-Flash-Thinking` - 推理模型

### API Keys
- Key 1: `ak_2957vN8wy5lR7m52fX3a60pS5m32i`（主力）
- Key 2: `ak_2Kl6Eu7CG0dH7uJ0Wp06K9Ho3dR2c`（备用）

### 调用示例
```bash
curl -X POST https://api.longcat.chat/openai/v1/chat/completions \
  -H "Authorization: Bearer ak_2957vN8wy5lR7m52fX3a60pS5m32i" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "LongCat-Flash-Chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

### Codex CLI 配置（已废弃）
**注意**：Codex v0.120.0+ 强制要求 `wire_api = "responses"`，但 LongCat 只支持 `/chat/completions` 端点，导致不兼容。

~~旧配置（不再可用）：~~
```toml
[model_providers.longcat]
name = "longcat"
base_url = "https://api.longcat.chat/openai/v1"
wire_api = "chat"  # ← Codex 不再支持
requires_openai_auth = false
env_key = "LONGCAT_API_KEY"
```

**结论**：无法通过 Codex CLI 直连 LongCat，需要通过 cc-switch 或其他兼容层。

---

## 火山引擎 Ark Coding API

### 基本信息
- **官网**: https://www.volcengine.com/docs/82379/1298459
- **Base URL**: `https://ark.cn-beijing.volces.com/api/coding/v3`
- **认证方式**: 自定义 header（非标准 Bearer token）
- **可用模型**: `ark-code-latest`（Auto 模式）
- **计费**: 按 token 计费，比 OpenAI 便宜

### API Key
- Key: `29cfdf1d-e8c5-4706-82ef-6c9101a9c850`

### 调用方式
**注意**：火山 API 的认证方式与标准 OpenAI 不同，需要查阅官方文档或通过 cc-switch 配置。

直连测试失败（认证 header 格式不明）：
```bash
curl -X POST https://ark.cn-beijing.volces.com/api/coding/v3/chat/completions \
  -H "Authorization: Bearer 29cfdf1d-e8c5-4706-82ef-6c9101a9c850" \
  -H "Content-Type: application/json" \
  -d '{"model":"ark-code-latest","messages":[{"role":"user","content":"test"}]}'
# 返回: InvalidParameter: invalid parameter: AuthHeader
```

**结论**：需要通过 cc-switch UI 添加为 Codex provider，或查阅官方文档获取正确认证方式。

---

## Relay (cc-switch 管理)

### 基本信息
- **Base URL**: `https://relay.nf.video/v1`
- **认证方式**: OpenAI 标准 Bearer token（由 cc-switch 管理）
- **可用模型**:
  - `gpt-5.4` - 最新旗舰模型
  - `gpt-5.4-mini` - 便宜快速模型
  - `gpt-5.3-codex` - 代码专用模型
  - `gpt-4o` - 多模态模型

### Codex CLI 配置（默认）
```toml
[model_providers.codex]
name = "codex"
base_url = "https://relay.nf.video/v1"
wire_api = "responses"
requires_openai_auth = true
```

### 调用示例
```bash
# 使用默认模型（gpt-5.3-codex）
codex exec "你的任务"

# 指定模型
codex exec -m gpt-5.4-mini "你的任务"
codex exec -m gpt-5.4 "你的任务"
```

---

## 成本优化策略

### 当前可行方案（2026-04-12）
由于 Codex CLI 与 LongCat/Volcano 不兼容，当前最优策略：

1. **简单任务**（文档、翻译、格式化）：`gpt-5.4-mini`
2. **中等任务**（单模块实现、测试）：`gpt-5.4-mini`
3. **复杂任务**（架构、多文件重构）：`gpt-5.3-codex`

### 理想方案（需要 cc-switch 配置）
如果在 cc-switch UI 中添加 LongCat 和 Volcano 为 Codex provider：

1. LongCat key1（免费）→ LongCat key2（免费）
2. Volcano ark-code-latest（便宜）
3. gpt-5.4-mini（便宜兜底）
4. gpt-5.3-codex（最终兜底）

---

## 环境变量设置

```bash
# LongCat（如果通过 cc-switch 配置后可用）
export LONGCAT_API_KEY="ak_2957vN8wy5lR7m52fX3a60pS5m32i"
export LONGCAT_API_KEY2="ak_2Kl6Eu7CG0dH7uJ0Wp06K9Ho3dR2c"

# 火山引擎（如果通过 cc-switch 配置后可用）
export VOLC_API_KEY="29cfdf1d-e8c5-4706-82ef-6c9101a9c850"

# Relay（由 cc-switch 自动管理，无需手动设置）
```

---

## 故障排查

### LongCat 额度用完
**症状**: `{"error":{"message":"AppId:**m32i 达到使用量上限","type":"rate_limit_error"}}`

**解决**: 等待北京时间 0 点重置，或切换到 key2

### Codex wire_api 不兼容
**症状**: `Error loading config.toml: wire_api = "chat" is no longer supported`

**原因**: Codex v0.120.0+ 只支持 `responses` API，但 LongCat 只有 `/chat/completions` 端点

**解决**: 放弃直连，通过 cc-switch 或其他兼容层接入

### Volcano 认证失败
**症状**: `InvalidParameter: invalid parameter: AuthHeader`

**原因**: 火山 API 认证方式与标准 OpenAI 不同

**解决**: 查阅官方文档或通过 cc-switch UI 配置

---

## 参考链接

- [LongCat API 文档](https://longcat.chat/platform/docs/)
- [火山引擎 Ark API 文档](https://www.volcengine.com/docs/82379/1298459)
- [Codex CLI wire_api 变更说明](https://github.com/openai/codex/discussions/7782)
