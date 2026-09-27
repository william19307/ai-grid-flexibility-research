"""Assemble corrected review materials without promoting missing field evidence."""
from pathlib import Path
import csv,json,hashlib,shutil,sys
from build_current_paper_docx import build

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/review_package_v1.8'
REV=ROOT/'outputs/research/revision'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'figures').mkdir(exist_ok=True)
(OUT/'data').mkdir(exist_ok=True)
(OUT/'field_intake').mkdir(exist_ok=True)
summary=json.loads((REV/'mlperf_power_corrected/audit_summary.json').read_text())
text=(REV/'manuscript_v1.7/core_paper_en_v1.7_review.md').read_text()
text=text.replace('Revision v1.7 power-boundary review edition','Revision v1.8 corrected review edition').replace('Evidence consolidated through revision stage 37','Evidence consolidated through revision stage 38')
text=text.replace('the stage 37 public power-boundary audit','the stage 37 public power-boundary audit, corrected in stage 38')
text=text.replace('both arms have valid performance and accuracy records.','both arms have valid performance summaries and available accuracy records; accuracy thresholds were not independently revalidated.')
text=text.replace('Its submitted Yokogawa measurements report mean system input of 3.777–5.377 kW, with at least 600 one-second samples per row.', 'Our secondary extraction of the submitted Yokogawa aggregate power samples within the logged LoadGen start/end windows gives sample means of 4.115–5.960 kW, with at least 600 samples per row. These replace the broader-session means in v1.7. Four inherited GPU power caps were also corrected to 450 W; the paired performance ratios are unchanged. This extraction is not an official benchmark recertification and does not independently establish clock synchronization or a shared physical serial number.')
text=text.replace('E8. Revision stage 37 and mlperf_power_admission:', 'E8. Revision stages 37–38 and mlperf_power_corrected (superseding the stage 37 caps and session means):')
text=text.replace('and the public power-boundary audit at commit b6da0c7.', 'and the original public power-boundary audit at commit b6da0c7. Stage 38 corrects that extraction; the corrected source hashes and independent arithmetic checks are included in data/mlperf_source_manifest.json and data/mlperf_independent_verification.json.')
(OUT/'core_paper_en_v1.8_review.md').write_text(text)
si=(ROOT/'outputs/research/current_paper_20260927/01_current_revision/supplementary_information_v1.5_review.md').read_text()
si=si.replace('Revision v1.5 review edition','Revision v1.8 review edition').replace('Evidence consolidated through revision stage 35 (23 September 2026)','Evidence consolidated through revision stage 38 (27 September 2026)')
si=si.replace('The measurement protocol remains an outstanding deliverable for empirical admission.','The measurement protocol and empty intake tables are provided; physical measurements remain outstanding. On 27 September 2026 the authors\' project contact reported that no field data or equipment were currently available.')
si+='''

## S10 Corrected external benchmark extraction

The MLCommons Inference v4.0 repository is pinned to commit 343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef. We match the NVIDIA DGX-H100_H100-SXM-80GBx8_TRT and its MaxQ variant on benchmark, accuracy profile and scenario. System descriptions agree except for the system name. This establishes matching submitted descriptions, not independently inspected hardware identity.

Configuration classes are parsed as syntax trees without executing vendor code. An absent local power_limit assignment is resolved through the named parent class; unsupported or ambiguous inheritance is rejected. Four stage-37 rows were incorrectly assigned caps from other hardware classes: DLRM-v2-99.9 Offline/Server and Llama2-70b-99.9 Offline/Server all resolve to 450 W. Performance ratios are unaffected.

For each capped run, we read power_begin and power_end from mlperf_log_detail.txt and select aggregate Watts samples in run_1/spl.txt within the inclusive interval. We average the aggregate channel once; summing its component channels again would double count energy. Samples must be increasing, positive and cover both boundaries; no extrapolation is performed. Dates are parsed in the submitted month-day-year format. We use the timestamps as supplied without an inferred timezone shift. Clock synchronization remains dependent on the submission's measurement process.

The 24 window sample means range from 4.115 to 5.960 kW. These replace the v1.7 broader-session means of 3.777 to 5.377 kW, which included time outside the performance window. An independent decimal-arithmetic extraction reproduces every window mean within 1e-9 W and every sample count exactly. This tolerance checks arithmetic, not instrument uncertainty. These sample means are not common-horizon energy estimates or official recertified benchmark scores.

The complete Git tree contains no power-directory or spl.txt file under the matched standard-system result tree. Therefore paired AC savings remain unavailable. Accuracy files are present, but their model-specific thresholds were not independently rerun or validated. Shared runs across accuracy profiles are not independent repetitions.

Sources: MLCommons, Inference v4.0 result repository, https://github.com/mlcommons/inference_results_v4.0 (pinned commit above); MLCommons, Power measurement rules, https://github.com/mlcommons/inference_policies/blob/master/power_measurement.adoc (accessed 27 September 2026). The row-level source hashes accompany the correction record.

## S11 Prospective field evidence and placement validation

The field experiment has not been conducted. The intake requires both policy arms on a common node, all PSU AC inputs, fixed useful work, quality criteria, randomized paired repeats, full-window idle and control overhead, and a frozen stopping rule. The existing measurement protocol defines these requirements. Empty CSV headers are schemas, not measurements.

Service records must link each job to a versioned contract effective at arrival. Release, deadline, latency percentile or violation threshold, quality requirement, and the evidence source remain explicit. Historical completion plus an analyst-selected allowance cannot populate a contractual deadline field. Anonymous stable job and node identifiers preserve joins without publishing customer identities or contracts.

Placement validation additionally requires per-GPU identity and model, memory and availability, node membership, interconnect endpoints and link capacity, and timestamped job-device assignments. A gang must simultaneously obtain its required devices; communication and memory constraints must be checked on that placement. Aggregate free-GPU counts alone do not prove deployability. No actual contract or topology record is present in this edition.

## S12 Provincial input admission and full-year evaluation

Before a provincial experiment, the load series must have a documented statistical boundary, units, timezone, actual calendar, and embedded-versus-incremental AI cohort treatment. A historical shape scaled to an annual total is a constructed series, not measured hourly demand. Province-level assets require matched identity, technology, capacity vintage, retirement/commissioning status and operational constraints. Gross industrial capacity is not net grid export. Heat obligations and shared process fuel remain mandatory where applicable. Exchanges require directional capability and simultaneous flow or explicitly stated scenario constraints. Reservoir inflow, usable storage, head/efficiency and release requirements must refer to compatible physical boundaries.

Renewable profiles require matched onshore/offshore/PV technology, equipment assumptions, capacity vintage, meteorological source, conversion and losses, and observations with the same fleet and meter scope. Annual agreement alone cannot validate hourly reliability. None of the existing candidate lists closes all of these admission requirements. The accompanying provincial register records what exists and what is missing; it is not a replacement input dataset.

The prospective evaluation sequence is: (1) admit and hash inputs, define the training/test split and record all previous exposure; (2) choose policies, hyperparameters and investment using development data only; (3) freeze generation, network and storage investment; (4) evaluate every hour of each test year without investment refitting; (5) retain energy-state continuity and initial/terminal conditions, serve the same workload, and record infeasible and unresolved cases; (6) report minimum unserved energy, shortage hours, cost, emissions, service violations and solver gaps; (7) evaluate predeclared stress and outage scenarios. A leap year has 8,784 hours; otherwise 8,760.

The implemented annual evaluator first minimizes unserved energy, then minimizes operating cost at that shortage level. Synthetic tests exercise complete years, binary commitment and cross-midnight storage. They do not establish empirical provincial reliability. Perfect-foresight dispatch is an optimistic diagnostic and cannot replace causal dispatch using archived forecasts. Deterministic shortage hours are not stochastic LOLE. A stochastic adequacy claim additionally needs outage distributions, dependence and a defined sampling/uncertainty procedure.

No untouched test year is designated here: weather from 2015–2024 has already been inspected. A future holdout or independently sequestered dataset must be selected before its outcomes are examined. Any evaluation of already examined periods must be labeled retrospective or exploratory. Full-year provincial validation remains unexecuted because its physical inputs are not admitted.

## S13 Supplementary data contents

Supplementary Data 1 is a review workbook with a gate register, 108 certified conditional factorial outcomes, 24 corrected external benchmark rows and a provincial input register. These are distinct evidence types. Percent columns inherited from the factorial output store percentages on a 0–100 scale, whereas performance retention is a ratio (0–1). Missing measured energy and empirical provincial results are not represented as zero. Complete CSV copies and file hashes accompany the workbook. Data and manuscript finalization requires resolution of the remaining gates.
'''
(OUT/'supplementary_information_v1.8_review.md').write_text(si)
cover='''# Cover letter for Nature Energy

Draft for author review — not cleared for submission | 27 September 2026

Dear Editors,

We are preparing a substantially revised manuscript entitled “Service constraints and power boundaries shape the grid value of flexible AI computing”. This draft relates to manuscript NENERGY-26093649; the appropriate route for any revision must follow the journal's actual decision and instructions.

The study examines the conditions under which changes in AI operating mode and task timing can be interpreted as energy-system flexibility. A controlled four-policy comparison holds the task cohort and completion conditions fixed. Across 108 conditional GPU-model configurations, the attribution depends strongly on the allowed completion window; lower modeled energy use can coexist with higher hourly GPU demand. Analytical counterexamples show how cohort double counting can reverse a capacity conclusion and how linear procurement-response extrema can miss nonlinear commitment costs.

We believe that a fully validated version of this work could interest Nature Energy readers by clarifying the evidence needed to translate computing flexibility into power-system value. The present findings are conditional modeling and source-audit results. They do not yet demonstrate measured paired whole-node energy savings, production-SLA compliance or validated provincial capacity benefits. The revision must obtain these missing measurements and physical inputs and complete fixed-investment full-year evaluation before a submission-ready claim can be made.

This letter will be finalized only after the empirical results, uncertainty, reproducibility materials and final author declarations are complete. All-author approval, competing interests, related submissions and the status of the existing manuscript require confirmation; no declaration is made here on the authors' behalf.

Sincerely,

William Wei and Lanlan Liu

Correspondence: qkfp0742@leeds.ac.uk
'''
(OUT/'cover_letter_nature_energy_DRAFT.md').write_text(cover)
gates=[
 ['G1','Paired whole-node AC measurement','missing','No field data or equipment available (user, 2026-09-27)','Both arms; equal work/quality; full horizon; repeated uncertainty'],
 ['G2','Actual SLA and topology','missing','Historical trace and aggregate gang feasibility only','Versioned contract; devices; links; timestamped assignments'],
 ['G3','Provincial physical inputs','incomplete','Candidate inventories and scope audits','Admitted load, generation, heat, water, exchanges and renewable observations'],
 ['G4','Full-year held-out validation','not executed','Annual evaluator has synthetic checks only','Freeze investments and evaluate admitted unseen or explicitly retrospective years'],
 ['G5','Final SI and supplementary data','review draft','Corrected SI and review workbook supplied','Regenerate from final admitted empirical results'],
 ['G6','Final cover letter','draft','Existing submission ID retained; no new submission','Final findings and author/editorial declarations']]
