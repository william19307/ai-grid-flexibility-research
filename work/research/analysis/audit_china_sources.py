"""Source consistency audit. Does not certify physical network accuracy."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'work/research/sources'
OUT = ROOT / 'outputs/research'
PREP = ROOT / 'work/research/prepared'
PREP.mkdir(exist_ok=True)
z = SRC / 'zenodo_8322210'
load_path = z / 'Appendix 1_Hourly electric power load final.csv'
model_path = SRC / 'PyPSA-China/resources/data/load/Hourly_demand_of_31_province_China_modified_V2.1.csv'
raw = pd.read_csv(load_path, sep=';')
ref = pd.read_csv(model_path)
assert len(raw) == 8760 and np.array_equal(raw.iloc[:, 0], np.arange(1, 8761))
assert not raw.isna().any().any()
assert (raw.iloc[:, 1:] >= 0).all().all()
mapping = []
for col in raw.columns[1:]:
    matches = [c for c in ref.columns[1:] if np.array_equal(raw[col], ref[c])]
    assert len(matches) == 1, (col, matches)
    mapping.append({'parsed_original_column': col, 'canonical_province': matches[0],
                    'matching_hours': 8760, 'maximum_absolute_difference': 0.0})
assert len({r['canonical_province'] for r in mapping}) == 31
pd.DataFrame(mapping).to_csv(OUT / 'tables/china_load_column_mapping.csv', index=False)
clean = raw.iloc[:, 1:].rename(columns={r['parsed_original_column']: r['canonical_province'] for r in mapping})
clean = clean[sorted(clean.columns)]
clean.index = pd.date_range('2018-01-01', periods=8760, freq='h', tz='Asia/Shanghai')
clean.index.name = 'timestamp_UTC_plus_08'
clean.to_csv(PREP / 'china_load_2018_reconstructed_MWh_per_hour.csv')
stats = []
for c in clean:
    s = clean[c]
    stats.append({'province': c, 'annual_energy_TWh': s.sum()/1e6,
                  'maximum_hourly_average_GW': s.max()/1000,
                  'minimum_hourly_average_GW': s.min()/1000,
                  'load_factor': s.mean()/s.max(), 'source_year': 2018,
                  'measurement_type': 'reconstructed_from_daily_extrema_and_typical_profiles'})
pd.DataFrame(stats).to_csv(OUT / 'tables/china_load_2018_descriptive.csv', index=False)

xlsx = z / 'Appendix 3_Transmission lines between provinces.xlsx'
net_summary, conflicts, duplicate_candidates = [], [], []
for sheet in ['HVAC', 'HVDC']:
    lines = pd.read_excel(xlsx, sheet_name=sheet)
    matrix = pd.read_excel(xlsx, sheet_name=sheet+'_Matrix', index_col=0)
    assert list(matrix.index) == list(matrix.columns)
    assert (matrix.to_numpy() >= 0).all()
    assert np.allclose(matrix, matrix.T)
    rebuilt = pd.DataFrame(0., index=matrix.index, columns=matrix.columns)
    for _, r in lines.iterrows():
        a, b, v = r['From Province'], r['To Province'], r['Power Capacity (GW)']
        assert a in rebuilt.index and b in rebuilt.columns and a != b
        rebuilt.loc[a, b] += v
        rebuilt.loc[b, a] += v
    for i in range(len(matrix)):
        for j in range(i+1, len(matrix)):
            if not np.isclose(matrix.iloc[i, j], rebuilt.iloc[i, j]):
                conflicts.append({'source_sheet': sheet, 'province_1': matrix.index[i],
                                  'province_2': matrix.columns[j],
                                  'line_list_GW': rebuilt.iloc[i, j],
                                  'published_matrix_GW': matrix.iloc[i, j],
                                  'difference_GW': matrix.iloc[i, j]-rebuilt.iloc[i, j]})
    # Same endpoints/rating can be separate assets. Flag; never deduplicate by tuple.
    dup = lines[lines.duplicated(subset=list(lines.columns[1:]), keep=False)].copy()
    for _, r in dup.iterrows():
        duplicate_candidates.append({'source_sheet': sheet, **r.to_dict(),
                                     'status': 'requires_project_identity_check_not_automatic_deletion'})
    rebuilt.to_csv(PREP / f'{sheet}_source_list_rebuilt_UNVERIFIED_GW.csv')
    net_summary.append({'source_sheet': sheet, 'listed_rows': len(lines),
                        'listed_capacity_sum_GW': float(lines['Power Capacity (GW)'].sum()),
                        'published_matrix_sum_divided_by_two_GW': float(matrix.to_numpy().sum()/2),
                        'mismatched_undirected_pairs': sum(r['source_sheet']==sheet for r in conflicts),
                        'appendix4_table_classification': 'HVDC' if sheet=='HVAC' else 'HVAC',
                        'approved_for_grid_results': False})
pd.DataFrame(conflicts).to_csv(OUT / 'tables/china_transmission_matrix_conflicts.csv', index=False)
pd.DataFrame(duplicate_candidates).to_csv(OUT / 'tables/china_transmission_identity_checks.csv', index=False)

files = [load_path, model_path, xlsx]
provenance = [{'path': str(f.relative_to(ROOT)), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()} for f in files]
summary = {'source': 'https://doi.org/10.5281/zenodo.8322210', 'license': 'CC-BY-4.0',
           'load': {'hours': len(clean), 'provinces': len(clean.columns), 'year': 2018,
                    'type': 'reconstructed_not_raw_hourly_metering',
                    'equal_to_PyPSA_China_after_column_mapping': True,
                    'national_annual_TWh': float(clean.to_numpy().sum()/1e6),
                    'HB_first_occurrence_maps_to': 'HE (Hebei)', 'HB_second_occurrence_maps_to': 'HB (Hubei)',
                    'permission': 'historical_shape_prototyping_only; recent_base_year_validation_pending'},
           'transmission': net_summary,
           'remaining_network_checks': ['Appendix 3 sheet names opposite Appendix 4 table headings',
                 'three undirected matrix/list conflicts in sheet HVDC',
                 'project identity, duplicate aliases, endpoints, capacity and commissioning dates need verification',
                 'rated capacities are not available transfer capability; do not count symmetric entries twice'],
           'provenance': provenance}
(OUT / 'tables/china_source_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
