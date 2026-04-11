# Task 4: CI/CD Pipeline

**优先级**: 中  
**预计时间**: 2 小时  
**依赖**: Task 3（Docker）

---

## 目标

配置 GitHub Actions，实现自动测试、代码质量检查和 Docker 构建。

## 输出文件

### 1. `.github/workflows/test.yml`
每次 push 或 PR 自动运行测试

```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests
      env:
        OPENAI_API_KEY: test_key_placeholder
      run: |
        pytest tests/ -v --tb=short

    - name: Check import health
      env:
        OPENAI_API_KEY: test_key_placeholder
      run: |
        python -c "from main import app; print('✓ App imports OK')"
```

### 2. `.github/workflows/lint.yml`
代码质量检查

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install ruff
      run: pip install ruff

    - name: Run ruff
      run: ruff check . --ignore E501
```

### 3. `.github/workflows/docker.yml`
打 tag 时自动构建 Docker 镜像

```yaml
name: Docker Build

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build Docker image
      run: docker build -t esg-toolkit:${{ github.ref_name }} .

    - name: Test Docker image
      run: |
        docker run -d -p 8000:8000 \
          -e OPENAI_API_KEY=test_key \
          --name esg-test \
          esg-toolkit:${{ github.ref_name }}
        sleep 5
        curl -f http://localhost:8000/health
        docker stop esg-test
```

### 4. 在 README 中添加 CI 徽章

在三个 README 文件的顶部添加：

```markdown
[![Tests](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/test.yml)
[![Lint](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/lint.yml/badge.svg)](https://github.com/wyl2607/esg-research-toolkit/actions/workflows/lint.yml)
```

## 验证标准

- [ ] `.github/workflows/` 目录已创建
- [ ] 三个 YAML 文件语法正确（`python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))"`)
- [ ] test.yml 中的 OPENAI_API_KEY 使用占位符（不暴露真实 key）
- [ ] ruff 检查通过（`ruff check . --ignore E501`）
- [ ] README 中添加了 CI 徽章

## 自愈规则

1. 如果 YAML 语法错误，检查缩进（YAML 对缩进敏感）
2. 如果 ruff 报错，修复代码风格问题（或在 ruff.toml 中添加忽略规则）
3. 如果 Docker 构建在 CI 中失败，检查是否需要额外的系统依赖

## 参考文件

- `requirements.txt` — 依赖列表
- `Dockerfile` — Docker 配置（Task 3 创建）
- `tests/` — 测试文件

## Codex 执行命令

```bash
codex exec \
  --prompt "读取 docs/codex-tasks/task_04_cicd.md，创建 GitHub Actions CI/CD：1) .github/workflows/test.yml，2) .github/workflows/lint.yml，3) .github/workflows/docker.yml，4) 在三个 README 文件顶部添加 CI 徽章。验证 YAML 语法正确，ruff 检查通过。"
```
