# Task 22: 前端 UI/UX 全面打磨

**目标**: 提升整体界面质感——加载动画、错误反馈、空状态、移动端适配、色彩一致性、微交互。

**前置条件**: 无（独立任务）  
**优先级**: P1  
**预计时间**: 45–60 分钟

---

## Step 1 — 全局加载骨架屏（Skeleton）

在 `frontend/src/components/ui/skeleton.tsx`（shadcn 已有）基础上，  
为每个页面添加 Skeleton 占位：

**DashboardPage.tsx** — isLoading 时显示：
```tsx
{isLoading && (
  <div className="space-y-4">
    <div className="grid grid-cols-3 gap-4">
      {[1,2,3].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
    </div>
    <Skeleton className="h-48 rounded-xl" />
  </div>
)}
```

**TaxonomyPage / FrameworksPage / RegionalPage** — 同样模式，各自适配网格。

---

## Step 2 — 全局错误边界 + Toast 通知

新建 `frontend/src/components/ErrorBoundary.tsx`：
```tsx
import { Component, ErrorInfo, ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; message: string }

export class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false, message: '' }
  
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }
  
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ESG Toolkit error:', error, info)
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="text-red-500 text-5xl">⚠️</div>
          <h2 className="text-lg font-semibold text-slate-800">Something went wrong</h2>
          <p className="text-sm text-slate-500 max-w-md text-center">{this.state.message}</p>
          <button
            className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700"
            onClick={() => this.setState({ hasError: false, message: '' })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
```

在 `App.tsx` 中用 `<ErrorBoundary>` 包裹 `<Routes>`。

安装并配置 `sonner`（Toast 库）：
```bash
cd frontend && npm install sonner
```

在 `main.tsx` 加入 `<Toaster />`，  
所有 API 错误处理从 `console.error` 改为 `toast.error(t('errors.xxx'))`。

---

## Step 3 — 上传页面体验升级

`UploadPage.tsx` 改进：
1. **拖拽高亮** — `onDragOver` 时 border 变色（`border-indigo-500 bg-indigo-50`）
2. **文件预览** — 显示选中文件名 + 大小（`(size/1024/1024).toFixed(1) MB`）
3. **进度条** — 上传中显示不确定进度条（`<Progress className="animate-pulse" />`）
4. **成功动画** — 上传成功后显示绿色 checkmark + 数据卡片淡入（`animate-fade-in`）

在 `frontend/src/index.css` 添加：
```css
@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-fade-in { animation: fade-in 0.3s ease-out both; }
```

---

## Step 4 — Dashboard 数据卡片升级

`DashboardPage.tsx` 的 MetricCard：
1. 数字动画（`useCountUp` hook）：
```tsx
// 新建 src/hooks/useCountUp.ts
import { useEffect, useState } from 'react'
export function useCountUp(target: number, duration = 800) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    let start = 0
    const step = target / (duration / 16)
    const timer = setInterval(() => {
      start = Math.min(start + step, target)
      setValue(Math.round(start))
      if (start >= target) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [target, duration])
  return value
}
```

2. MetricCard 颜色方案统一：
   - 绿色 = `bg-green-50 border-green-200 text-green-700`
   - 蓝色 = `bg-blue-50 border-blue-200 text-blue-700`  
   - 橙色 = `bg-orange-50 border-orange-200 text-orange-700`
   - 红色 = `bg-red-50 border-red-200 text-red-700`

---

## Step 5 — Companies 页面升级

1. **列排序** — 点击列头切换升降序（`useState<{col, dir}>`）
2. **分页** — 超过 20 条显示分页控件（`Pagination` from shadcn）
3. **行展开** — 点击公司行展开 Scope 1/2/3 详情小卡片

---

## Step 6 — 移动端适配

1. Sidebar 在小屏（< 768px）折叠为汉堡菜单：
```tsx
// 在 Sidebar.tsx 添加：
const [collapsed, setCollapsed] = useState(false)
// 屏幕宽度 < 768px 时自动折叠
```

2. 所有 `grid-cols-4` 改为 `grid-cols-2 md:grid-cols-4`
3. 所有 `grid-cols-3` 改为 `grid-cols-1 md:grid-cols-3`
4. 表格添加 `overflow-x-auto` 包裹

---

## Step 7 — 编译验证

```bash
cd frontend && npm run build 2>&1 | grep -E "error|built"
# 期望：✓ built，0 error TS
```

---

## Step 8 — 提交

```bash
git add frontend/
git commit -m "feat: UI/UX 全面打磨——骨架屏、Toast、拖拽上传、数字动画、移动端适配

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 完成标准

- [ ] 所有页面 isLoading 时显示骨架屏
- [ ] 错误边界包裹 Routes
- [ ] sonner Toast 替换 console.error
- [ ] UploadPage 有拖拽高亮 + 文件预览
- [ ] Dashboard MetricCard 有数字动画
- [ ] Companies 列表可排序
- [ ] 移动端 grid 响应式修复
- [ ] `npm run build` 无 TS 报错
