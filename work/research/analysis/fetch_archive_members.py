"""Fetch specific public ZIP members using verified HTTP byte ranges.

No full-archive checksum is claimed. Check member size/CRC32 and retain local
SHA256, archive record, central-directory metadata and exact member path.
"""
from pathlib import Path,PurePosixPath
import json,requests,struct,zlib,hashlib
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/zenodo_13987282'
record=json.loads((SRC/'record.json').read_text());archive=record['files'][0]
index=json.loads((SRC/'archive_index.json').read_text())
PREFIX='PyPSA-China-main /'

def byte_range(start,end):
    expected=f'bytes {start}-{end}/{archive["size"]}'
    with requests.get(archive['links']['self'],headers={'Range':f'bytes={start}-{end}'},
                      stream=True,timeout=(20,60)) as r:
        if r.status_code!=206 or r.headers.get('Content-Range')!=expected:
            raise RuntimeError(('unexpected range response',r.status_code,r.headers.get('Content-Range'),expected))
        content=r.content
    assert len(content)==end-start+1
    return content

def fetch(member):
    name=member['name'];relative=PurePosixPath(name.removeprefix(PREFIX))
    assert name.startswith(PREFIX) and not relative.is_absolute() and '..' not in relative.parts
    assert member['bytes']<20000000 and member['compressed_bytes']<20000000
    offset=member['offset'];header=byte_range(offset,offset+29)
    assert header[:4]==b'PK\x03\x04'
    filename_len,extra_len=struct.unpack_from('<HH',header,26)
    start=offset+30+filename_len+extra_len
    compressed=byte_range(start,start+member['compressed_bytes']-1)
    if member['compression']==8:body=zlib.decompress(compressed,-15)
    elif member['compression']==0:body=compressed
    else:raise ValueError('Unsupported ZIP compression')
    assert len(body)==member['bytes']
    assert zlib.crc32(body)==member['crc32']
    dst=SRC/'selected'/str(relative);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(body)
    return {**member,'local_path':str(dst.relative_to(ROOT)),'sha256':hashlib.sha256(body).hexdigest(),
            'member_crc_and_size_verified':True,'full_archive_checksum_verified':False}

if __name__=='__main__':
    exact={'resources/profile_onwind.nc','resources/profile_solar.nc','resources/profile_offwind.nc',
       'config.yaml','README.md','scripts/build_renewable_potential.py','scripts/build_load_profiles.py',
       'scripts/prepare_base_network_2020.py','scripts/prepare_base_network.py',
       'data/costs/costs_2020.csv','data/costs/costs_2030.csv','data/costs/costs_2035.csv',
       'data/p_nom/hydro_p_nom.h5','data/p_nom/hydro_p_max_pu.h5',
       'data/load/load_2020_weatheryears_1979_2016_TWh.h5',
       'data/load/Province_Load_2020_2060.csv'}
    members=[x for x in index if x['name'].startswith(PREFIX) and
       (x['name'][len(PREFIX):] in exact or
        (x['name'].startswith(PREFIX+'data/existing_infrastructure/') and x['name'].endswith('capacity.csv')) or
        (x['name'].startswith(PREFIX+'data/grids/') and x['name'].endswith('.csv')) or
        (x['name'].startswith(PREFIX+'data/hydro/') and x['name'].endswith(('.csv','.pickle'))))]
    results=[]
    with ThreadPoolExecutor(4) as pool:
        for item in pool.map(fetch,members):
            results.append(item);print('verified',item['name'],item['bytes'],flush=True)
            (SRC/'selected_members_manifest.json').write_text(json.dumps(results,indent=2))
    print('complete',len(results),'members',sum(x['bytes'] for x in results),'uncompressed bytes')
