# 显式来源版本下的独立复算

前置：按阶段 27 的 RUNBOOK 建立网络克隆、隔离 Python 环境并恢复其余输入。原模式的最终报告仍应为 13/14；不能把甘肃当前页面写到原文件名或改旧预期哈希。

在独立克隆中执行（P 指向该克隆的隔离环境 Python；示例沿用 `.venv`）：

```bash
.venv/bin/python work/research/analysis/fetch_reviewed_tariff_version.py --fetch
.venv/bin/python work/research/analysis/validate_demand_cohort.py --reviewed-tariff-version --output-dir work/tmp/reviewed_tariff_version/cohort
.venv/bin/python work/research/analysis/validate_fixed_cohort_factorial.py --reviewed-tariff-version --output-dir work/tmp/reviewed_tariff_version/factorial
```

输出目录必须全新或为空，不能覆盖原有证据；再次执行时选择新的目录。上述标准目录名对应本轮比较脚本。下载器只接受已审读的单个新版本，另存为 `gansu_reviewed_20260923.html`。若服务器再次改变字节，应停止并重新审读，不接受“看起来类似”的新页面。默认入口仍坚持原文件，新版本须用明确参数启用，真实采用的替代来源、原/新哈希和审读记录哈希随轨迹证明保存。

本轮在 9b9ce89 网络检出上执行这些数值入口，仍使用阶段 27 的隔离环境。随后在主研究树用同一隔离 Python 执行 `work/research/analysis/compare_reviewed_source_replay.py --checkout /absolute/path/to/independent-checkout`，比较独立输出并复制派生证据到阶段 28 目录。比较器不会填补原数据或修改认证文件；它确认四张数值 CSV、完整 192h 账目和 18 条因素记录的数值/时钟/来源证书一致，单列新增来源证明导致的哈希变化。

源版本审读和准入变异检查可由主研究树运行 `audit_reviewed_tariff_version.py --new-file /path/to/new-version.html` 与 `validate_reviewed_tariff_version.py --new-file ...`；二者需要原历史文件作为比较参照。这个旧文件仍只在原研究环境保留，不声称能从当前网站恢复。新克隆使用已发布的审读证据，并自行检查新版本哈希、脚本和其余字节哈希，因此这部分是有证据的来源版本准入，不是独立重新取得原历史文件。

本轮旧模式仍为 13 个原字节输入通过、1 个原 HTML 缺失；新模式为 13 个原字节输入加 1 个显式审读版本全部准入。不要把二者混写成“14 个原始文件均从网上恢复”。检查沿用已认证轨迹，没有重新优化全部 108 个任务案例，也没有证明第二台机器/操作系统、真实功率或全年电网结果。
