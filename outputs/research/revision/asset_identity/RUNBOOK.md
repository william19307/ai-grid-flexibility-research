# 阶段 35：从数据库行到候选物理资产

本阶段以明确审读的别名组修正重复容量记账。它不修改阶段 23/33 原件与历史输出，不执行省级模型，不联系数据库作者。

```bash
python work/research/analysis/build_asset_identity_staging.py --output-dir work/tmp/asset-identity-stage35-replay
python work/research/analysis/validate_asset_identity.py --input-dir work/tmp/asset-identity-stage35-replay
```

构建器需要 openpyxl（本机验证版本 3.1.5），验证器仅需标准库。本机使用 `work/figure-env/bin/python` 运行构建器。先恢复阶段 23 的 GEM 工作簿及本目录 `source_access_log.json` 中标为 `raw_snapshot` 的三个 HTML，并逐一核对哈希。失败页面不必恢复，也不能伪装成已恢复的原件。旧 permalink 返回 403 后，成功取得两个 GEM 当前页面，其实际 revision IDs 为 1280775 和 1280776；不能混作 web 缓存中更早的 1061629/1061631。

`adjudication.json` 是人工研究判定的权威输入，绑定原阶段 33 清单哈希。只有其中明确列出的组可以合并；程序不会按距离、名称相似或容量相同自动去重。四条阜宁原记录分别按 1/1 与 2/2 对应，保留全部 ID、来源行与坐标/股权等冲突。原数据库无修改，其他 105 条记录仍按未经完整身份核查的候选保留。

`asset_candidates.json` 的来源记录通过 `source_staging_path` 与哈希引用完整历史清单；`source_units` 覆盖全部 109 条。它提供 107 个候选资产、24,759 MW，一次性扣除阜宁重复计数 200 MW。95 个 CCGT 候选共 23,634 MW，其中 80 个 CHP=yes、17,653 MW，15 个 CHP 未知、5,981 MW；12 个工业副产气候选、1,125 MW 不变。未来 OCGT 选项和归档条件参数不变，所有候选仍不具备调度准入。

`selected_identity_fields.json` 保留 109 条原身份元数据及工作簿行号。`identity_screen.json` 仅作检索辅助：不同 location ID、同省/技术/单机容量/投产年份且距离不超过 5 km。本轮只检出阜宁项目对；该规则不覆盖所有别名、坐标错误、年代差异或其他能源技术，不证明余下容量已无重复。

11 项来源/元数据检查与 23 项分组/算术/错误输入检查分别记录。后者含独立并查集重建、全量 provenance 恰好一次覆盖、合并顺序不变、无审读不自动合并、跨编号/容量/省份/供热冲突拒绝及投资角色保留。它们证明实现与输入规则一致，不替代物理身份的独立确认。

下一步继续补设备/许可与热电运行参数，核对其他候选资产的唯一性和需求统计边界。若新原始证据支持另一独立项目，必须新增审读决定并重新构建；不得手工给旧重复记录赋零容量或覆盖原始字段。省级收益和可靠容量必须在完整物理输入就绪后重算。

完整两步已在另一输出目录复跑，7 份产物逐字节一致，见 `replay_comparison.json`。这不属于第二机器验证或新增物理观测。