with (OUT/'data/evidence_gates.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['gate_id','requirement','status','available_evidence','completion_requirement']);w.writerows(gates)
inputs=[
 ['Load','2018 hourly source; 2020 annual calibration','Same-year hourly scope; AI embedded boundary','tables/china_load_input_audit.csv'],
 ['Thermal identity','107 candidate assets, 24759 MW after one alias adjudication','Remaining identity, vintage and retirement confirmation','revision/asset_identity/asset_candidates.json'],
 ['Thermal operation','Technology and CHP classifications','Heat demand; min output; ramp; startup; outage; heat-rate evidence','revision/thermal_technology/fleet_staging.json'],
 ['Industrial supply','12 by-product-gas units; shared-fuel model implemented','Site load, gas supply, auxiliaries, storage and net grid exchange','revision/captive_operating/annual_energy_disclosures.csv'],
 ['Reservoirs','Hydro classification and annual water-source audits','Compatible hourly inflow, usable storage, head and release rules','tables/major_hydro_annual_source_volume_m3.csv'],
 ['Pumped storage','Separated from natural-inflow supply','Observed efficiency, duration and operating boundary','revision/阶段01_抽水蓄能修正.md'],
 ['Wind and solar','Technology/vintage recovery; limited site diagnostics','Matched fleet and hourly observations; calibrated conversion/losses','revision/weather_site_technology/archived_sites_with_technology_and_vintage.csv'],
 ['Interprovincial exchange','Published line inventory and conflict checks','Study-year directional capability and operating constraints','tables/china_transmission_identity_checks.csv'],
 ['Forecast information','Decision-time interface exists','Timestamped archived participant-visible forecasts','revision/阶段21_固定响应与非线性系统成本.md'],
 ['Holdout provenance','Previously inspected weather years recorded','Untouched period or explicit retrospective designation','revision/fixed_fleet_annual/validation.json']]
with (OUT/'data/provincial_input_register.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['input_group','available','missing_for_admission','evidence_path_from_outputs_research']);w.writerows(inputs)
# Do not silently retain a guessed filename in the register.
for row in inputs:
 if not (ROOT/'outputs/research'/row[3]).exists():
  row[3]='revision/REVISION_STATUS.md'
with (OUT/'data/provincial_input_register.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['input_group','available','missing_for_admission','evidence_path_from_outputs_research']);w.writerows(inputs)
for src,dst in [(REV/'policy/certified_factorials.csv','conditional_factorials.csv'),(REV/'mlperf_power_corrected/matched_results.csv','external_power_corrected.csv')]:
    shutil.copy2(src,OUT/'data'/dst)
for name in ['source_manifest','independent_verification','audit_summary']:
 shutil.copy2(REV/f'mlperf_power_corrected/{name}.json',OUT/f'data/mlperf_{name}.json')
for f in (REV/'measurement').iterdir():
 if f.is_file():shutil.copy2(f,OUT/'field_intake'/f.name)
schemas={
 'service_contracts.csv':'contract_id,version,effective_from_utc,effective_to_utc,workload_class,metric,threshold,unit,quality_rule,source_sha256',
 'jobs.csv':'job_id,contract_id,contract_version,arrival_utc,deadline_utc,required_gpus,memory_gb_per_gpu,work_fingerprint,quality_result',
 'devices.csv':'device_id,node_id,gpu_model,memory_gb,available_from_utc,available_to_utc,source_sha256',
 'links.csv':'link_id,endpoint_a,endpoint_b,link_type,capacity_gbps,valid_from_utc,valid_to_utc,source_sha256',
 'allocations.csv':'job_id,device_id,start_utc,end_utc,source_sha256'}
for name,header in schemas.items():(OUT/'field_intake'/name).write_text(header+'\n')
for src in [REV/'manuscript_v1.7/figures/fig1_policy_attribution.png',ROOT/'outputs/research/current_paper_20260927/01_current_revision/figures/figS1_quarterly_diagnostic.png']:
 shutil.copy2(src,OUT/'figures'/src.name)
for stem,title in [('core_paper_en_v1.8_review','AI flexibility | corrected review'),('supplementary_information_v1.8_review','Supplementary information | review'),('cover_letter_nature_energy_DRAFT','Cover letter | draft')]:
 build(OUT/(stem+'.md'),OUT/(stem+'.docx'),title,subject='Revision v1.8; not submission-ready')
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
letter=Document(OUT/'cover_letter_nature_energy_DRAFT.docx')
for paragraph in letter.paragraphs:
 paragraph.alignment=WD_ALIGN_PARAGRAPH.LEFT
letter.save(OUT/'cover_letter_nature_energy_DRAFT.docx')
shutil.copy2(ROOT/'outputs/research/current_paper_20260927/03_research_records/证据索引.md',OUT/'evidence_index_historical.md')
readme='''# 当前论文与补证交接包 v1.8

日期：2026-09-27。**这是修订审读包，尚不能作为最终投稿文件。**

用户已确认暂无现场数据或设备。双侧交流功率测量、实际 SLA 和拓扑仍缺；省级物理输入未完整准入，全年留出期省级验证未执行。文档生成不代表这四项已完成。

本包包含纠错主文、扩展 SI、补充数据审读表、投稿信草稿、原始记录接收空表和来源哈希。原投稿 v1.4 不变。v1.7 中 4 条功率上限及单侧功率均值口径由本版更正；24 条窗口功率均值已独立复算。

阅读顺序：主文 → SI 的 S10–S13 → 补充数据 → data/evidence_gates.csv。field_intake 是空表，不能作为实验数据。CSV 是机器读取数据副本；Excel 是供审读的同源展示。

补证执行：先落实可开展交流整机测量的合作实验室/平台及真实服务授权；由现场依协议填写硬件、仪表、工作与质量、服务、随机化和重复方案，再冻结确认实验。公开 GPU 遥测不能替代该采集。省级输入按 data/provincial_input_register.csv 逐项准入，之后才能冻结投资开展完整年份验证。没有承诺可凭现有材料自动完成真实实测。

投稿信保留稿号和未完成状态，不发送、不代作者声明批准或排他投稿。最终 SI、数据和信须随最终结果重新生成并审读。
'''
(OUT/'README.md').write_text(readme)
payload=[]
for name,file in [('Evidence gates','evidence_gates.csv'),('Conditional factorials','conditional_factorials.csv'),('External power','external_power_corrected.csv'),('Provincial inputs','provincial_input_register.csv')]:
 with (OUT/'data'/file).open() as f:matrix=list(csv.reader(f))
 for row in matrix[1:]:
  for i,value in enumerate(row):
   try:row[i]=float(value) if any(c in value for c in '.eE') else int(value)
   except ValueError:pass
 payload.append(dict(name=name,rows=matrix))
(ROOT/'work/tmp/evidence_workbook_v18.json').write_text(json.dumps(payload))
print(OUT)
