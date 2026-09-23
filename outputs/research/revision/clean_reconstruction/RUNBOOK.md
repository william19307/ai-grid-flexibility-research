# 独立目录恢复与认证复算

这一入口覆盖阶段 24/26 所需的原始轨迹、证书依赖和背景负荷，不覆盖全部论文原始数据。它是复现审计，不能修补物理校准、实际 SLA 或全年可靠性证据。

## 从网络建立新副本

选择一个不存在的目录，在该副本中执行。不要指向日常研究目录，不复制旧 sources/prepared 或运行环境。

```bash
git clone --depth 1 --branch codex/research-evidence-revision https://github.com/william19307/ai-grid-flexibility-research.git research-reconstruction
cd research-reconstruction
git rev-parse HEAD
python3.14 -m venv .venv
.venv/bin/python -m pip --isolated install --no-cache-dir --index-url https://pypi.org/simple -r work/research/requirements-reconstruction.txt
.venv/bin/python work/research/analysis/restore_certified_inputs.py --fetch
```

记录实际提交与依赖版本。阶段 27 首次尝试的入口提交为 `3ffe061`，数组 C 顺序修正为 `a8c2003`。本轮最终为 13/14 项准入，甘肃原始页面未恢复，完整认证复算未执行。现有输出和证书来自 Git；它们只是待比较的历史结果，不等于已重新求解。Python 3.14 解释器本身需自行安装；本次检查使用同一台 Mac 上的新隔离环境，不宣称验证了另一机器或操作系统。

恢复器只读取版本固定的公开输入，保留许可/引用信息的入口见 `source_spec.json`、原始注册表和 Helios 上游仓库。压缩包仅提取白名单中的数据成员，不执行上游代码。PyPSA 大包只读取必要范围，核对成员名称、长度、CRC32 和 SHA256，不宣称校验了整个 16.9 GB 包。原始文件保持 Git 排除；输出报告默认为 `work/tmp/reconstruction/input_restore.json`。

非零退出码表示输入链未恢复完整。检查报告中每个失败，不应修改冻结哈希、删去输入依赖或用原研究目录文件填补后仍称从零恢复。可以在有合法可用的原件后另作清楚标注的离线恢复，但必须保留本次网络失败记录。源页面改版须重新审计、建立新版本，不能静默替换原证书。

## 输入全部通过后

先在新副本里保留 Git 原有输出的独立比较快照，再运行以下入口；这些验证脚本会重写本副本对应阶段的产物，因此不在原研究树里运行独立复现。

```bash
.venv/bin/python work/research/analysis/validate_demand_cohort.py
.venv/bin/python work/research/analysis/validate_fixed_cohort_factorial.py
git diff -- outputs/research/revision/demand_cohort outputs/research/revision/fixed_cohort_factorial
```

应比较实际数值、完整场景数量和哈希，不仅查看退出码。这仍是同一算法和既有任务证书的重新执行，没有重新优化全部 108 个案例，不能称为独立算法复核或整篇论文重现。只有全部输入认证、数值复算及结果比较都有实测记录，才关闭这一小段复现门槛。

若原始输入无法恢复，仍可在隔离环境中运行不依赖外部数据的数学检查，但应单列为环境/模型可运行性证据，不将其计为认证链成功：

```bash
.venv/bin/python work/research/analysis/validate_thermal_commitment.py --output-dir work/tmp/reconstruction/commitment
.venv/bin/python work/research/analysis/validate_coupled_grid_compute.py --output-dir work/tmp/reconstruction/grid
.venv/bin/python work/research/analysis/validate_reservoir_coupling.py --output-dir work/tmp/reconstruction/reservoir
```

已下载输入经过校验后，仅重建数组可运行 `restore_certified_inputs.py --rebuild-only --report work/tmp/reconstruction/input_rebuild.json`；这不执行网络请求，也不豁免全部输入的最终检查。必须保留初次失败报告，不用新的尝试覆盖它。当前公开甘肃入口返回不同版本，恢复器会按原哈希拒绝；状态详见阶段报告。
