#!/usr/bin/env python3
"""Independent structural checks for the MLPerf same-system evidence extract."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path("outputs/research/revision/mlperf_power_admission")


def check(condition: bool, label: str, passed: list[str]) -> None:
    if not condition:
        raise AssertionError(label)
    passed.append(label)


def main() -> None:
    rows = list(csv.DictReader((ROOT / "matched_results.csv").open()))
    summary = json.loads((ROOT / "audit_summary.json").read_text())
    identity = json.loads((ROOT / "system_identity.json").read_text())
    manifest = json.loads((ROOT / "source_manifest.json").read_text())
    passed: list[str] = []
    check(len(rows) == 24, "24 matched benchmark-scenario-accuracy rows", passed)
    check(len({(r["benchmark"], r["scenario"]) for r in rows}) == 24, "rows are unique", passed)
    check(all(float(r["standard_performance"]) > 0 and float(r["maxq_performance"]) > 0 for r in rows), "positive paired performance", passed)
    check(all(0 < float(r["maxq_to_standard_ratio"]) < 2 for r in rows), "finite plausible performance ratios", passed)
    check(all(2000 < float(r["maxq_measured_system_power_mean_w"]) < 7000 for r in rows), "plausible AC system-power means", passed)
    check(all(int(r["power_samples"]) >= 600 for r in rows), "at least 600 power samples per row", passed)
    check(all(r["standard_measured_system_power_w"] == "" for r in rows), "standard AC power absent", passed)
    check(all(r["whole_node_energy_saving_computable"] == "false" for r in rows), "energy saving marked non-computable", passed)
    check(all(r["maxq_accuracy_record"] and r["standard_accuracy_record"] for r in rows), "accuracy records retained", passed)
    check(summary["source_commit"] == "343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef", "source commit pinned", passed)
    check(summary["standard_system_power_rows"] == 0, "summary records zero standard-power rows", passed)
    check(summary["whole_node_energy_saving_computable"] is False, "summary rejects savings claim", passed)
    check(identity["same_hardware_fields_after_name_exclusion"] is True, "system descriptions match except name", passed)
    check(set(identity["differences"]) == {"system_name"}, "only system-name field differs", passed)
    check(len(manifest["files"]) >= 100, "source manifest covers raw evidence", passed)
    check(manifest["raw_files_redistributed"] is False, "raw repository data not redistributed", passed)
    out = {"status": "pass", "checks_passed": len(passed), "checks": passed}
    (ROOT / "independent_verification.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
