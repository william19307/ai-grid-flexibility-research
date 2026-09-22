**未决水电技术分类：来源线索，尚未用于修改模型｜2026-09-22**

原始机组库中的 ID、中文名及坐标已核对。不能根据下面的检索线索直接填补调节性能、储能量或当前运行状态。

- G100000601204：塔勒德萨依，80 MW，新疆，43.4205, 83.0633。国家能源局刊载的[建设方访谈](https://www.nea.gov.cn/2011-08/19/c_131069060.htm)确认其属于喀什河梯级开发项目；[尼勒克县 2026 防汛责任通知](https://www.xjnlk.gov.cn/xjnlk/c112936/202603/7be4cdeb7b8b43e08877b17b5a43c1a1.shtml)确认该电站水库大坝及运营主体。需要继续取得设计/环评或运营方技术资料来确认调节能力；目前仍保持 unknown。
- G100001051222：云贵桥，45 MW，云南，27.3871, 104.0154。[GEM 资料页](https://www.gem.wiki/Yunguiqiao_hydroelectric_plant)列出运营方、2014 年投运及洛泽河位置，但没有给出技术类型。[UNFCCC 的 2011 年项目意向记录](https://cdm.unfccc.int/methodologies/Projects/PriorCDM/notifications/index_html?s=5960)可按 Luoze River Yunguiqiao Hydropower Project 查找，当前取得的是意向列表，不能代替项目设计文件。GEM 所引政府页面与工程公司 ynjlx.com/public_show.aspx?id=386 在本次工具读取中失败，未据此认定链接永久失效。
- G100000601037：密云，原库 92 MW，北京，40.5048, 116.9394。原字段为 conventional and pumped storage，必须按机组拆分且核查当前状态，不能全部当成常规水电或全部当成抽蓄。当前三个目标省的直接邻省集合不涉及北京，但全国数据门槛仍保留这一未决项。

这些是后续数据工作的具体入口，不是需要等待外界回复的阻塞；其他修订工作可继续。

后续补证：已从 UNFCCC 注册项目 8507 / 6524 的设计与监测文件取得技术描述；云贵桥出现 45/56 MW 容量冲突，塔勒德萨依设计文件明确径流式。参见 `primary_document_audit_20260922.md` 和 `primary_document_candidates.json`。这两项是新增证据候选，尚未覆盖冻结分类或关闭水量门槛。
