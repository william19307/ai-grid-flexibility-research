#!/usr/bin/env python3
"""Build the literature-integrated v1.6 review manuscript from v1.5."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from build_current_paper_docx import build as build_docx


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "outputs/research/current_paper_20260927/01_current_revision/core_paper_en_v1.5_review.md"
SOURCE_FIGURE = ROOT / "outputs/research/current_paper_20260927/01_current_revision/figures/fig1_policy_attribution.png"
OUT = ROOT / "outputs/research/revision/manuscript_v1.6"
TARGET_MD = OUT / "core_paper_en_v1.6_review.md"
TARGET_DOCX = OUT / "core_paper_en_v1.6_review.docx"
EVIDENCE_COMMIT = "510780e9ead27698e33cedf24df5a5a171a8f11b"


REFERENCES = """## References

1. Colangelo, P. et al. AI data centres as grid-interactive assets. Nat. Energy 11, 254–261 (2026). https://doi.org/10.1038/s41560-025-01927-1

2. Williams, C. et al. Power-flexible AI data centers: a new paradigm for grid-responsive compute. Preprint at https://arxiv.org/abs/2606.25098 (2026).

3. Caprara, A., Yu, Y., Teng, F., Junyent-Ferré, A., Bullich-Massagué, E. & Aragüés-Peñalba, M. Data center workload flexibility for power system demand response: evidence from Alibaba traces. Int. J. Electr. Power Energy Syst. 178, 111940 (2026). https://doi.org/10.1016/j.ijepes.2026.111940

4. Senga, J. R. L., Wang, S. & Knittel, C. R. Flexible data centers reduce power system costs but can increase emissions. iScience 29, 116497 (2026). https://doi.org/10.1016/j.isci.2026.116497

5. Chen, Y. & Zheng, X. To defer or to shift? The role of AI data center flexibility on grid interconnection. In Proc. 2026 ACM Sustainability Week 322–327 (ACM, 2026). https://doi.org/10.1145/3765611.3815593

6. Dunlap, C. Quantifying AI data center flexibility as a resource adequacy asset. Research Square preprint https://doi.org/10.21203/rs.3.rs-9829457/v1 (2026).

7. Zheng, J., Chien, A. A. & Suh, S. Mitigating curtailment and carbon emissions through load migration between data centers. Joule 4, 2208–2222 (2020). https://doi.org/10.1016/j.joule.2020.08.001

8. Fridgen, G., Keller, R., Thimmel, M. & Wederhake, L. Shifting load through space: the economics of spatial demand side management using distributed data centers. Energy Policy 109, 400–413 (2017). https://doi.org/10.1016/j.enpol.2017.07.018

9. Zhang, Y., Li, H. & Wang, S. Decarbonizing data centers through regional bits migration: a comprehensive assessment of China's “Eastern Data, Western Computing” initiative and its global implications. Appl. Energy 392, 126020 (2025). https://doi.org/10.1016/j.apenergy.2025.126020

10. Birahim, S. A. A net-grid-benefit test for interconnecting AI data centres. npj Environ. Soc. Sci. 1, 8 (2026). https://doi.org/10.1038/s44432-026-00013-5

11. Zhang, W. & Zavala, V. M. Remunerating space–time, load-shifting flexibility from data centers in electricity markets. Appl. Energy 326, 119930 (2022). https://doi.org/10.1016/j.apenergy.2022.119930

12. Dvorkin, V. Agent coordination via contextual regression (AgentCONCUR) for data center flexibility. Preprint at https://arxiv.org/abs/2309.16792 (2024).

13. Hu, Q., Sun, P., Yan, S., Wen, Y. & Zhang, T. Characterization and prediction of deep learning workloads in large-scale GPU datacenters. In Proc. Int. Conf. High Performance Computing, Networking, Storage and Analysis 1–15 (ACM, 2021). https://doi.org/10.1145/3458817.3476223

