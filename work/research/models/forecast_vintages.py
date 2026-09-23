"""Select whole, provenance-admitted curves available at a decision cutoff.

Admission is an external source-review decision, not inferred from a rule's
deadline, filename, download time or model accuracy. This module only checks
the consistency of that review and selects the latest complete eligible curve.
"""
import copy
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta


def timestamp(value):
    if not isinstance(value,str):raise ValueError('ISO timestamp required')
    out=datetime.fromisoformat(value.replace('Z','+00:00'))
    if out.tzinfo is None or out.utcoffset() is None:raise ValueError('Timezone offset required')
    return out.astimezone(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def select_curve(curves,admissions,*,decision_at,delivery_start,periods,interval_minutes,series_id,unit,kind='forecast'):
    """Return an explicit unavailable/ambiguous state instead of imputing data.

Each admission binds the entire normalized snapshot hash, raw-source hash,
publication-evidence hash and verified availability timestamp. Authenticity
and extraction fidelity must be checked before populating admissions. All
times are offset-aware. Interval timestamps denote starts, never interval ends.
The selector does not resample, fill, merge versions or read realized targets.
    """
    cutoff=timestamp(decision_at);start=timestamp(delivery_start)
    if isinstance(periods,bool) or not isinstance(periods,int) or periods<=0 or isinstance(interval_minutes,bool) or not isinstance(interval_minutes,int) or interval_minutes<=0:
        raise ValueError('Positive integer periods and interval minutes required')
    if cutoff>start or kind not in ['forecast','announced_price'] or not series_id or not unit:
        raise ValueError('Invalid requested decision horizon or signal kind')
    expected=[start+timedelta(minutes=interval_minutes*i) for i in range(periods)]
    ids=[r.get('snapshot_id') for r in curves]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Distinct snapshot ids required')
    eligible=[];audit=[]
    for record in curves:
        rid=record['snapshot_id'];reasons=[]
        if any(record.get(k)!=v for k,v in [('series_id',series_id),('unit',unit),('kind',kind),('interval_minutes',interval_minutes)]):
            reasons.append('signal_scope_mismatch')
        approval=admissions.get(rid)
        available=None
        try:
            available=timestamp(record['available_at'])
            if available>cutoff:reasons.append('published_after_decision')
            times=[timestamp(t) for t in record['interval_starts']]
            if times!=expected:reasons.append('incomplete_or_misaligned_horizon')
            values=record['values']
            if len(values)!=periods or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
                reasons.append('invalid_values')
            payload_hash=digest(record)
        except (KeyError,ValueError,TypeError,OverflowError):
            reasons.append('malformed_snapshot');payload_hash=None
        if not approval:
            reasons.append('no_source_admission')
        else:
            if approval.get('evidence_kind') not in ['archived_version_record','contemporaneous_capture','publisher_release_record']:
                reasons.append('unsupported_availability_evidence')
            if approval.get('snapshot_sha256')!=payload_hash or payload_hash is None:
                reasons.append('snapshot_hash_mismatch')
            if approval.get('source_sha256')!=record.get('source_sha256') or not _sha(approval.get('source_sha256')):
                reasons.append('raw_source_hash_mismatch')
            if not _sha(approval.get('availability_evidence_sha256')):
                reasons.append('missing_availability_evidence')
            try:
                if timestamp(approval['verified_available_at'])!=available:reasons.append('availability_timestamp_mismatch')
            except (KeyError,TypeError,ValueError):reasons.append('availability_timestamp_mismatch')
        audit.append(dict(snapshot_id=rid,eligible=not reasons,reasons=reasons))
        if not reasons:eligible.append((available,record))
    result=dict(status='unavailable',selected=None,audit=audit,decision_at=cutoff.isoformat(),
        scope='Consistency of externally reviewed source admission, not independent proof of historical availability')
    if not eligible:return result
    latest=max(t for t,r in eligible);winners=[r for t,r in eligible if t==latest]
    if len(winners)!=1:
        result['status']='ambiguous_latest_release';result['ambiguous_snapshot_ids']=[r['snapshot_id'] for r in winners]
        return result
    result.update(status='selected',selected=copy.deepcopy(winners[0]))
    return result


def _sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
