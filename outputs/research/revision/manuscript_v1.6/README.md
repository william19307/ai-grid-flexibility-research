# v1.6 文献整合审读稿

这是当前可审读的英文主文版本。它将阶段 01–36 中已经通过检查的内容与当前文献边界合并，保留原投稿 v1.4 作为历史冻结版本。v1.6 不是可直接重新投稿的终稿。

## 文件

- `core_paper_en_v1.6_review.docx`：可编辑 Word 主文。
- `core_paper_en_v1.6_review.pdf`：与 Word 对应的 8 页审阅版。
- `core_paper_en_v1.6_review.md`：生成主文的可追踪文本。
- `citation_validation.json`：引用、证据登记、表格和媒体的独立检查结果。
- `figures/fig1_policy_attribution.png`：当前证据支持的归因图。

## 已验证

- 23 条正式参考文献全部在正文引用，并按首次出现顺序排列。
- 21 项直接相关研究已登记；17 项 DOI/arXiv 元数据标题核对通过。
- Caprara 等 2026 年论文的 27 页正式版本完成 13 项全文边界审计。
- 7 项内部证据登记、2 张表、1 幅图和广义首次主张检查通过。
- DOCX 完整性检查通过；PDF 为 Letter 8 页，全部页面逐页检查，无裁切、重叠、表格溢出或链接越界。

## 当前结论边界

可支持的贡献是：在相同任务群体和明确完成基准下，对启动时间与运行档位进行四格归因，并用重复计入与非线性启停反例说明从计算侧结果转换到电网价值时必须满足的边界。

仍缺同硬件整机交流侧测量、真实服务合同与拓扑、同口径省级需求和发电输入、历史决策时信息，以及固定投资的完整留出期验证。因此，稿件没有恢复旧省级收益区间、避免容量或机制优越性主张。

## 复核入口

在仓库根目录运行：

```bash
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/analysis/verify_literature_revision.py
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/analysis/audit_caprara_fulltext.py
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/analysis/verify_manuscript_v16.py
```

生成入口与完整依赖顺序见仓库根目录 `REPRODUCE.md`。
