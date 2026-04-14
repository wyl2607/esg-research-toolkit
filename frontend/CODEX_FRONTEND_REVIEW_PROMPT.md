# Codex Frontend Review Prompt

Use this prompt when you want Codex to run the frontend verification stack and summarize the findings from real browser evidence instead of source-only guesses.

```text
Please run a full frontend validation pass in /Users/yumei/projects/esg-research-toolkit/frontend.

Run these commands in order:
1. npm run lint
2. npm run build
3. npm run test:smoke
4. npm run test:a11y
5. npm run health:check

Review the generated artifacts from:
- frontend/playwright-report
- frontend/test-results
- frontend/health-reports/latest/result.json
- frontend/health-reports/latest/summary.md

Then summarize:
1. Blocking issues
2. UX or layout regressions
3. Accessibility findings
4. Performance or bundle concerns
5. The smallest high-impact fixes to make next

When you report issues, include:
- route or page
- repro step
- evidence source
- likely root cause
- suggested fix
```
