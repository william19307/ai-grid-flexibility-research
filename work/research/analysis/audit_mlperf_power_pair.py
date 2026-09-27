#!/usr/bin/env python3
"""Audit a same-system MLPerf v4.0 MaxP/MaxQ pair without redistributing raw logs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path


EXPECTED_COMMIT = "343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef"
REPOSITORY_URL = "https://github.com/mlcommons/inference_results_v4.0"
STANDARD_SYSTEM = "DGX-H100_H100-SXM-80GBx8_TRT"
MAXQ_SYSTEM = STANDARD_SYSTEM + "_MaxQ"

# Direct assignments in the NVIDIA v4.0 configuration classes. High-accuracy
# classes that inherit a MaxQ class without overriding power use the parent cap.
CAPS = {
    "3d-unet-99": (300, "3d-unet/Offline/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "3d-unet-99.9": (300, "3d-unet/Offline/__init__.py", "H100_SXM_80GBx8_HighAccuracy_MaxQ"),
    "bert-99": (400, "bert/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "bert-99.9": (450, "bert/{scenario}/__init__.py", "H100_SXM_80GBx8_HighAccuracy_MaxQ"),
    "dlrm-v2-99": (450, "dlrm-v2/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "dlrm-v2-99.9": (275, "dlrm-v2/{scenario}/__init__.py", "H100_SXM_80GBx8_HighAccuracy_MaxQ"),
    "gptj-99": (350, "gptj/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "gptj-99.9": (350, "gptj/{scenario}/__init__.py", "H100_SXM_80GBx8_HighAccuracy_MaxQ"),
    "llama2-70b-99.9": (350, "llama2-70b/{scenario}/__init__.py", "H100_SXM_80GB_TP2x4_HighAccuracy_MaxQ"),
    "resnet50": (300, "resnet50/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "retinanet": (350, "retinanet/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "rnnt": (300, "rnnt/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
    "stable-diffusion-xl": (350, "stable-diffusion-xl/{scenario}/__init__.py", "H100_SXM_80GBx8_MaxQ"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def metric(summary: str) -> tuple[str, float]:
    if "Result is : VALID" not in summary:
        raise ValueError("performance result is not VALID")
    for name in ("Scheduled samples per second", "Samples per second"):
        m = re.search(rf"^{re.escape(name)}\s*:\s*([0-9.eE+-]+)", summary, re.M)
        if m:
            return name, float(m.group(1))
    raise ValueError("no supported performance metric")


def completed_metric(summary: str) -> float | None:
    m = re.search(r"^Completed samples per second\s*:\s*([0-9.eE+-]+)", summary, re.M)
    return float(m.group(1)) if m else None


def measured_power(server_json: Path) -> tuple[float, float, float, int, str]:
    data = json.loads(server_json.read_text())
    watts = [m["reply"] for m in data["ptd_messages"] if m.get("cmd") == "Watts"]
    if not watts:
        raise ValueError(f"no PTDaemon Watts record: {server_json}")
    fields = watts[-1].split(",")
    if len(fields) < 7:
        raise ValueError(f"unexpected Watts record: {watts[-1]}")
    identify = next(m["reply"] for m in data["ptd_messages"] if m.get("cmd") == "Identify")
    return float(fields[1]), float(fields[2]), float(fields[3]), int(fields[4]), identify


def class_power_limit(config_file: Path, class_name: str) -> int | None:
    text = config_file.read_text()
    pattern = rf"class\s+{re.escape(class_name)}\([^\n]+\):(?P<body>.*?)(?=\n(?:@|class\s)|\Z)"
    m = re.search(pattern, text, re.S)
    if not m:
        raise ValueError(f"missing config class {class_name} in {config_file}")
    p = re.search(r"^\s*power_limit\s*=\s*(\d+)", m.group("body"), re.M)
    return int(p.group(1)) if p else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=Path("work/tmp/mlperf-inference-v40"))
    ap.add_argument("--output", type=Path, default=Path("outputs/research/revision/mlperf_power_admission"))
    args = ap.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if commit != EXPECTED_COMMIT:
        raise SystemExit(f"expected {EXPECTED_COMMIT}, found {commit}")

    nvidia = source / "closed/NVIDIA"
    standard_root = nvidia / "results" / STANDARD_SYSTEM
    maxq_root = nvidia / "results" / MAXQ_SYSTEM
    rows: list[dict[str, object]] = []
    source_files: set[Path] = set()

    for q_summary in sorted(maxq_root.glob("*/*/performance/run_1/mlperf_log_summary.txt")):
        benchmark = q_summary.relative_to(maxq_root).parts[0]
        scenario = q_summary.relative_to(maxq_root).parts[1]
        s_summary = standard_root / benchmark / scenario / "performance/run_1/mlperf_log_summary.txt"
        q_power = q_summary.parents[1] / "power/server.json"
        q_accuracy = q_summary.parents[2] / "accuracy/accuracy.txt"
        s_accuracy = standard_root / benchmark / scenario / "accuracy/accuracy.txt"
        for required in (s_summary, q_power, q_accuracy, s_accuracy):
            if not required.exists():
                raise FileNotFoundError(required)

        cap, config_pattern, class_name = CAPS[benchmark]
        config_rel = config_pattern.format(scenario=scenario)
        config_file = nvidia / "configs" / config_rel
        direct_cap = class_power_limit(config_file, class_name)
        if direct_cap is not None and direct_cap != cap:
            raise ValueError(f"cap mismatch for {benchmark}/{scenario}: {direct_cap} vs {cap}")

        q_metric_name, q_perf = metric(q_summary.read_text())
        s_metric_name, s_perf = metric(s_summary.read_text())
        if q_metric_name != s_metric_name:
            raise ValueError(f"metric mismatch for {benchmark}/{scenario}")
        mean_w, min_w, max_w, samples, meter = measured_power(q_power)
        rows.append({
            "benchmark": benchmark,
            "scenario": scenario,
            "performance_metric": q_metric_name,
            "standard_performance": s_perf,
            "maxq_performance": q_perf,
            "maxq_to_standard_ratio": q_perf / s_perf,
            "maxq_performance_loss_percent": 100.0 * (1.0 - q_perf / s_perf),
            "gpu_power_limit_w_each": cap,
            "maxq_measured_system_power_mean_w": mean_w,
            "maxq_measured_system_power_min_w": min_w,
            "maxq_measured_system_power_max_w": max_w,
            "power_samples": samples,
            "standard_measured_system_power_w": "",
            "whole_node_energy_saving_computable": "false",
            "maxq_completed_samples_per_second": completed_metric(q_summary.read_text()) or "",
            "standard_completed_samples_per_second": completed_metric(s_summary.read_text()) or "",
            "maxq_accuracy_record": " | ".join(q_accuracy.read_text().splitlines()[:2]),
            "standard_accuracy_record": " | ".join(s_accuracy.read_text().splitlines()[:2]),
            "power_meter": meter,
            "config_source": f"closed/NVIDIA/configs/{config_rel}::{class_name}",
            "standard_summary_sha256": sha256(s_summary),
            "maxq_summary_sha256": sha256(q_summary),
            "maxq_power_json_sha256": sha256(q_power),
            "standard_accuracy_sha256": sha256(s_accuracy),
            "maxq_accuracy_sha256": sha256(q_accuracy),
        })
        source_files.update((s_summary, q_summary, q_power, s_accuracy, q_accuracy, config_file))

    if len(rows) != 24:
        raise ValueError(f"expected 24 matched rows, found {len(rows)}")

    csv_path = output / "matched_results.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    standard_system = json.loads((nvidia / "systems" / f"{STANDARD_SYSTEM}.json").read_text())
    maxq_system = json.loads((nvidia / "systems" / f"{MAXQ_SYSTEM}.json").read_text())
    differences = {k: [standard_system.get(k), maxq_system.get(k)] for k in sorted(set(standard_system) | set(maxq_system)) if standard_system.get(k) != maxq_system.get(k)}
    (output / "system_identity.json").write_text(json.dumps({
        "same_hardware_fields_after_name_exclusion": set(differences) <= {"system_name"},
        "differences": differences,
        "standard_system": STANDARD_SYSTEM,
        "maxq_system": MAXQ_SYSTEM,
    }, indent=2) + "\n")

    ratios = [float(r["maxq_to_standard_ratio"]) for r in rows]
    powers = [float(r["maxq_measured_system_power_mean_w"]) for r in rows]
    summary = {
        "source_repository": REPOSITORY_URL,
        "source_commit": commit,
        "matched_result_rows": len(rows),
        "unique_benchmark_accuracy_profiles": len({r["benchmark"] for r in rows}),
        "scenarios": sorted({str(r["scenario"]) for r in rows}),
        "all_performance_results_valid": True,
        "all_accuracy_records_present": True,
        "maxq_system_power_rows": len(rows),
        "standard_system_power_rows": 0,
        "maxq_to_standard_performance_ratio_min": min(ratios),
        "maxq_to_standard_performance_ratio_median": statistics.median(ratios),
        "maxq_to_standard_performance_ratio_max": max(ratios),
        "maxq_measured_system_power_mean_w_min": min(powers),
        "maxq_measured_system_power_mean_w_max": max(powers),
        "whole_node_energy_saving_computable": False,
        "admission_decision": "service_performance_admissible_power_savings_not_admissible",
        "reason": "The same-system MaxP arm has no submitted AC system-power measurement.",
    }
    (output / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    manifest = [{"path": str(p.relative_to(source)), "sha256": sha256(p)} for p in sorted(source_files)]
    (output / "source_manifest.json").write_text(json.dumps({
        "repository": REPOSITORY_URL,
        "commit": commit,
        "files": manifest,
        "raw_files_redistributed": False,
    }, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
