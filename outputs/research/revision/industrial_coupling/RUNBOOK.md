# 阶段 31 复现与接手

本阶段只用合成输入。所需运行环境与固定依赖见 `../clean_reconstruction/` 对应说明及仓库 REPRODUCE；本机实际使用 `work/figure-env/bin/python`。以下 `python` 指已安装 NumPy/SciPy 的同一个解释器。从仓库根目录执行，不加 `-O`（检查包含 assert）。

## 独立输出目录复算

```bash
python work/research/analysis/validate_industrial_coupling.py --output-dir work/tmp/industrial-stage31-replay
python work/research/analysis/compare_industrial_regression.py --scratch work/tmp/industrial-stage31-regression --output work/tmp/industrial-stage31-comparison.json
```

第一条输出 47 项检查、19 次求解、全部案例输入/结果及实现哈希。第二条要求 scratch 尚不存在；从 Git 提取固定基线 `e936ef6bbce7e8a4ef32c19149a9cad0aa2a759b` 的源文件，以同一解释器分别启动三组基线/当前进程，再比较结果。完整克隆需要包含此历史提交；浅克隆应先获取对应历史。这里只忽略模型来源哈希字段，不能忽略数值、检查名或其他元数据。保留日志，不覆盖历史输出。

`regression/comparison.json` 是最初六进程验证；`replay_comparison.json` 是新增可复用比较器对原输出的重比；`runbook_comparison.json` 是实际执行第二条完整流程的验证。三者职责不同，不计为独立科学样本。

## 实际输入准入

入口为 `solve(..., industrial_sites=[IndustrialSite(...)])`；完整可运行合成配置见验证脚本及 analytic_cases.json。空列表保持原接口与结果结构。所有燃料、厂用电、放散、存储、成本/排放系数和接口序列须显式传入。现场未知值不能抄合成零值。

工业私有节点只通过一个有符号净进口接口连接公共节点；`Scenario.load_mw` 在该节点必须是排除发电厂用电的毛生产负荷。公共节点负荷必须同时排除已单列的这一工业负荷，不能把全省净购电、全省毛负荷与该私有节点重复相加。模型检验声明的计量口径，但不能从声明字符串核实实际统计口径。

下一步取得厂区同步煤气、机组毛/净输出、生产负荷、净购售电、运行/供热/停运与热值资料，再形成带出处的输入包。阶段 29/30 机组台账仍未转换为求解器参数。无新省级收益结果；原稿、历史省级结果及天气采集暂停均保留。
