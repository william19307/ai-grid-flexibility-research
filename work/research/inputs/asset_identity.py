"""Project alias resolution for research candidates, never dispatch admission.

No distance/name matching is performed here. Only explicit reviewed groups are
combined. Source rows remain addressable through the pinned input manifest.
"""
import copy
import hashlib
import json
from decimal import Decimal

SCHEMA = 'identity_resolved_thermal_candidates_v1'
MATCH_FIELDS = ('province', 'role', 'capacity_mw', 'new_build_capacity_mw',
                'candidate_technology', 'fuel', 'chp_evidence', 'captive_evidence',
                'conditional_parameter_reference')
SOURCE_MATCH_FIELDS = ('Unit / Phase name', 'Status', 'Start year', 'Retired year')


def resolve_aliases(staging, adjudication):
    if staging.get('schema') != 'thermal_technology_staging_v1':
        raise ValueError('Requires technology-preserving staging schema')
    if adjudication.get('schema') != 'asset_alias_adjudication_v1':
        raise ValueError('Unknown adjudication schema')
    stock = staging.get('stock', [])
    by_id = {r['unit_id']: r for r in stock}
    if not stock or len(by_id) != len(stock):
        raise ValueError('Missing or repeated source unit ID')
    for unit in stock:
        cap = Decimal(unit['capacity_mw'])
        if not cap.is_finite() or cap <= 0:
            raise ValueError('Invalid source capacity')
        if unit['role'] != 'existing_candidate_stock' or Decimal(unit['new_build_capacity_mw']) != 0:
            raise ValueError('Only existing candidate assets may be resolved')
    assignment = {}
    group_specs = []
    group_ids = set()
    decision_ids = set()
    for decision in adjudication.get('decisions', []):
        did = decision.get('decision_id')
        if not did or did in decision_ids:
            raise ValueError('Missing or duplicate decision identity')
        decision_ids.add(did)
        if decision.get('relation') != 'supported_same_asset_inference' or not decision.get('evidence_refs'):
            raise ValueError('Decision must be explicitly reviewed and source-referenced')
        if not decision.get('groups'):
            raise ValueError('Empty reviewed decision')
        for spec in decision['groups']:
            aid, ids = spec.get('asset_id'), spec.get('source_unit_ids', [])
            if not aid or aid in group_ids or aid in by_id or aid.startswith('inventory:'):
                raise ValueError('Invalid or repeated asset identity')
            if len(ids) < 2 or len(ids) != len(set(ids)):
                raise ValueError('Alias group must contain distinct source IDs')
            if any(uid not in by_id or uid in assignment for uid in ids):
                raise ValueError('Unknown or multiply assigned source record')
            members = [by_id[uid] for uid in ids]
            ref = members[0]
            for other in members[1:]:
                if any(ref[k] != other[k] for k in MATCH_FIELDS):
                    raise ValueError('Conflicting asset operating/classification fields require separate resolution')
                if any(ref['source_record'][k] != other['source_record'][k] for k in SOURCE_MATCH_FIELDS):
                    raise ValueError('Conflicting unit label/status/vintage requires separate resolution')
            group_ids.add(aid)
            assignment.update({uid: aid for uid in ids})
            group_specs.append((aid, sorted(ids), did))
    for uid in by_id:
        if uid not in assignment:
            group_specs.append(('inventory:' + uid, [uid], None))
    assets = []
    for aid, ids, did in sorted(group_specs):
        members = [by_id[uid] for uid in ids]
        unit = members[0]
        unresolved = sorted({v for m in members for v in m['unresolved_requirements']}
                            | {'complete_asset_identity_and_current_existence_review'})
        assets.append(dict(asset_id=aid, source_unit_ids=ids, adjudication_id=did,
                           identity_basis='reviewed_alias_inference' if did else 'unreviewed_inventory_identity',
                           **{k: copy.deepcopy(unit[k]) for k in MATCH_FIELDS},
                           source_unit_label_status_vintage={k: unit['source_record'][k] for k in SOURCE_MATCH_FIELDS},
                           unresolved_requirements=unresolved, dispatch_ready=False))
    source_total = sum(Decimal(r['capacity_mw']) for r in stock)
    asset_total = sum(Decimal(r['capacity_mw']) for r in assets)
    return dict(schema=SCHEMA, scope='RESEARCH_CANDIDATES_NOT_OPERATIONAL_INPUT',
                vintage=staging['vintage'],
                reviewed_on=adjudication['reviewed_on'], asset_candidates=assets,
                source_units=[dict(unit_id=r['unit_id'], source_record_sha256=r['source_record_sha256']) for r in stock],
                investment_options=copy.deepcopy(staging['investment_options']),
                conditional_parameters=copy.deepcopy(staging['conditional_parameters']),
                source_capacity_mw=str(source_total), resolved_candidate_capacity_mw=str(asset_total),
                alias_counting_difference_mw=str(source_total-asset_total),
                qualified_operational_parameter_sets=0)


def resolve_pinned_file(path, adjudication):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != adjudication.get('source_staging_sha256'):
        raise ValueError('Source staging bytes differ from the reviewed version')
    result = resolve_aliases(json.loads(raw), adjudication)
    result['source_staging_sha256'] = hashlib.sha256(raw).hexdigest()
    return result
