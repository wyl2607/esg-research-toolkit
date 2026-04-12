# Task 07: 前端构建和部署

**目标**: 构建 React 前端并配置 Nginx 反向代理

**优先级**: P0

**预计时间**: 15-20 分钟

---

## 前置条件

- Task 06 已完成（Docker 容器运行正常）
- 后端 API 在 `http://127.0.0.1:8001` 可访问

---

## 任务清单

### 1. 安装 Node.js 和 npm

```bash
ssh usa-vps "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -"
ssh usa-vps "apt-get install -y nodejs"
```

**验证点**:
```bash
ssh usa-vps "node --version && npm --version"
```

**预期**: Node >= 18.x, npm >= 9.x

### 2. 构建前端

```bash
ssh usa-vps "cd /opt/esg-research-toolkit/frontend && npm install --silent"
ssh usa-vps "cd /opt/esg-research-toolkit/frontend && npm run build"
```

**验证点**:
```bash
ssh usa-vps "ls -lh /opt/esg-research-toolkit/frontend/dist/index.html"
```

**预期**: `dist/` 目录存在，包含 `index.html`, `assets/` 等

### 3. 配置 Nginx

```bash
# 复制 nginx 配置
ssh usa-vps "cp /opt/esg-research-toolkit/nginx/esg.conf /etc/nginx/sites-available/esg.conf"

# 创建软链接
ssh usa-vps "ln -sf /etc/nginx/sites-available/esg.conf /etc/nginx/sites-enabled/esg.conf"

# 删除默认配置（如果存在）
ssh usa-vps "rm -f /etc/nginx/sites-enabled/default"

# 测试配置
ssh usa-vps "nginx -t"
```

**验证点**: `nginx -t` 输出 `syntax is ok` 和 `test is successful`

### 4. 重启 Nginx

```bash
ssh usa-vps "systemctl restart nginx"
ssh usa-vps "systemctl status nginx"
```

**验证点**: Nginx 状态为 `active (running)`

### 5. 测试 HTTP 访问

```bash
# 测试前端
ssh usa-vps "curl -I http://127.0.0.1/"

# 测试 API 代理
ssh usa-vps "curl -sf http://127.0.0.1/api/health"
```

**预期**:
- 前端返回 200，Content-Type: text/html
- API 代理返回 `{"status":"healthy"}`

### 6. 配置 HTTPS（Let's Encrypt）

```bash
ssh usa-vps "certbot --nginx -d esg.meichen.beauty --non-interactive --agree-tos -m admin@meichen.beauty --redirect"
```

**验证点**:
```bash
ssh usa-vps "certbot certificates | grep esg.meichen.beauty"
```

**预期**: 证书已颁发，有效期 90 天

---

## 完成标准

- [ ] Node.js 和 npm 安装成功
- [ ] 前端构建成功，`dist/` 目录存在
- [ ] Nginx 配置正确，测试通过
- [ ] Nginx 服务运行正常
- [ ] HTTP 访问前端和 API 代理正常
- [ ] HTTPS 证书配置成功

---

## 自愈策略

### npm install 失败（网络问题）

```bash
# 使用淘宝镜像
ssh usa-vps "npm config set registry https://registry.npmmirror.com"
ssh usa-vps "cd /opt/esg-research-toolkit/frontend && npm install --silent"
```

### 前端构建失败（内存不足）

```bash
# 增加 Node.js 内存限制
ssh usa-vps "cd /opt/esg-research-toolkit/frontend && NODE_OPTIONS='--max-old-space-size=1536' npm run build"
```

### Nginx 配置测试失败

```bash
# 检查配置文件语法
ssh usa-vps "cat /etc/nginx/sites-available/esg.conf"

# 检查端口冲突
ssh usa-vps "lsof -i :80"

# 查看 Nginx 错误日志
ssh usa-vps "tail -50 /var/log/nginx/error.log"
```

### Certbot 失败（DNS 未解析）

```bash
# 检查 DNS 解析
ssh usa-vps "nslookup esg.meichen.beauty"

# 如果 DNS 未生效，跳过 HTTPS，稍后手动配置
echo "WARN: DNS not ready, skipping HTTPS for now"
```

### Nginx 无法启动

```bash
# 检查配置文件权限
ssh usa-vps "ls -l /etc/nginx/sites-available/esg.conf"

# 检查日志
ssh usa-vps "journalctl -u nginx -n 50"

# 重置配置
ssh usa-vps "rm /etc/nginx/sites-enabled/esg.conf && systemctl restart nginx"
```

---

## 依赖

- Task 06: Docker 容器构建和启动

---

## 后续任务

- Task 08: 端到端功能验证
