# Release Notes Workflow

从 `v0.1.0` 开始，项目使用以下三件套记录每日版本推进：

1. `docs/releases/VERSION.md`：当前项目版本号
2. `docs/releases/CHANGELOG.md`：累计变更摘要
3. `docs/releases/YYYY-MM-DD-vX.Y.Z.md`：当天详细日报

推荐更新规则：

- **Patch**：修 bug、文档修正、非破坏性小优化
- **Minor**：新增页面、接口、分析能力、流程能力
- **Major**：有破坏性变更或架构重置

每日最小动作：

1. 更新 `docs/releases/VERSION.md`
2. 在 `docs/releases/CHANGELOG.md` 追加当天版本摘要
3. 新建当天 release report
4. 在 `PROJECT_PROGRESS.md` 留一条简短索引