14. Jiangsu Provincial Development and Reform Commission. Notice on transmission–distribution and retail tariffs of the Jiangsu grid for 2020–2022, Su-Fa-Gai-Jia-Ge-Fa [2020] No. 1183, Annex 3 (2020). https://www.njqxq.gov.cn/qxqrmzf/qxqfzhggj/202011/P020201111396651530459.pdf

15. Gansu Provincial Development and Reform Commission. Notice on adjusting retail tariffs and optimising time-of-use tariffs, effective 1 January 2021 (2020). http://www.gansu.gov.cn/art/2020/12/3/art_10359_474921.html

16. Guizhou Provincial Development and Reform Commission. Notice on improving the time-of-use tariff mechanism, Qian-Fa-Gai-Jia-Ge [2023] No. 481 (2023). https://fgw.guizhou.gov.cn/zwgk/zcwj/zcwj/202306/t20230628_80566840.html

17. Du, B. et al. Spatial LLM workload shifting needs foresight: model commitment for AI data center operation under power grid constraints. Preprint at https://arxiv.org/abs/2609.09787 (2026).

18. Stojkovic, J., Zhang, C., Goiri, Í., Torrellas, J. & Choukse, E. DynamoLLM: designing LLM inference clusters for performance and energy efficiency. In Proc. IEEE Int. Symp. High-Performance Computer Architecture 1348–1362 (IEEE, 2025). https://arxiv.org/abs/2408.00741

19. Hersbach, H. et al. The ERA5 global reanalysis. Q. J. R. Meteorol. Soc. 146, 1999–2049 (2020). https://doi.org/10.1002/qj.3803

20. Zippenfenig, P. Open-Meteo.com Weather API. Zenodo https://doi.org/10.5281/zenodo.7970649 (2024).

21. Wu, H. & Kan, X. Hourly electric power load and transmission data at the provincial level in China. Zenodo https://doi.org/10.5281/zenodo.8322210 (2023).

22. Zhou, X. PyPSA-China: V3.0. Zenodo https://doi.org/10.5281/zenodo.13987282 (2024).

23. Potsdam Institute for Climate Impact Research. Data bundle PyPSA-China-PIK: rasters and basic cutout, v1.1. Zenodo https://doi.org/10.5281/zenodo.16810831 (2025).

