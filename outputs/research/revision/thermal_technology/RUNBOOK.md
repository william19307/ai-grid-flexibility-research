# 阶段 33：技术、用途与投资角色分离

本阶段是可执行的输入整理与拒绝准入流程，不是省级调度入口。不导入或运行旧省级程序，只用 AST 读取两个旧发电机定义的位置。

从仓库根目录执行（Python 标准库；不需要新增求解器依赖）：

```bash
python work/research/analysis/build_thermal_technology_staging.py --output-dir work/tmp/thermal-stage33-replay
python work/research/analysis/audit_thermal_unit_labels.py --output-dir work/tmp/thermal-stage33-replay
python work/research/analysis/validate_thermal_technology_staging.py --input-dir work/tmp/thermal-stage33-replay
```

须先按阶段 23 清单恢复原成本 CSV 及 GEM 工作簿，哈希在 input_consistency/source_hashes.json。构建器同时核对跟踪的 109 行来源表哈希。输出完整 fleet_staging.json、原参数说明、分类小计、投资角色条件算术、日期格式名称审计及 36 项检查。新版来源必须独立审读，不能无解释地修改预期哈希。

源记录逐字段保留，稳定 GEM ID 是关联键。19 个名称单元格使用原始数值加 Excel 内置日期格式 16（d-mmm）；代码独立按 1900 日期系统重建，与准备表一致。这证明日期格式来源，不证明原本应当叫“1-1”或某个特定编号。切勿把机组名称中的日期当 Start year。

`thermal_technology.stage` 返回待核实清单。`require_dispatch_ready` 在本版本始终不能生成实证机组输入：发现缺项时解释缺项；即使手工清空缺项或改 ready 字段，也要求另行审读的运行输入编译器。它不保护所有旧代码入口；旧省级程序保持历史用途，不能绕过本记录发布新实证结果。

现有候选机组的新建容量权限为零；这是避免对同一资产追加未声明容量的模型角色约定，不是禁止真实电厂扩建。未来扩建应新增带政策/机型/位置/上限来源的选项。三个 OCGT 选项只保留旧情景的技术候选：既有容量为零、是否允许及上限未知。它们不是已获批项目或三省必然需要新建燃机的结论。

下一步先用原始项目许可/机组清单核清日期格式名称和用途，再获取或明确界定供热、燃料与净电表、可用率/启停/爬坡、2030 存续情景与建设权限。不能把年度平均效率或通用 CHP 示例当作机组实测。真实全套输入仍为零；本阶段未运行省级重算。

上述三步已在另一输出目录实际执行；7 份产物逐字节一致，见 replay_comparison.json。
