#!/usr/bin/env python3
"""Build the stage-37 power-boundary-integrated v1.7 review manuscript."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from build_current_paper_docx import build as build_docx


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "outputs/research/revision/manuscript_v1.6"
SOURCE = SOURCE_DIR / "core_paper_en_v1.6_review.md"
OUT = ROOT / "outputs/research/revision/manuscript_v1.7"
TARGET_MD = OUT / "core_paper_en_v1.7_review.md"
TARGET_DOCX = OUT / "core_paper_en_v1.7_review.docx"
EVIDENCE_COMMIT = "b6da0c7"


NEW_REFERENCES = """24. Elsayed, A. A. E., Al-Obaidi, A. A. & Farag, H. E. Z. Characterization of high-resolution AI data center training workloads on single and multiple GPU nodes. Sci. Data 13, 1268 (2026). https://doi.org/10.1038/s41597-026-07496-6

25. MLCommons. MLPerf Inference v4.0 results. GitHub repository at commit 343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef (2024). https://github.com/mlcommons/inference_results_v4.0

26. MLCommons. MLPerf Inference power measurement rules. https://github.com/mlcommons/inference_policies/blob/master/power_measurement.adoc (accessed 27 September 2026).

"""


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Expected one occurrence, found {count}: {old[:90]}")
    return text.replace(old, new, 1)


def citations(text: str) -> list[int]:
    values: list[int] = []
    for match in re.finditer(r"\[([0-9,–-]+)\]", text):
        for token in match.group(1).split(","):
            if "–" in token or "-" in token:
                sep = "–" if "–" in token else "-"
                left, right = map(int, token.split(sep))
                values.extend(range(left, right + 1))
            else:
                values.append(int(token))
    return values


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "Revision v1.6 literature-integrated review edition | 27 September 2026 | Evidence consolidated through revision stage 36",
        "Revision v1.7 power-boundary review edition | 27 September 2026 | Evidence consolidated through revision stage 37",
    )
    text = replace_once(
        text,
        "**Manuscript status.** This edition integrates the supported revision findings with the stage 36 literature and novelty audit. It is not submission-ready and does not replace the submitted v1.4. Provincial system-benefit estimates, annual firm-capacity results and implementable market comparisons remain to be recomputed. The title and abstract are provisional. Author details are retained from v1.4.",
        "**Manuscript status.** This edition integrates the supported revision findings with the stage 36 literature audit and the stage 37 public power-boundary audit. It is not submission-ready and does not replace the submitted v1.4. Provincial system-benefit estimates, annual firm-capacity results and implementable market comparisons remain to be recomputed. The title and abstract are provisional. Author details are retained from v1.4.",
    )
    text = replace_once(
        text,
        "These results concern a conditional GPU-power model rather than measured whole-node or grid savings. Two analytical counterexamples show why translation to grid value requires additional care:",
        "These results concern a conditional GPU-power model rather than measured whole-node or grid savings. In an external same-system audit of 24 official 8-GPU H100 benchmark rows, capped operation retained 65.13–82.03% of standard performance, but the standard arm lacked AC system-power logs, so whole-node savings were not identifiable. Two analytical counterexamples show why translation to grid value requires additional care:",
    )
    text = replace_once(
        text,
        "A two-hour analytical example makes the consequence explicit. The observed total is [8, 8] MW, including a reference cohort [4, 0] MW. The controlled cohort is [0, 2] MW, so the common background is [4, 8] MW. Correct accounting gives a peak change from 8 to 10 MW. Adding both cohorts to the already inclusive total instead gives an apparent change from 12 to 10 MW. With an investment cost of 10 per MW and a variable cost of 5 per MWh, the correct cost comparison is 160 to 170, whereas the duplicated comparison is 220 to 190. The monetary units are arbitrary and the example is synthetic. It proves a possible sign reversal, not the size or sign of an error in the provincial manuscript.",
        "A two-hour example makes the consequence explicit. An observed total [8, 8] MW includes the reference cohort [4, 0] MW, so the common background is [4, 8] MW. A controlled cohort [0, 2] MW changes the true peak from 8 to 10 MW, whereas double counting changes the apparent peak from 12 to 10 MW. Under arbitrary investment and variable costs, the respective totals are 160 to 170 and 220 to 190. This proves a possible sign reversal, not its size in the provincial manuscript.",
    )
    insertion_point = (
        "Neither the 200 MW accounting correction nor a small annual renewable error can be converted directly into a corrected system-benefit percentage.\n\n"
        "## Discussion"
    )
    subsection = """Neither the 200 MW accounting correction nor a small annual renewable error can be converted directly into a corrected system-benefit percentage.

### Public same-system power evidence remains one-sided

Recent high-resolution training data include 32 sessions on 8-GPU H100 and B200 nodes at 20 ms resolution, but their node-power variable is the sum of GPU telemetry because whole-node access was unavailable [24]. These traces resolve fast device dynamics; they do not measure the AC input of the server or facility.

We separately extracted matched NVIDIA submissions from the official MLPerf Inference v4.0 repository at a fixed commit [25]. The standard and MaxQ system descriptions identify the same DGX H100 hardware and software fields apart from the system name. Across 24 matched benchmark–accuracy–scenario rows, both arms have valid performance and accuracy records. MaxQ retains 65.13–82.03% of standard performance, with a median of 74.57%. Its submitted Yokogawa measurements report mean system input of 3.777–5.377 kW, with at least 600 one-second samples per row. The rows include duplicated performance runs across some accuracy targets and are not independent repetitions.

