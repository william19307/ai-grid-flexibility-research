"""Read-only historical project evidence; no dispatch or inventory replacement.

Requires pypdf and pdfplumber. Source bytes are deliberately version pinned.
The ledger is a research admission record, not an enforced model constraint.
"""
from pathlib import Path
from html.parser import HTMLParser
from decimal import Decimal
import csv
import hashlib
import html
import json
import re
import importlib.metadata

from pypdf import PdfReader
import pdfplumber

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "work/research/sources/captive_boundary_20260923"
OUT = ROOT / "outputs/research/revision/captive_boundary"
INVENTORY = ROOT / "outputs/research/revision/input_consistency/selected_oil_gas_unit_audit.csv"
PINNED = {
    "nangang_green_bond_20220214.pdf": "fe509d7399b18d33a0e9fed49936f69f0275aa263eb44a1b1f7e9ddafecab475",
    "nangang_2022_operations.html": "9f8c6eaa1abba1138d9cf439bee39e978bf360009d37fff07f2bde75cd746a24",
    "zhongtian_20180827.html": "e9474118aa83db7837453a95123331eba25acdaccb7c76490d59af6023c062ae",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value):
    return re.sub(r"\s+", "", value)


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def main():
    checks = []

    def check(name, valid):
        if not valid:
            raise ValueError(name)
        checks.append(name)

    for name, expected in PINNED.items():
        check("source_sha256:" + name, sha(SRC / name) == expected)

    # Independent text engines, same page and field, rather than trusting a search snippet.
    pdf = SRC / "nangang_green_bond_20220214.pdf"
    reader = PdfReader(pdf)
    with pdfplumber.open(pdf) as other:
        texts = {p: (compact(reader.pages[p].extract_text()),
                     compact(other.pages[p].extract_text())) for p in (14, 15, 16, 156)}
        # Page-wide extraction interleaves neighbouring columns. Read the bordered
        # table cells and require the visual header before interpreting values.
        table = other.pages[14].extract_tables()[0]
        check("pdfplumber_table_header", compact(table[1][2]) == "项目基本情况")
        texts[14] = (texts[14][0], compact("".join(c or "" for row in table for c in row)))
    fields = {
        "rated_power_MW": r"1套(120)MW",
        "boiler_t_per_h": r"1台(390)t/h",
        "gross_annual_10k_kWh": r"年发电量([\d,]+)万kWh",
        "supply_annual_10k_kWh": r"年供电量([\d,]+)万kWh",
        "incremental_supply_10k_kWh": r"年新增供电量([\d,]+)万kWh",
    }
    values = {}
    for field, pattern in fields.items():
        found = [re.search(pattern, text) for text in texts[14]]
        check("dual_pdf_field:" + field, all(found))
        pair = [Decimal(m.group(1).replace(",", "")) for m in found]
        check("dual_pdf_value:" + field, pair[0] == pair[1])
        values[field] = pair[0]
    # Short fragments only; table context and caveats are manually reviewed in the report.
    fragments = {
        14: ["全部自用，不并网", "转为检修备用", "另外3台50MW", "完成20%"],
        15: ["减少相应的外购电量", "96,512", "89,660", "41,788"],
        16: ["2012年", "0.7035", "29.40", "预计每年"],
        156: ["6#120MW", "43,000.00", "11,793.42"],
    }
    for page, tokens in fragments.items():
        for token in tokens:
            check(f"dual_pdf_context:{page}:{token}", all(compact(token) in t for t in texts[page]))

    html_tokens = {
        "nangang_2022_operations.html": ["2023/8/9", "6#120MW", "22.41亿KWh", "6号机组开机并网发电", "2022年"],
        "zhongtian_20180827.html": ["2018-08-27", "2017年7月份", "400t/h", "135MW", "高炉煤气", "项目建成后"],
    }
    for name, tokens in html_tokens.items():
        raw = (SRC / name).read_text(encoding="utf-8")
        parser = Text()
        parser.feed(raw)
        pair = [compact("".join(parser.parts)), compact(html.unescape(re.sub(r"<[^>]*>", "", raw)))]
        for token in tokens:
            check("dual_html:" + name + ":" + token, all(compact(token) in t for t in pair))

    with INVENTORY.open() as stream:
        all_units = list(csv.DictReader(stream))
    units = [r for r in all_units if r["candidate_category"] == "INDUSTRIAL_BYPRODUCT_REQUIRES_PROCESS_AND_EXPORT_BOUNDARY"]
    check("selected_byproduct_inventory_12_units_1125MW", len(units) == 12 and sum(Decimal(r["capacity_numeric_MW"]) for r in units) == Decimal("1125"))
    check("unique_unit_ids", len({r["GEM unit/phase ID"] for r in units}) == len(units))
    candidates = {
        "G100000412573": ("120", "nangang_green_bond_20220214.pdf;nangang_2022_operations.html", "Nangang Unit 6: issuer unit number and capacity support candidate match; bond project identity is not linked by a unique permit to inventory; CNY 471m vs CNY 430m project budgets unresolved", "planned self-use/no-grid statement; later grid-connection wording does not identify public export or meter boundary"),
        "G100001017684": ("135", "zhongtian_20180827.html", "Changzhou phase-3 project, same technology/capacity; phase 3 is not independently proven equal to inventory Unit 3", "historical construction announcement; export, fuel budget and current operation not established"),
    }
    ledger = []
    for unit in units:
        uid = unit["GEM unit/phase ID"]
        candidate = candidates.get(uid)
        if candidate:
            check("candidate_capacity:" + uid, Decimal(unit["capacity_numeric_MW"]) == Decimal(candidate[0]))
        ledger.append({
            "unit_id": uid, "plant": unit["Plant / Project name"], "unit": unit["Unit / Phase name"],
            "capacity_MW": unit["capacity_numeric_MW"], "inventory_technology": unit["Technology"],
            "inventory_fuel": unit["Fuel"], "inventory_CHP": unit["CHP"],
            "primary_candidate_sources": candidate[1] if candidate else "",
            "identity_status": candidate[2] if candidate else "No unit-specific primary evidence admitted in this stage",
            "boundary_status": candidate[3] if candidate else "Unresolved; do not transfer another unit's restrictions",
            "export_limit_MW": "", "firm_flexible_capacity_MW": "",
            "operational_admission": "NOT_ADMITTED_AS_UNCONSTRAINED_GRID_RESOURCE",
            "inventory_mutation": "NONE", "solver_enforcement": "NOT_IMPLEMENTED_BY_THIS_AUDIT",
        })
    check("candidate_ids_present", {r["unit_id"] for r in ledger if r["primary_candidate_sources"]} == set(candidates))
    check("no_invented_zero_export_or_firm_capacity", all(r["export_limit_MW"] == r["firm_flexible_capacity_MW"] == "" for r in ledger))
    gross = values["gross_annual_10k_kWh"] / 100
    supplied = values["supply_annual_10k_kWh"] / 100
    increment = values["incremental_supply_10k_kWh"] / 100
    check("planned_energy_order", gross > supplied > increment > 0)
    energy = {
        "scope": "Historical bond-project expectations, not observed annual generation or dispatch limits",
        "source_printed_pages": [14, 15, 16], "pdf_one_based_pages": [15, 16, 17],
        "planned_gross_GWh": str(gross), "planned_supply_GWh": str(supplied),
        "planned_incremental_supply_over_old_units_GWh": str(increment),
        "planned_gross_minus_supply_GWh": str(gross - supplied),
        "unqualified_company_report_plant_total_GWh": "2241",
        "plant_total_warning": "2023-08-09 company narrative discussing 2022; plant aggregate, not Unit 6 output; not an admitted unit calibration target",
        "carbon_factor_warning": "2012 regional average used in project appraisal; not present/future marginal avoided emissions",
        "firm_export_capacity_MW": None,
    }
    access = json.loads((SRC / "download_log.json").read_text()) + json.loads((SRC / "supplementary_download_log.json").read_text())
    check("access_receipts_match_pinned_sources", {Path(r["path"]).name: r["sha256"] for r in access} == PINNED)

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "unit_admission_ledger.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ledger[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(ledger)
    for name, value in [("planned_energy_boundaries.json", energy), ("source_access_log.json", access),
                        ("audit_results.json", {"checks_passed": len(checks), "checks": checks,
                            "scope": "source reading and arithmetic, not independent empirical experiments",
                            "selected_units": 12, "selected_MW": 1125,
                            "candidate_source_matches": 2, "candidate_matched_MW": 255,
                            "qualified_unconstrained_dispatch_units": 0, "new_dispatch_runs": 0})]:
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    manifest = {
        "inputs": {str(p.relative_to(ROOT)): sha(p) for p in [INVENTORY, *(SRC / n for n in PINNED)]},
        "code": {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))},
        "text_engines": {n: importlib.metadata.version(n) for n in ("pypdf", "pdfplumber")},
        "outputs": {p.name: sha(p) for p in sorted(OUT.glob("*")) if p.name in ("unit_admission_ledger.csv", "planned_energy_boundaries.json", "source_access_log.json", "audit_results.json")},
    }
    (OUT / "evidence_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"checks_passed": len(checks), "units": len(ledger), "qualified_dispatch_units": 0}))


if __name__ == "__main__":
    main()
