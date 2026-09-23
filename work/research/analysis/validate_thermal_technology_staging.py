"""Independent field/subtotal/formula checks and malformed-input mutations."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
import argparse,csv,copy,hashlib,json,math,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'work/research/inputs'))
from thermal_technology import stage,archive_parameters,verify_cohort,read_verified_csv,require_dispatch_ready
parser=argparse.ArgumentParser();parser.add_argument('--input-dir',type=Path,default=ROOT/'outputs/research/revision/thermal_technology');parser.add_argument('--output',type=Path);args=parser.parse_args()
D=args.input_dir;output=args.output or D/'validation.json'
manifest=json.loads((D/'fleet_staging.json').read_text())
with (ROOT/'outputs/research/revision/input_consistency/selected_oil_gas_unit_audit.csv').open(newline='') as f:source=list(csv.DictReader(f))
with (ROOT/'work/research/sources/zenodo_13987282/selected/data/costs/costs_2030.csv').open(newline='') as f:costs=list(csv.DictReader(f))
checks=[]
def check(condition,label):
 if not condition:raise AssertionError(label)
 checks.append(label)
def rejected(fn,label):
 try:fn()
 except ValueError:checks.append(label)
 else:raise AssertionError('Accepted '+label)
byid={r['GEM unit/phase ID']:r for r in source};stock=manifest['stock']
check(len(stock)==len(source)==109 and {r['unit_id'] for r in stock}==set(byid),'all_109_identities_retained')
check(all(r['source_record']==byid[r['unit_id']] for r in stock),'all_original_fields_retained')
check(all(r['source_record_sha256']==hashlib.sha256(json.dumps(byid[r['unit_id']],sort_keys=True,ensure_ascii=False).encode()).hexdigest() for r in stock),'per_unit_record_hashes')
check(sum(Decimal(r['capacity_mw']) for r in stock)==Decimal('24959'),'capacity_conservation')
classes=defaultdict(lambda:[0,Decimal(0)])
for r in stock:
 classes[r['candidate_technology']][0]+=1;classes[r['candidate_technology']][1]+=Decimal(r['capacity_mw'])
check(classes=={'CCGT_fossil_gas':[97,Decimal('23834')],'industrial_byproduct_steam':[12,Decimal('1125')]},'technology_partition')
ccgt=[r for r in stock if r['candidate_technology']=='CCGT_fossil_gas'];industrial=[r for r in stock if r not in ccgt]
check(sum(r['chp_evidence']=='reported_yes' for r in ccgt)==82 and sum(Decimal(r['capacity_mw']) for r in ccgt if r['chp_evidence']=='reported_yes')==Decimal('17853'),'ccgt_heat_yes')
check(sum(r['chp_evidence']=='unknown' for r in ccgt)==15 and sum(Decimal(r['capacity_mw']) for r in ccgt if r['chp_evidence']=='unknown')==Decimal('5981'),'ccgt_heat_unknown_not_no')
check(all(r['conditional_parameter_reference'] is None for r in industrial),'no_natural_gas_cost_for_industrial_fuel')
check(all(r['new_build_capacity_mw']=='0' for r in stock),'no_investment_on_existing_stock')
check(len(manifest['investment_options'])==3 and all(r['technology']=='OCGT' and r['existing_capacity_mw']=='0' and r['max_new_capacity_mw'] is None for r in manifest['investment_options']),'separate_ocgt_option_without_assumed_permission')
check(all(not r['dispatch_ready'] and r['unresolved_requirements'] for r in stock),'no_silent_operational_admission')
labels=json.loads((D/'date_formatted_unit_labels.json').read_text())
check({r['unit_id'] for r in stock if r['date_formatted_unit_label']}=={r['unit_id'] for r in labels['records']} and labels['affected_units']==19,'date_formatted_names_flagged_from_raw_xml')
# Different arithmetic implementation: float direct retrieval and closed-form CRF.
v={(r['technology'],r['parameter']):float(r['value']) for r in costs if r['technology'] in ['OCGT','CCGT','gas']}
comparisons=[]
for tech in ['OCGT','CCGT']:
 p=manifest['conditional_parameters'][tech]['values'];eta=v[tech,'efficiency'];n=v[tech,'lifetime'];rate=.05
 crf=rate*(1+rate)**n/((1+rate)**n-1)
 expected={'marginal_cost_eur_per_mwh':v['gas','fuel']/eta+v[tech,'VOM'],'emissions_t_per_mwh':v['gas','CO2 intensity']/eta,
 'annualized_capital_eur_per_mw':v[tech,'investment']*1000*crf,'fixed_om_eur_per_mw_year':v[tech,'investment']*1000*v[tech,'FOM']/100}
 expected['annualized_capital_plus_fixed_om_eur_per_mw']=expected['annualized_capital_eur_per_mw']+expected['fixed_om_eur_per_mw_year']
 check(all(math.isclose(float(p[k]),x,rel_tol=1e-12,abs_tol=1e-10) for k,x in expected.items()),'independent_archive_formula:'+tech)
 comparisons.append(dict(technology=tech,**expected))
separation=json.loads((D/'existing_investment_separation.json').read_text())
x=(comparisons[1]['annualized_capital_plus_fixed_om_eur_per_mw']-comparisons[0]['annualized_capital_plus_fixed_om_eur_per_mw'])/(comparisons[0]['marginal_cost_eur_per_mwh']-comparisons[1]['marginal_cost_eur_per_mwh'])
check(math.isclose(x,float(separation['conditional_break_even_full_load_hours']),rel_tol=1e-12),'independent_conditional_cost_crossover')
check(float(separation['examples'][0]['ocgt_eur_per_mw_year'])<float(separation['examples'][0]['ccgt_eur_per_mw_year']) and float(separation['examples'][1]['ocgt_eur_per_mw_year'])>float(separation['examples'][1]['ccgt_eur_per_mw_year']),'investment_ranking_changes_with_utilization')
check({r['name'] for r in separation['legacy_constructor_trace']}=={'ocgt','nb_gas'},'main_and_neighbour_legacy_roles_located')
zero,_=archive_parameters(costs,'0');check(all(math.isclose(float(zero[t]['values']['annualized_capital_eur_per_mw']),v[t,'investment']*1000/v[t,'lifetime']) for t in ['OCGT','CCGT']),'zero_discount_capital_recovery')
rejected(lambda:verify_cohort(source[:-1],source),'reject_missing_unit')
rejected(lambda:verify_cohort(source+[source[0]],source),'reject_duplicate_unit')
mut=copy.deepcopy(source);mut[0]['capacity_numeric_MW']='0';rejected(lambda:verify_cohort(mut,source),'reject_capacity_change_against_source')
mut=copy.deepcopy(source);mut[0]['CHP']='no';rejected(lambda:verify_cohort(mut,source),'reject_heat_status_change_against_source')
mut=copy.deepcopy(source);mut[0]['Technology']='unknown-new-type';r=stage(mut,manifest['conditional_parameters'])['stock'][0]
check(r['candidate_technology']=='unclassified_requires_review' and r['conditional_parameter_reference'] is None and not r['dispatch_ready'],'unknown_technology_retained_without_fallback')
for parameter,field,value,label in [('efficiency','unit','percent','unit'),('efficiency','year','2020','year'),('efficiency','value','0','zero_efficiency'),('efficiency','value','NaN','nonfinite'),('lifetime','value','0','zero_lifetime'),('VOM','source','','missing_parameter_source')]:
 mut=copy.deepcopy(costs);target=next(r for r in mut if r['technology']=='CCGT' and r['parameter']==parameter);target[field]=value
 rejected(lambda:archive_parameters(mut,'0.05'),'reject_'+label)
mut=copy.deepcopy(costs);mut.append(next(r for r in mut if r['technology']=='CCGT' and r['parameter']=='VOM').copy());rejected(lambda:archive_parameters(mut,'0.05'),'reject_duplicate_parameter')
mut=[r for r in costs if not (r['technology']=='CCGT' and r['parameter']=='c_v')];rejected(lambda:archive_parameters(mut,'0.05'),'reject_missing_heat_metadata')
rejected(lambda:archive_parameters(costs,True),'reject_boolean_discount')
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'changed.csv';p.write_text('changed')
 rejected(lambda:read_verified_csv(p,'0'*64),'reject_unknown_source_hash')
rejected(lambda:require_dispatch_ready(manifest),'reject_actual_unqualified_cohort')
mut=copy.deepcopy(manifest)
for r in mut['stock']:r['dispatch_ready']=True;r['unresolved_requirements']=[]
rejected(lambda:require_dispatch_ready(mut),'reject_edited_ready_flags_as_fake_approval')
rejected(lambda:require_dispatch_ready({'schema':manifest['schema'],'stock':[]}),'reject_empty_fleet')
report=dict(check_count=len(checks),checks=checks,independent_conditional_rates=comparisons,
    scope='Source-preserving staging and conditional arithmetic; no operational parameter qualification or provincial solve',
    design_commit='d20a5d5',validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
