"""Read-only public-source audit; never executes downloaded benchmark code."""
from pathlib import Path
import json,hashlib,urllib.request,concurrent.futures,time
ROOT=Path(__file__).resolve().parents[3];SRC=ROOT/'work/research/sources/tokenpowerbench_audit';OUT=ROOT/'outputs/research/revision/power_attribution/source_screening';OUT.mkdir(exist_ok=True)
sha='9a50272213885bd9bba8427e34ebdf345c2204fe';tree=json.loads((SRC/'tree.json').read_text());assert tree['sha']==sha
paths=[x['path'] for x in tree['tree'] if x['type']=='blob' and ((x['path'].startswith('results/') and x['path'].endswith('.json')) or x['path'].startswith('tokenpowerbench/energy/'))]

def download(p):
    f=SRC/p;url=f'https://raw.githubusercontent.com/chenxuniu/TokenPowerBench/{sha}/{p}'
    if not f.exists():
        data=urllib.request.urlopen(url,timeout=45).read();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    return dict(path=p,url=url,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest())
manifest=[];errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    future={pool.submit(download,p):p for p in paths}
    for f in concurrent.futures.as_completed(future):
        try:manifest.append(f.result())
        except Exception as e:errors.append(dict(path=future[f],error=str(e)))
records=[];fields=set()
def walk(obj,path):
    if isinstance(obj,dict):
        fields.update(obj)
        if 'gpu_energy' in obj and 'duration' in obj:
            records.append(dict(path=path,duration=obj.get('duration'),gpu_energy=obj.get('gpu_energy'),total_energy=obj.get('total_energy'),total_avg_power=obj.get('total_avg_power'),cpu_energy=obj.get('cpu_energy'),dram_energy=obj.get('dram_energy'),system_energy_j=obj.get('system_energy_j')))
        for v in obj.values():walk(v,path)
    elif isinstance(obj,list):
        for v in obj:walk(v,path)
for item in manifest:
    if item['path'].endswith('.json'):
        try:walk(json.loads((SRC/item['path']).read_text()),item['path'])
        except Exception as e:errors.append(dict(path=item['path'],error=str(e)))
isnum=lambda x:isinstance(x,(int,float))
summary=dict(commit=sha,downloaded_files=len(manifest),result_files=sum(x['path'].endswith('.json') for x in manifest),download_errors=errors,records=len(records),
    positive_reported_total_average_power=sum(isnum(r['total_avg_power']) and r['total_avg_power']>0 for r in records),
    total_energy_equals_gpu_energy=sum(isnum(r['total_energy']) and isnum(r['gpu_energy']) and abs(r['total_energy']-r['gpu_energy'])<1e-8 for r in records),
    zero_cpu_and_dram=sum(r['cpu_energy']==0 and r['dram_energy']==0 for r in records),
    positive_explicit_system_energy_j=sum(isnum(r['system_energy_j']) and r['system_energy_j']>0 for r in records),
    power_control_fields=[k for k in sorted(fields) if any(x in k.lower() for x in ['power_cap','power_limit','clock','frequency','ipmi','system_energy'])],
    scope='Audit of existing public result fields and current collection code. A label total_energy is not certification of AC/node measurement, DVFS control or fixed useful work.')
(OUT/'tokenpowerbench_manifest.json').write_text(json.dumps(dict(commit=sha,files=sorted(manifest,key=lambda x:x['path']),errors=errors),indent=2)+'\n')
(OUT/'tokenpowerbench_audit.json').write_text(json.dumps(summary,indent=2)+'\n');(OUT/'tokenpowerbench_records.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(summary,indent=2))
