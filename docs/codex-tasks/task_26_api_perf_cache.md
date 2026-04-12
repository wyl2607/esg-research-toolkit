# Task 26: API 性能优化 + 缓存层

**目标**: 对计算密集型端点加本地缓存（TTL 缓存），减少重复 AI 调用，加快框架评分响应。

**前置条件**: 无  
**优先级**: P2  
**预计时间**: 30 分钟

---

## Step 1 — 安装依赖

```bash
# cachetools 已是 Python 标准生态，加入 requirements.txt
echo "cachetools~=5.3" >> requirements.txt
source .venv/bin/activate && pip install cachetools~=5.3
```

---

## Step 2 — 框架评分缓存

在 `esg_frameworks/api.py` 加入 TTL 缓存：

```python
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
import threading

_score_cache: TTLCache = TTLCache(maxsize=200, ttl=300)  # 5 分钟 TTL
_cache_lock = threading.Lock()


@router.get("/compare", response_model=MultiFrameworkReport)
def compare_frameworks(
    company_name: str = Query(...),
    report_year: int = Query(...),
    db: Session = Depends(get_db),
):
    cache_key = hashkey(company_name, report_year)
    with _cache_lock:
        if cache_key in _score_cache:
            return _score_cache[cache_key]
    
    data = _load_company(db, company_name, report_year)
    results = [scorer(data) for scorer in _SCORERS.values()]
    report = MultiFrameworkReport(
        company_name=data.company_name,
        report_year=data.report_year,
        results=results,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    with _cache_lock:
        _score_cache[cache_key] = report
    return report
```

---

## Step 3 — Taxonomy Score 缓存（同样模式）

在 `taxonomy_scorer/api.py` 对 `/taxonomy/report` 端点加相同 TTL Cache。

---

## Step 4 — 缓存清除端点（管理员）

```python
@router.post("/cache/clear")
def clear_framework_cache():
    """清除框架评分缓存（管理员用）"""
    with _cache_lock:
        _score_cache.clear()
    return {"status": "cache cleared", "entries_removed": "all"}
```

---

## Step 5 — 响应时间对比验证

```bash
source .venv/bin/activate
uvicorn main:app --port 8000 &
sleep 2

# 第 1 次（无缓存）
time curl -sf "http://localhost:8000/frameworks/compare?company_name=宁德时代&report_year=2024" > /dev/null

# 第 2 次（命中缓存，应 < 50ms）
time curl -sf "http://localhost:8000/frameworks/compare?company_name=宁德时代&report_year=2024" > /dev/null

kill %1
```

---

## Step 6 — 提交

```bash
git add requirements.txt esg_frameworks/api.py taxonomy_scorer/api.py
git commit -m "perf: 框架评分 + Taxonomy 端点加 5 分钟 TTL 缓存

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] cachetools 在 requirements.txt
- [ ] `/frameworks/compare` 第二次调用 < 50ms
- [ ] `/cache/clear` 端点可用
- [ ] `pytest tests/ -v` 全部通过
