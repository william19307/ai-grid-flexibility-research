"""Run unchanged legacy mathematical checks with isolated revision output paths."""
from pathlib import Path
import hashlib,json,sys,platform
import scipy,numpy,pandas

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/research/revision/power_attribution/regression'
OUT.mkdir(parents=True,exist_ok=True)
for filename in ['validate_sequential_tasks.py','validate_response_cost.py']:
    p=ROOT/'work/research/analysis'/filename
    source=p.read_text()
    old="pd.read_csv(OUT/'dvfs_measured_and_derived.csv')"
    assert source.count(old)==1
    source=source.replace(old,"pd.read_csv(ROOT/'outputs/research/tables/dvfs_measured_and_derived.csv')")
    old="OUT=ROOT/'outputs/research/tables'"
    assert source.count(old)==1
    source=source.replace(old,"OUT=ROOT/'outputs/research/revision/power_attribution/regression'")
    exec(compile(source,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
manifest=dict(python=sys.version,platform=platform.platform(),packages=dict(numpy=numpy.__version__,scipy=scipy.__version__,pandas=pandas.__version__),
              validation_sources={name:hashlib.sha256((ROOT/'work/research/analysis'/name).read_bytes()).hexdigest()
                                  for name in ['validate_sequential_tasks.py','validate_response_cost.py']},
              redirected_outputs_only=True,limits='Local regression, not clean-machine rebuild')
(OUT/'run_environment.json').write_text(json.dumps(manifest,indent=2)+'\n')
