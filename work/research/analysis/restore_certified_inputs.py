"""Restore a bounded certified-power input chain from public URLs, fail closed.

Run only in a separate checkout. No local source-cache fallback. Original
certificates and source digests are never rewritten to admit changed downloads.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import struct
import urllib.request
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / 'outputs/research/revision/clean_reconstruction/source_spec.json'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def destination(relative):
    target = (ROOT / relative).resolve()
    if not target.is_relative_to(ROOT.resolve()) or not relative.startswith('work/research/'):
        raise ValueError('Output path outside admitted research input tree')
    return target


def write_verified(relative, body, expected):
    actual = sha(body)
    if actual != expected:
        raise ValueError(f'SHA256 mismatch for {relative}: expected {expected}, received {actual}')
    target = destination(relative)
    if target.exists():
        if sha(target.read_bytes()) != expected:
            raise ValueError(f'Existing mismatched input preserved: {relative}')
        return dict(path=relative, status='existing_exact', sha256=actual, bytes=len(body))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as output:
        output.write(body)
    return dict(path=relative, status='restored_exact', sha256=actual, bytes=len(body))


def fetch(url, *, maximum_bytes, byte_range=None):
    headers = {'User-Agent': 'research-reconstruction/1.0'}
    if byte_range is not None:
        start, end, total = byte_range
        headers['Range'] = f'bytes={start}-{end}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
        if byte_range is not None:
            expected = f'bytes {start}-{end}/{total}'
            if response.status != 206 or response.headers.get('Content-Range') != expected:
                raise ValueError('Range response status/extent mismatch; full-archive fallback disabled')
        elif response.status != 200:
            raise ValueError('Unexpected HTTP status')
        body = response.read(maximum_bytes + 1)
        if len(body) > maximum_bytes:
            raise ValueError('Response exceeds declared byte budget')
        if byte_range is not None and len(body) != end-start+1:
            raise ValueError('Range response is incomplete')
        return body


def restore_helios(spec):
    source = spec['helios']
    body = fetch(source['url'], maximum_bytes=source['bytes'])
    if len(body) != source['bytes'] or sha(body) != source['sha256']:
        raise ValueError('Pinned Helios archive size/hash mismatch')
    records = []
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        for relative, expected in spec['policy_input_sha256'].items():
            prefix = 'work/research/sources/helios_sensetime/'
            if relative.startswith(prefix):
                name = relative[len(prefix):]
                info = archive.getinfo(name)
                if info.file_size > 200_000_000:
                    raise ValueError('Unexpected member size')
                # Explicit members only, no extractall or execution of archive code.
                records.append(write_verified(relative, archive.read(name), expected))
    return records


def restore_load_member(spec):
    member, archive = spec['load_member'], spec['archive']
    offset = member['offset']; url = archive['links']['self']; total = archive['size']
    header = fetch(url, maximum_bytes=30, byte_range=(offset, offset+29, total))
    if header[:4] != b'PK\x03\x04':
        raise ValueError('Not a ZIP local header')
    method = struct.unpack_from('<H', header, 8)[0]
    fn, extra = struct.unpack_from('<HH', header, 26)
    if method != member['compression'] or fn+extra > 100_000:
        raise ValueError('Member compression/header differs')
    metadata = fetch(url, maximum_bytes=fn+extra, byte_range=(offset+30, offset+29+fn+extra, total))
    if metadata[:fn].decode('utf-8') != member['name']:
        raise ValueError('ZIP member name mismatch')
    start = offset+30+fn+extra
    compressed = fetch(url, maximum_bytes=member['compressed_bytes'],
                       byte_range=(start,start+member['compressed_bytes']-1,total))
    body = zlib.decompress(compressed, -15)
    if len(body) != member['bytes'] or zlib.crc32(body) != member['crc32']:
        raise ValueError('Load member CRC32/size mismatch')
    return [write_verified(member['local_path'],body,member['sha256'])]


def rebuild_load(spec):
    import numpy as np
    import pandas as pd
    import h5py
    transcription = spec['transcription']
    p = destination(transcription['path'])
    if sha(p.read_bytes()) != transcription['sha256']:
        raise ValueError('Tracked transcription changed')
    member = spec['load_member']; path = destination(member['local_path'])
    if sha(path.read_bytes()) != member['sha256']:
        raise ValueError('HDF source member changed')
    # Rebuild only the required load array; do not import the historical audit
    # that also requires unrelated wind/hydro/capacity and 2018 source files.
    with h5py.File(path) as h:
        g=h['load']; labels=[x.decode() for x in g['block0_items'][...]]
        array=g['block0_values'][...]; raw_clock=g['axis1'][...]; tz=g['axis1'].attrs.get('tz')
    if array.dtype.kind != 'f':
        raise ValueError('Non-numeric HDF dataset')
    clock = pd.to_datetime(raw_clock,utc=True).tz_convert(tz.decode()) if tz is not None else pd.to_datetime(raw_clock).tz_localize('Asia/Shanghai')
    observations=pd.read_csv(p).set_index('province')
    names=np.array(sorted(observations.index),dtype='U20')
    data=pd.DataFrame(array,index=clock,columns=labels)[list(names)]
    expected=pd.date_range('2020-01-01',periods=8784,freq='h',tz='Asia/Shanghai',unit='ns')
    if len(names)!=31 or not clock.equals(expected) or data.shape!=(8784,31):
        raise ValueError('Province/calendar shape mismatch')
    # The frozen prepared input uses C order. Summation across a Fortran-order
    # array changes floating-point accumulation and therefore the original hash.
    # Make the historical layout explicit instead of relaxing the certificate.
    power=np.ascontiguousarray(data.to_numpy()*1e6)
    if not np.isfinite(power).all() or (power<0).any():
        raise ValueError('Nonfinite/negative source demand')
    target=observations.loc[names].electricity_2020_100million_kWh.to_numpy(dtype=float)/10
    annual=power.sum(axis=0)/1e6; factors=target/annual; adjusted=power*factors[None,:]
    if not np.allclose(adjusted.sum(axis=0)/1e6,target,rtol=0,atol=1e-9):
        raise ValueError('Annual energy reconstruction differs')
    buffer=io.BytesIO()
    np.savez_compressed(buffer,timestamps_UTC_ns=expected.tz_convert('UTC').as_unit('ns').asi8,
        provinces=names,load_MW=adjusted,annual_targets_TWh=target,annual_scaling_factors=factors,
        status=np.array('Annual energy anchored; hourly shape NOT independently validated'))
    return [write_verified(spec['prepared_target']['path'],buffer.getvalue(),spec['prepared_target']['sha256'])]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--fetch',action='store_true',help='Fetch and verify external sources, including existing inputs')
    mode.add_argument('--rebuild-only',action='store_true',help='Rebuild from already restored, hash-verified load sources; no network')
    parser.add_argument('--report',default='work/tmp/reconstruction/input_restore.json')
    args=parser.parse_args()
    spec=json.loads(SPEC.read_text()); started=datetime.now(timezone.utc).isoformat()
    jobs=[('helios_pinned_archive',lambda:restore_helios(spec)),('archive_load_member',lambda:restore_load_member(spec))]
    for item in spec['tariffs']:
        def action(item=item):
            body=fetch(item['url'],maximum_bytes=10_000_000)
            return [write_verified(item['path'],body,spec['policy_input_sha256'][item['path']])]
        jobs.append((item['path'],action))
    def attempt(job):
        name,action=job
        try:
            return dict(step=name,ok=True,files=action())
        except Exception as exc:
            return dict(step=name,ok=False,error_type=type(exc).__name__,error=str(exc))
    results=[]
    if args.fetch:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(attempt,jobs))
    results.append(attempt(('rebuild_prepared_load',lambda:rebuild_load(spec))))
    admitted=[]
    for relative,expected in {**spec['policy_input_sha256'],spec['prepared_target']['path']:spec['prepared_target']['sha256']}.items():
        path=ROOT/relative
        actual=sha(path.read_bytes()) if path.exists() else None
        admitted.append(dict(path=relative,expected_sha256=expected,actual_sha256=actual,exact=actual==expected))
    report=dict(started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
        source_spec_sha256=sha(SPEC.read_bytes()),steps=results,admission=admitted,
        all_inputs_admitted=all(x['exact'] for x in admitted),
        network_requested=args.fetch,local_cache_fallback=False,full_archive_checksum_verified=False,
        scope='Bounded input reconstruction, not independent physical validation or full manuscript reproduction')
    out=ROOT/args.report
    if not out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Report must stay in checkout')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(all_inputs_admitted=report['all_inputs_admitted'],steps=[{k:v for k,v in x.items() if k!='files'} for x in results],report=str(out)),indent=2),flush=True)
    return 0 if report['all_inputs_admitted'] else 1


if __name__=='__main__':
    raise SystemExit(main())
