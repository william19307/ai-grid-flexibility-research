"""Build a complete, source-pinned staging ledger; no dispatch or old-runner import."""
from pathlib import Path
import argparse,sys,json,hashlib,csv
from collections import defaultdict
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/inputs'))
from thermal_technology import read_verified_csv,verify_cohort,archive_parameters,stage,require_dispatch_ready
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/research/revision/thermal_technology');args=parser.parse_args()
OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
cohort_rel='outputs/research/revision/input_consistency/selected_oil_gas_unit_audit.csv'
cost_rel='work/research/sources/zenodo_13987282/selected/data/costs/costs_2030.csv'
proof=json.loads((ROOT/'outputs/research/revision/input_consistency/evidence_manifest.json').read_text())
sources=json.loads((ROOT/'outputs/research/revision/input_consistency/source_hashes.json').read_text())
cohort=read_verified_csv(ROOT/cohort_rel,proof['artifact_sha256'][cohort_rel]);costs=read_verified_csv(ROOT/cost_rel,sources[cost_rel])
verify_cohort(cohort,cohort);parameters,provenance=archive_parameters(costs,'0.05');manifest=stage(cohort,parameters)
manifest['source_sha256']={cohort_rel:proof['artifact_sha256'][cohort_rel],cost_rel:sources[cost_rel]}
(OUT/'fleet_staging.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
(OUT/'parameter_provenance.json').write_text(json.dumps(provenance,indent=2,ensure_ascii=False)+'\n')
groups=defaultdict(lambda:[0,Decimal(0)])
for unit in manifest['stock']:
    key=(unit['province'],unit['candidate_technology'],unit['chp_evidence'],unit['captive_evidence'])
    groups[key][0]+=1;groups[key][1]+=Decimal(unit['capacity_mw'])
with (OUT/'technology_role_summary.csv').open('w',newline='') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['province','candidate_technology','chp_evidence','captive_evidence','units','capacity_mw'])
    for key,(n,mw) in sorted(groups.items()):w.writerow([*key,n,str(mw)])
try:require_dispatch_ready(manifest)
except ValueError as ex:blocked=str(ex)
else:raise AssertionError('Unqualified fleet admitted')
report=dict(source_units=len(cohort),source_capacity_mw=str(sum(Decimal(x['capacity_numeric_MW']) for x in cohort)),
    preserved_units=len(manifest['stock']),prospective_options=len(manifest['investment_options']),dispatch_admission='REJECTED',reason=blocked,
    implementation_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'work/research/inputs/thermal_technology.py']})
(OUT/'build_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
# A cost-screening illustration explains why stock and new-build roles must differ.
# It does not use or optimize the provincial demand/fleet.
import ast
a=parameters['OCGT']['values'];b=parameters['CCGT']['values']
fixed_delta=Decimal(b['annualized_capital_plus_fixed_om_eur_per_mw'])-Decimal(a['annualized_capital_plus_fixed_om_eur_per_mw'])
variable_delta=Decimal(a['marginal_cost_eur_per_mwh'])-Decimal(b['marginal_cost_eur_per_mwh'])
examples=[]
for h in [1000,6000]:
    examples.append(dict(equivalent_full_load_hours=h,
        ocgt_eur_per_mw_year=str(Decimal(a['annualized_capital_plus_fixed_om_eur_per_mw'])+h*Decimal(a['marginal_cost_eur_per_mwh'])),
        ccgt_eur_per_mw_year=str(Decimal(b['annualized_capital_plus_fixed_om_eur_per_mw'])+h*Decimal(b['marginal_cost_eur_per_mwh']))))
path=ROOT/'work/research/analysis/run_regional_2030_s0_s3.py';trace=[]
for node in ast.walk(ast.parse(path.read_text())):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='Generator' and node.args and isinstance(node.args[0],ast.Constant) and node.args[0].value in ['ocgt','nb_gas']:
        trace.append(dict(file=str(path.relative_to(ROOT)),line=node.lineno,name=node.args[0].value,
            existing_capacity=ast.unparse(node.args[2]),max_new=ast.unparse(node.args[3]),investment=ast.unparse(node.args[4]),
            marginal_cost=ast.unparse(node.args[5]),emissions=ast.unparse(node.args[6])))
(OUT/'existing_investment_separation.json').write_text(json.dumps(dict(
    archive_annualized_fixed_cost_delta_eur_per_mw_year=str(fixed_delta),archive_variable_cost_delta_eur_per_mwh=str(variable_delta),
    conditional_break_even_full_load_hours=str(fixed_delta/variable_delta),examples=examples,legacy_constructor_trace=trace,
    legacy_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    scope='Algebraic constant-efficiency comparison only; excludes heat obligations, commitment, outage and network. Not a China build recommendation or actual fleet reestimate.'),indent=2)+'\n')