MLPerf requires system-level AC measurement, inclusion of active host components and same-run power and performance [26]. However, the matched standard arm contains no submitted power logs. The public pair therefore supports a workload-dependent service-performance comparison and a measured MaxQ power level, but it cannot identify the change in whole-node power, energy per completed sample or energy savings. Common hardware is necessary but insufficient: both operating arms must cross the same measurement boundary while delivering matched useful work and quality [E8].

## Discussion"""
    text = replace_once(text, insertion_point, subsection)
    text = replace_once(
        text,
        "The supported conclusion is that attribution and system value depend on explicitly defined service, power and supply boundaries.",
        "The supported conclusion is that attribution and system value depend on explicitly defined service, power and supply boundaries. The external benchmark audit makes the measurement requirement concrete: a valid capped-power run does not establish savings when its standard comparator lacks power measurement.",
    )
    text = replace_once(
        text,
        "Current code includes unit commitment, energy-conserving storage and reservoirs, shared industrial fuel and a private-site grid interface, fixed-cohort demand construction and conditional mechanism evaluation.",
        "Current code includes unit commitment, energy-conserving storage and reservoirs, shared industrial fuel and a private-site grid interface, fixed-cohort demand construction and conditional mechanism evaluation. The external benchmark audit is a deterministic extraction from a pinned public result repository; it compares matched performance and accuracy records, submitted MaxQ AC power logs and system descriptions without fitting those data to the Helios schedules.",
    )
    text = replace_once(
        text,
        "The scheduling and physical-boundary results retain their frozen stage-specific evidence commits; the literature and novelty audit is anchored at commit 510780e9ead27698e33cedf24df5a5a171a8f11b.",
        f"The scheduling and physical-boundary results retain their frozen stage-specific evidence commits; the literature and novelty audit is anchored at commit 510780e9ead27698e33cedf24df5a5a171a8f11b, and the public power-boundary audit at commit {EVIDENCE_COMMIT}.",
    )
    text = replace_once(
        text,
        "23. Potsdam Institute for Climate Impact Research. Data bundle PyPSA-China-PIK: rasters and basic cutout, v1.1. Zenodo https://doi.org/10.5281/zenodo.16810831 (2025).\n\n",
        "23. Potsdam Institute for Climate Impact Research. Data bundle PyPSA-China-PIK: rasters and basic cutout, v1.1. Zenodo https://doi.org/10.5281/zenodo.16810831 (2025).\n\n" + NEW_REFERENCES,
    )
    text = replace_once(
        text,
        "E7. Revision stage 36 and literature_20260927: current direct-literature registry, metadata checks, novelty matrix and claim–citation ledger.",
        "E7. Revision stage 36 and literature_20260927: current direct-literature registry, metadata checks, novelty matrix and claim–citation ledger.\n\nE8. Revision stage 37 and mlperf_power_admission: pinned same-system performance, accuracy, MaxQ AC power, system-identity and admission audit.",
    )
    text = replace_once(
        text,
        "Stage 36 verifies the present bibliography and novelty boundary against current primary metadata; full-text checking remains incomplete for some entries, and the audit is not a systematic review.",
        "Stages 36–37 verify the present bibliography, novelty boundary and the pinned public power extraction. Full-text checking remains incomplete for some literature entries, the literature audit is not systematic, and the MLPerf extraction does not create the missing standard-arm power measurement.",
    )

    body, refs_tail = text.split("## References\n", 1)
    refs, evidence = refs_tail.split("## Evidence register\n", 1)
    numbers = [int(x) for x in re.findall(r"(?m)^(\d+)\. ", refs)]
    if numbers != list(range(1, 27)):
        raise ValueError(numbers)
    cited = citations(body)
    first: list[int] = []
    for number in cited:
        if number not in first:
            first.append(number)
    if set(cited) != set(numbers) or first != numbers:
        raise ValueError({"missing": sorted(set(numbers) - set(cited)), "first": first})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)
    TARGET_MD.write_text(text, encoding="utf-8")
    shutil.copy2(SOURCE_DIR / "figures/fig1_policy_attribution.png", OUT / "figures/fig1_policy_attribution.png")
    build_docx(
        TARGET_MD,
        TARGET_DOCX,
        "AI computing flexibility · v1.7 review",
        subject="Revision v1.7 power-boundary review edition; evidence through revision stage 37",
        comments="Prepared as an evidence-bounded review manuscript on 27 September 2026.",
    )
    validation = {
        "source": str(SOURCE.relative_to(ROOT)),
        "stage_37_evidence_commit": EVIDENCE_COMMIT,
        "references": len(numbers),
        "cited_references": len(set(cited)),
        "references_in_first_appearance_order": first == numbers,
        "internal_evidence_register_entries": len(re.findall(r"(?m)^E\d+\.", evidence)),
        "mlperf_matched_rows": 24,
        "whole_node_energy_saving_computable": False,
        "nature_energy_system_claim_ready": False,
        "docx_created": TARGET_DOCX.is_file(),
    }
    (OUT / "citation_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation))
    return 0


if __name__ == "__main__":
    sys.exit(main())