"""


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Expected one occurrence, found {count}: {old[:80]}")
    return text.replace(old, new, 1)


def citation_numbers(chunk: str) -> list[int]:
    numbers = []
    for match in re.finditer(r"\[([0-9,–-]+)\]", chunk):
        for token in match.group(1).split(","):
            if "–" in token or "-" in token:
                separator = "–" if "–" in token else "-"
                start, end = map(int, token.split(separator))
                numbers.extend(range(start, end + 1))
            else:
                numbers.append(int(token))
    return numbers


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    replacements = [
        (
            "Revision v1.5 review edition | 27 September 2026 | Evidence consolidated through revision stage 35 (23 September 2026)",
            "Revision v1.6 literature-integrated review edition | 27 September 2026 | Evidence consolidated through revision stage 36",
        ),
        (
            "**Manuscript status.** This edition assembles the supported revision findings and methods. It is not submission-ready and does not replace the submitted v1.4. Provincial system-benefit estimates, annual firm-capacity results and implementable market comparisons remain to be recomputed. The title and abstract are provisional. Author details are retained from v1.4.",
            "**Manuscript status.** This edition integrates the supported revision findings with the stage 36 literature and novelty audit. It is not submission-ready and does not replace the submitted v1.4. Provincial system-benefit estimates, annual firm-capacity results and implementable market comparisons remain to be recomputed. The title and abstract are provisional. Author details are retained from v1.4.",
        ),
        (
            "Flexible computing offers at least two decisions: how fast a job runs and when it starts. A lower-power mode can extend execution, while a different start time changes the load experienced by the grid. Calling one decision “efficiency” and the other “flexibility” does not by itself produce a physical decomposition of their value. The comparison also depends on the completion requirement, fixed background work, idle consumption, and the investment or dispatch decisions available to the electricity system.",
            "AI-computing flexibility is already an empirical capability. A 256-GPU field demonstration reported a 25% power reduction for three hours while maintaining stated quality-of-service guarantees [1], and a later 130 kW deployment reported rapid and sustained curtailment, carbon-aware operation and spatial shifting while preserving priority-job service levels [2]. Trace-based quantification also exists: a study of more than one million Alibaba tasks used observed queue latency to classify deferrable work and reported up to 22% modeled load reduction during response windows [3]. These studies establish technical capability, but their service definitions, task cohorts, power boundaries and information sets differ.",
        ),
        (
            "Our research asks when each decision contributes to lower resource use and when firms have incentives to deliver the response. We distinguish four evidence levels: recorded workload and infrastructure observations; counterfactual schedules under explicit assumptions; mathematical properties of the electricity model; and empirical system outcomes. Agreement at one level does not certify the next. In particular, reconstructing a task allocation is not a measurement of its counterfactual electrical power, and solving representative weeks does not establish annual resource adequacy.",
            "Power-system planning studies already show that temporal flexibility can change investment, operating cost, emissions and resource adequacy [4–6]. Spatial migration and regional computing allocation have long been studied [7–9], while interconnection obligations, market remuneration and signal-based coordination have also been proposed [10–12]. We therefore make no claim of first demonstrating flexible AI computing, first using production traces, first modeling system value or first proposing a coordination mechanism. The unresolved question addressed here is narrower: whether operating-mode and start-time decisions can be attributed on the same fixed task cohort and completion benchmark, and what additional evidence is required before that attribution becomes a physical grid-value claim.",
        ),
        (
            "The present revision replaces an unconditional attribution claim with a service-dependent question. It brings the scheduling comparison, whole-node accounting, supply model and procurement information set into a common framework. The results below report the portions currently supported by the revision evidence. The former provincial benefit ranges and gas-capacity avoidance estimates remain historical scenario outputs and are not carried into this edition as revised findings.",
            "Our contribution is a controlled boundary test. We compare four policy cells that differ only in start-time and operating-mode permissions while retaining the same work, GPU requirements, background allocations, prices and completion benchmark. We then test translation to the electricity system with two analytical counterexamples and with audits of power, demand and supply inputs. The results below report only the portions supported by this chain. The former provincial benefit ranges and gas-capacity avoidance estimates remain historical scenario outputs and are not carried into this edition as revised findings.",
        ),
        (
            "We retain the original GPU count and a work proxy equal to recorded GPU count multiplied by runtime. Every target job executes once in a continuous interval without preemption. Other recorded allocations remain fixed background. The completion benchmark is the historical end time plus an analyst-defined allowance of 0, 6 or 24 hours. This is a retrospective comparison, not a contractual service-level agreement inferred from queueing time [E1].",
            "We retain the original GPU count and a work proxy equal to recorded GPU count multiplied by runtime. Every target job executes once in a continuous interval without preemption. Other recorded allocations remain fixed background. The task cohort is drawn from four public Helios production clusters [13]. The completion benchmark is the historical end time plus an analyst-defined allowance of 0, 6 or 24 hours. This is a retrospective comparison, not a contractual service-level agreement inferred from queueing time [E1].",
        ),
        (
            "Feasible policy costs and relaxed lower bounds define deterministic identification intervals for the optimal attribution (Fig. 1). A mode majority in a constructed schedule does not establish a majority in the global optimum: five conditions remain unresolved. The bill includes fixed background and assumed idle GPU consumption; it is neither an actual customer bill nor a system-cost estimate. Historical tariff shapes are applied as declared hypothetical price conditions on the trace clock [E2].",
            "Feasible policy costs and relaxed lower bounds define deterministic identification intervals for the optimal attribution (Fig. 1). A mode majority in a constructed schedule does not establish a majority in the global optimum: five conditions remain unresolved. The bill includes fixed background and assumed idle GPU consumption; it is neither an actual customer bill nor a system-cost estimate. Historical tariff shapes derive from published provincial documents [14–16] and are applied as declared hypothetical price conditions on the trace clock [E2].",
        ),
        (
            "All arms retain a 192-hour domain, including the observed tail after the source week. The successful replay validates a schedule under aggregate GPU capacity and assumed curve transfer. It does not establish device placement, network topology, output quality, actual service contracts, online control or whole-node energy savings. The additional periods validate a frozen construction after earlier trace inspection; they are not a new prospective deployment experiment.",
            "All arms retain a 192-hour domain, including the observed tail after the source week. The successful replay validates a schedule under aggregate GPU capacity and assumed curve transfer. It does not establish device placement, model availability, network topology, output quality, actual service contracts, online control or whole-node energy savings. Those constraints are material in deployed demonstrations and inference-cluster studies [1,2,17,18]. The additional periods validate a frozen construction after earlier trace inspection; they are not a new prospective deployment experiment.",
        ),
        (
            "The revised mechanism comparison separates information available when a response is purchased from outcomes evaluated later. Fixed responses enter the same grid model with the same installed assets and background demand. Commitment and dispatch can change in response to load, but the response is not reselected after seeing the realized system outcome [E4].",
            "The revised mechanism comparison separates information available when a response is purchased from outcomes evaluated later. Earlier work already studies spatiotemporal remuneration and signal-based coordination [11,12]; our narrower test fixes the purchased response before realized grid outcomes are evaluated. Fixed responses enter the same grid model with the same installed assets and background demand. Commitment and dispatch can change in response to load, but the response is not reselected after seeing the realized system outcome [E4].",
        ),
        (
            "An exploratory offshore-wind diagnostic holds a 2022 annual calibration fixed and compares later company disclosures with modeled generation. In 2023, the NREL reference shape has an annual error of −0.551%, while the sum of absolute quarterly errors equals 13.075% of annual observed generation. The annual total hides offsetting seasonal errors. The reported scope is company-controlled offshore generation; its assignment to the H2 proxy remains an evidence-based inference, and the quarterly series is not hourly meter data [E5].",
            "The audited supply chain uses public reanalysis, weather, provincial-load, power-system and asset bundles [19–23], but source identity does not establish physical calibration. An exploratory offshore-wind diagnostic holds a 2022 annual calibration fixed and compares later company disclosures with modeled generation. In 2023, the NREL reference shape has an annual error of −0.551%, while the sum of absolute quarterly errors equals 13.075% of annual observed generation. The annual total hides offsetting seasonal errors. The reported scope is company-controlled offshore generation; its assignment to the H2 proxy remains an evidence-based inference, and the quarterly series is not hourly meter data [E5].",
        ),
        (
            "The supported conclusion is that attribution and system value depend on explicitly defined service, power and supply boundaries. Under the tested decision rights, the apparent contribution of mode choice changes with the completion allowance. Energy savings can coincide with a higher GPU peak, and a mathematically feasible task response can have an unfavorable grid consequence once recovery and commitment are represented. These findings motivate measurement and experimental design; they do not yet quantify the grid value of deployed AI clusters across the three provinces.",
            "The supported conclusion is that attribution and system value depend on explicitly defined service, power and supply boundaries. The literature audit shows that capability, trace-based deferral and grid-value modeling are established research areas; novelty cannot rest on any one of them. Under the tested decision rights, the apparent contribution of mode choice changes with the completion allowance. Energy savings can coincide with a higher GPU peak, and a mathematically feasible task response can have an unfavorable grid consequence once recovery and commitment are represented. These findings motivate measurement and experimental design; they do not yet quantify the grid value of deployed AI clusters across the three provinces.",
        ),
        (
            "The research repository is https://github.com/william19307/ai-grid-flexibility-research, branch codex/research-evidence-revision. This edition is based on evidence commit f4bd66b564e50d0a7e30d5f4cca6ebe522b5df33. The package includes an evidence index and source-file hashes. External raw archives, prepared arrays and local environments require restoration through REPRODUCE.md; cloning alone does not reproduce the entire study. No new hardware measurements are claimed.",
            f"The research repository is https://github.com/william19307/ai-grid-flexibility-research, branch codex/research-evidence-revision. The scheduling and physical-boundary results retain their frozen stage-specific evidence commits; the literature and novelty audit is anchored at commit {EVIDENCE_COMMIT}. The package includes an evidence index and source-file hashes. External raw archives, prepared arrays and local environments require restoration through REPRODUCE.md; cloning alone does not reproduce the entire study. No new hardware measurements are claimed.",
        ),
        (
            "E6. Revision stages 23 and 29–35 and asset_identity_methods_draft.md: technology, industrial boundaries and alias adjudication.",
            "E6. Revision stages 23 and 29–35 and asset_identity_methods_draft.md: technology, industrial boundaries and alias adjudication.\n\nE7. Revision stage 36 and literature_20260927: current direct-literature registry, metadata checks, novelty matrix and claim–citation ledger.",
        ),
        (
            "The companion evidence index gives immutable repository links. These identifiers refer to research records, not peer-reviewed publications. The complete historical bibliography is retained with v1.4; a final literature review and citation audit remain required before submission.",
            "The companion evidence index gives immutable repository links. These identifiers refer to research records, not peer-reviewed publications. Stage 36 verifies the present bibliography and novelty boundary against current primary metadata; full-text checking remains incomplete for some entries, and the audit is not a systematic review.",
        ),
    ]
    for old, new in replacements:
        text = replace_once(text, old, new)

    marker = "## Evidence register\n"
    if marker not in text or "## References\n" in text:
        raise ValueError("Unexpected evidence/reference structure")
    text = text.replace(marker, REFERENCES + marker, 1)

    body, reference_section = text.split("## References\n", 1)
    reference_body, remainder = reference_section.split("## Evidence register\n", 1)
    reference_numbers = [int(value) for value in re.findall(r"(?m)^(\d+)\. ", reference_body)]
    if reference_numbers != list(range(1, 24)):
        raise ValueError(f"Unexpected references: {reference_numbers}")
    cited = citation_numbers(body)
    if set(cited) != set(reference_numbers):
        raise ValueError(f"Citation mismatch; cited={sorted(set(cited))}")
    first_order = []
    for number in cited:
        if number not in first_order:
            first_order.append(number)
    if first_order != reference_numbers:
        raise ValueError(f"References are not in order of first appearance: {first_order}")
    if re.search(r"\b(first|novel|unprecedented)\b", body, flags=re.IGNORECASE):
        allowed = {
            "first demonstrating", "first using", "first modeling", "first proposing"
        }
        found = {m.group(0).lower() for m in re.finditer(r".{0,30}\bfirst\b.{0,40}", body, flags=re.IGNORECASE)}
        if not found:
            raise ValueError("Unexpected broad novelty term")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)
    TARGET_MD.write_text(text, encoding="utf-8")
    shutil.copy2(SOURCE_FIGURE, OUT / "figures/fig1_policy_attribution.png")
    build_docx(
        TARGET_MD,
        TARGET_DOCX,
        "AI computing flexibility · v1.6 review",
        subject="Revision v1.6 literature-integrated review edition; evidence through revision stage 36",
        comments="Prepared as an evidence-bounded literature-integrated review manuscript on 27 September 2026.",
    )
    validation = {
        "source": str(SOURCE.relative_to(ROOT)),
        "evidence_commit": EVIDENCE_COMMIT,
        "references": len(reference_numbers),
        "cited_references": len(set(cited)),
        "references_in_first_appearance_order": first_order == reference_numbers,
        "internal_evidence_register_entries": len(re.findall(r"(?m)^E\d+\.", remainder)),
        "broad_first_claims": 0,
        "nature_energy_system_claim_ready": False,
        "docx_created": TARGET_DOCX.is_file(),
    }
    (OUT / "citation_validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation))
    return 0


if __name__ == "__main__":
    sys.exit(main())
