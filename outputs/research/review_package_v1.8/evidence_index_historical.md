# v1.5 审读稿证据索引

本索引说明当前主文中的 E1–E6 对应什么证据。阶段记录是研究过程证据，不是同行评议文献；引用时仍需完成正式文献综述和参考文献审计。

证据基线为 Git 提交 `f4bd66b564e50d0a7e30d5f4cca6ebe522b5df33`。仓库地址：<https://github.com/william19307/ai-grid-flexibility-research/tree/f4bd66b564e50d0a7e30d5f4cca6ebe522b5df33>

## E1 固定服务重放

- 本包：`stages/阶段05_真实任务整组回放.md`、`stages/阶段06_跨时间与功率曲线验证.md`
- 方法稿：`methods/service_replay_methods_draft.md`
- 支持范围：固定任务工作量、连续执行、显式完成基准、聚合 GPU 容量和跨时间冻结重放。
- 不支持：物理放置、通信拓扑、真实 SLA、整机功率或在线部署。

## E2 四政策单元与归因边界

- 本包：`stages/阶段07_固定服务下的政策归因.md`
- 方法稿：`methods/policy_attribution_methods_draft.md`
- 支持范围：108 个条件、432 份构造排程、确定性成本上下界和归因区间。
- 不支持：独立统计重复、全局最优构造解、真实客户账单或省级系统成本。

## E3 需求群体记账

- 本包：`stages/阶段24_AI群体需求记账与容量反例.md`、`stages/阶段25_峰荷证据与旧敏感性混杂审计.md`、`stages/阶段26_固定群体与负荷形状独立控制.md`
- 方法稿：`methods/demand_cohort_methods_draft.md`、`methods/fixed_cohort_factorial_methods_draft.md`
- 支持范围：嵌入与增量群体的统一账本、负背景拒绝、192 小时完整轨迹、容量结论反转的解析反例。
- 不支持：0.5 kW/GPU、0.41 空闲比和 3 MW 背景作为江苏实测值。

## E4 机制与决策时信息

- 本包：`stages/阶段20_机制比较信息与采购目标修正.md`、`stages/阶段21_机制响应电网联算与非线性边界反例.md`、`stages/阶段22_决策时信息来源与预测版本准入.md`
- 方法稿：`methods/mechanism_grid_methods_draft.md`、`methods/mechanism_information_methods_draft.md`、`methods/forecast_information_methods_draft.md`
- 支持范围：采购时信息和事后评价分离、固定响应联算、含启停成本时线性端点失效的反例。
- 不支持：某一种采购机制在现实中普遍优越，或事后影子价格是可部署市场价格。

## E5 可再生能源时间验证

- 本包：`stages/阶段18_实际年度发电量与跨年校准检验.md`、`stages/阶段19_季度观测揭示年度误差抵消.md`
- 方法稿：`methods/renewable_temporal_validation_methods_draft.md`
- 支持范围：固定 2022 校准下的年度与季度误差诊断，以及年度误差可能被季节误差抵消的事实。
- 不支持：企业口径季度披露等于省级逐小时风电计量。

## E6 技术、用途与资产身份

- 本包：`stages/阶段23_2030输入口径与燃气技术错配.md`、`stages/阶段29_工业自备发电与电网调节边界.md` 至 `stages/阶段35_阜宁项目别名与重复容量记账.md`
- 方法稿：`methods/thermal_technology_methods_draft.md`、`methods/captive_generation_methods_draft.md`、`methods/asset_identity_methods_draft.md`
- 支持范围：源记录追踪、CCGT/工业煤气机组分离、CHP 未知状态保留、阜宁别名候选合并及 200 MW 记账影响。
- 不支持：完整 2030 在运机组组合、实际运行参数、供热义务、工业净外送能力或 GEM 官方勘误。

## 复现边界

本包收录的是可读文稿和研究记录快照。完整重算仍需按仓库根目录 `REPRODUCE.md` 恢复受许可约束或体积较大的外部原始数据、准备数组和运行环境。哈希只能证明版本一致，不能证明来源内容准确。
