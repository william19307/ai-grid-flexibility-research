# 阶段 32：年度电量统计范围审读

恢复 source_access_log.json 中成功取得的原始文件到记录路径，保留 URL、访问时间、版本及哈希。三个 PDF/HTML 核心输入由 evidence_manifest.json 固定；官网落地页用于记录下载链。所有原件留在排除的 sources 目录，不进入 Git。

```bash
python work/research/analysis/audit_captive_operating_scope.py --output-dir work/tmp/captive-operating-replay
```

需 pypdf 6.10.0、pdfplumber 0.11.9（实际版本记录在 validation.json）。脚本输出 24 个年度数值、来源边界检查、精确十进制勾稽和两个 PDF 版本的正文对应。新版源文件哈希不符必须另行审读，不可直接改预期值。

香港交易所版本 75 页，官网版本 73 页。官网第 n 页对应交易所第 n+1 页，73 页标准化文本完全对应；仅对已审读页的嵌入图片核对哈希，未宣称整本像素或字节相同。目标交易所页 4/33/66/72/73，对应官网页 3/32/65/71/72；印刷页分别为 1–2、59–60、125–126、137–138、139–140。完整目标页已经视觉审读。

assurance_visual_review.json 是鉴证扫描页的人工读取，不是文本双引擎核查。有限保证、温室气体核查和本研究的模型验证是不同证据。

控制系统原文下载因 TLS 证书失效失败，web 文本读取超时；没有关闭证书验证。此文件只保留失败收据，不作为输入。报道中的 55MWh 光伏容量及 8000 千瓦时年度移峰没有被擅自改单位。导出的 annual_energy_disclosures.csv 全部 dispatch_admitted=False；不得直接填入阶段 31 模型。下一步需要同一电表/厂区/时间轴的生产用电、毛净输出、煤气和净购售电记录。
