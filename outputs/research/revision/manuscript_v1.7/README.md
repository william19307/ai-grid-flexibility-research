# v1.7 功率边界整合审读稿

这是当前可审阅的英文主文。它在 v1.6 的文献与创新边界基础上，加入阶段 37 的 MLPerf 同硬件功率准入审计。v1.7 的 Word/PDF 版面和引用已经通过检查；它仍是投稿候选稿，不是已完成全部科学门槛的重新投稿终稿。

## 文件

- `core_paper_en_v1.7_review.docx`：可编辑 Word 主文；
- `core_paper_en_v1.7_review.pdf`：与 Word 对应的 9 页 Letter 审阅版；
- `core_paper_en_v1.7_review.md`：可追踪正文源稿；
- `citation_validation.json`：引用、证据登记和主张边界检查；
- `figures/fig1_policy_attribution.png`：当前证据支持的归因图。

## 已验证

- 26 条正式参考文献全部在正文引用，并按首次出现顺序排列；
- 8 项内部证据登记完整；
- MLPerf 同硬件审计的 24 个配对与正文数值一致；
- 2 张表、1 幅图和 Word 包结构通过独立检查；
- Word 渲染为 9 页 Letter 版，全部页面逐页检查，无裁切、重叠、表格溢出、断裂段落或链接越界。

## 当前结论边界

公共 MLPerf 证据支持同一 8×H100 系统在 MaxQ 下的任务相关性能损失和单侧交流整机功率，但常规模式没有提交交流功率日志，因此不能计算整机节能率。主文继续把省级收益、避免容量和机制优越性留在未准入状态。

正式重新投稿前仍需共同硬件双侧交流测量、真实 SLA/拓扑、同口径省级物理输入、历史决策时信息、固定投资完整留出期验证、最终 SI、补充数据、成套图件和新版投稿信。

## 复核入口

```bash
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/analysis/verify_mlperf_power_pair.py
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/drafts/build_manuscript_v17.py
/Users/apple/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 work/research/analysis/verify_manuscript_v17.py
```
