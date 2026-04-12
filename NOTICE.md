# NOTICE — ESG Research Toolkit

## 用途声明 / Purpose Statement / Nutzungshinweis

**中文**
本工具仅用于学术研究、ESG 合规分析及非商业性教育目的。
系统仅展示从公开 ESG 报告中提取的结构化指标数据，不公开托管或再分发原始 PDF 文件。
所有原始报告的版权归各自发布方所有（如上市公司、监管机构）。

**English**
This toolkit is intended solely for academic research, ESG compliance analysis, and
non-commercial educational purposes.
Only structured metrics extracted from publicly available ESG reports are displayed.
Original PDF files are not publicly hosted or redistributed.
All original reports remain the copyright of their respective publishers
(listed companies, regulatory bodies, etc.).

**Deutsch**
Dieses Werkzeug dient ausschließlich der wissenschaftlichen Forschung, der ESG-Compliance-Analyse
und nicht-kommerziellen Bildungszwecken.
Es werden ausschließlich strukturierte Kennzahlen aus öffentlich zugänglichen ESG-Berichten angezeigt.
Originale PDF-Dateien werden weder öffentlich gehostet noch weitergegeben.
Das Urheberrecht an allen Originalberichten verbleibt bei den jeweiligen Herausgebern.

---

## 来源追溯 / Source Traceability

每条数据记录保存：
- 原始文件来源 URL（`source_url`）
- 上传/下载时间（`downloaded_at`）
- 文件 SHA-256 哈希（`file_hash`）

以上信息仅用于内部审计，不对外公开。

---

## 删除请求 / Takedown / Löschungsanfragen

如您是原始报告的版权持有人，可通过以下方式请求删除本平台存储的数据副本：

**API 请求**（立即删除 PDF 副本）：
```
POST /api/report/companies/{company_name}/{report_year}/request-deletion
```

**邮件请求**：发送至项目维护者，说明公司名称、报告年份及版权依据。
收到请求后，PDF 副本立即删除，提取的指标数据将在 30 天内清除。

**English**: Rights holders may request removal via the API endpoint above or by
contacting the project maintainer with company name, report year, and proof of copyright.
PDF copies are deleted immediately; extracted metrics are purged within 30 days.

**Deutsch**: Rechteinhaber können die Löschung über den obigen API-Endpunkt oder
per E-Mail an den Projektbetreuer beantragen. PDF-Kopien werden sofort gelöscht;
extrahierte Kennzahlen werden innerhalb von 30 Tagen bereinigt.

---

## 免责声明 / Disclaimer

本工具提供的 ESG 评分和分析结果仅供参考，不构成投资建议或法律意见。
评分模型基于公开文献实现，可能与官方认证结果存在差异。
