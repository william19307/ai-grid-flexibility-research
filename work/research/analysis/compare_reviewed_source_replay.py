"""Compare a separately executed reviewed-source replay with frozen outputs."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
ap=argparse.ArgumentParser();ap.add_argument('--checkout',type=Path,required=True);a=ap.parse_args()
clone=a.checkout.resolve();replayed=clone/'work/tmp/reviewed_tariff_version'
OUT=ROOT/'outputs/research/revision/reviewed_tariff_version';checks=[]
sys.path.insert(0,str(clone/'work/research/models'))
from verified_power_bridge import load_verified_case
from reviewed_tariff_version import OLD_PATH,NEW_PATH,NEW_SHA,AUDIT_PATH
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)
def remove_reviewed_proof(proof):
    versions=proof.pop('reviewed_source_versions')
    check('single_bound_reviewed_source_in_proof',len(versions)==1 and versions[0]['original_path']==OLD_PATH and
          versions[0]['admitted_path']==NEW_PATH and versions[0]['admitted_sha256']==NEW_SHA and
          versions[0]['source_audit_sha256']==sha(clone/AUDIT_PATH))
try:load_verified_case(clone,'Earth_ft_llama_8b_dolly_6_Jiangsu')
except ValueError as error:check('strict_original_mode_still_rejects',str(error)=='Missing original input: '+OLD_PATH)
else:raise AssertionError('Strict original mode unexpectedly passed')
case=load_verified_case(clone,'Earth_ft_llama_8b_dolly_6_Jiangsu',allow_reviewed_tariff_version=True)
check('reviewed_mode_explicitly_records_replacement',len(case['proof']['reviewed_source_versions'])==1)
check('historical_original_not_fabricated',not (clone/OLD_PATH).exists())
check('network_receipt_matches_reviewed_file',read(replayed/'fetch_receipt.json')['sha256']==sha(clone/NEW_PATH)==NEW_SHA)
for name,folder in [('cohort','demand_cohort'),('factorial','fixed_cohort_factorial')]:
    new=read(replayed/name/'validation.json');old=read(ROOT/'outputs/research/revision'/folder/'validation.json')
    check(name+'_admission_mode_declared',new.pop('source_admission_mode')=='explicit_reviewed_tariff_version')
    check(name+'_all_numeric_results_and_existing_checks_identical',new==old)
check('synthetic_accounting_examples_byte_identical',sha(replayed/'cohort/synthetic_counterexample_ledgers.json')==sha(ROOT/'outputs/research/revision/demand_cohort/synthetic_counterexample_ledgers.json'))
new=read(replayed/'cohort/verified_trace_synthetic_background_ledger.json')
old=read(ROOT/'outputs/research/revision/demand_cohort/verified_trace_synthetic_background_ledger.json')
check('new_ledger_hash_matches_new_payload',new['sha256']==hashlib.sha256(json.dumps(new['payload'],sort_keys=True,allow_nan=False).encode()).hexdigest())
check('provenance_changes_ledger_hash',new['sha256']!=old['sha256'])
payload=copy.deepcopy(new['payload']);remove_reviewed_proof(payload['provenance']['verified_case_proof'])
check('complete_192h_ledger_identical_except_declared_provenance',payload==old['payload'])
csvs=['demand_metrics.csv','policy_contrasts.csv','shape_interactions.csv','solver_oracle_checks.csv']
for name in csvs:
    check(name+'_byte_identical',sha(replayed/'factorial'/name)==sha(ROOT/'outputs/research/revision/fixed_cohort_factorial'/name))
new=read(replayed/'factorial/factor_ledger_manifest.json');old=read(ROOT/'outputs/research/revision/fixed_cohort_factorial/factor_ledger_manifest.json')
check('all_18_predeclared_ledgers_present',len(new)==len(old)==18)
for n,o in zip(new,old):
    n=copy.deepcopy(n);o=copy.deepcopy(o)
    check('factor_ledger_hash_changes_with_provenance',n.pop('ledger_sha256')!=o.pop('ledger_sha256'))
    remove_reviewed_proof(n['proof'])
    check('factor_clock_cohort_background_and_certificate_identical',n==o)
copies=[]
for name in ['cohort','factorial']:
    target=OUT/'replayed'/name;target.mkdir(parents=True,exist_ok=True)
    for source in sorted((replayed/name).glob('*')):
        shutil.copyfile(source,target/source.name)
        copies.append(dict(path=str((target/source.name).relative_to(ROOT)),sha256=sha(source)))
shutil.copyfile(replayed/'fetch_receipt.json',OUT/'fetch_receipt.json')
report=dict(checks=checks,number_of_checks=len(checks),
    checkout_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip(),
    clone_tracked_status=subprocess.check_output(['git','status','--porcelain'],cwd=clone,text=True),
    original_source_mode='Still 13/14 including prepared load; original Gansu HTML not restored',
    reviewed_source_mode='13 original-byte inputs plus one explicitly reviewed HTML version; all required inputs admitted',
    isolated_checks=dict(cohort=25,factorial=67),factorial_policy_solves=72,
    replayed_outputs=copies,all_numerical_outputs_identical=True,
    scope='Same-host isolated bounded replay of existing certified trajectories; no new 108-case optimization, second OS/machine or full-manuscript physical validation')
(OUT/'replay_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','replayed_outputs']},indent=2))
