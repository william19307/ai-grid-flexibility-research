"""Prepare source-model inputs without claiming a calibrated Chinese base year."""
from pathlib import Path
import json,hashlib
import h5py,pandas as pd,numpy as np,xarray as xr
ROOT=Path(__file__).resolve().parents[3]
SRC=ROOT/'work/research/sources/zenodo_13987282'
p=SRC/'selected';OUT=ROOT/'outputs/research/tables';PREP=ROOT/'work/research/prepared'
names=['Anhui','Beijing','Chongqing','Fujian','Gansu','Guangdong','Guangxi','Guizhou','Hainan','Hebei','Heilongjiang','Henan','Hubei','Hunan','InnerMongolia','Jiangsu','Jiangxi','Jilin','Liaoning','Ningxia','Qinghai','Shaanxi','Shandong','Shanghai','Shanxi','Sichuan','Tianjin','Tibet','Xinjiang','Yunnan','Zhejiang']
codes=['AH','BJ','CQ','FJ','GS','GD','GX','GZ','HI','HE','HL','HA','HB','HN','NM','JS','JX','JL','LN','NX','QH','SN','SD','SH','SX','SC','TJ','XZ','XJ','YN','ZJ']
mapping=dict(zip(names,codes))

def primitive_hdf_frame(file,key):
    # Read only numeric/string datasets; no pandas metadata unpickling.
    with h5py.File(file) as h:
        g=h[key];labels=[x.decode() for x in g['block0_items'][...]]
        arr=g['block0_values'][...]
        assert arr.dtype.kind=='f'
        idx=g['axis1'][...];tz=g['axis1'].attrs.get('tz')
        if tz is not None:
            idx=pd.to_datetime(idx,utc=True).tz_convert(tz.decode())
        else:
            idx=pd.to_datetime(idx).tz_localize('Asia/Shanghai')
        return pd.DataFrame(arr,index=idx,columns=labels)

load=primitive_hdf_frame(p/'data/load/load_2020_weatheryears_1979_2016_TWh.h5','load')[names]
assert load.shape==(8784,31) and not load.isna().any().any() and (load>=0).all().all()
expected=pd.date_range('2020-01-01',periods=8784,freq='h',tz='Asia/Shanghai')
assert load.index.equals(expected)
profiles={};profile_stats=[]
for tech in ['solar','onwind','offwind']:
    with xr.open_dataset(p/f'resources/profile_{tech}.nc',engine='h5netcdf') as ds:
        data=ds.profile.transpose('time','bus').to_pandas()
        data.index=data.index.tz_localize('Asia/Shanghai')
        assert data.index.equals(expected)
        assert not data.isna().any().any() and data.min().min()>=-1e-10 and data.max().max()<=1+1e-10
        profiles[tech]=data.reindex(columns=names)
        for bus in data:
            a=data[bus]
            profile_stats.append({'technology':tech,'province':bus,'hours':len(a),
                'mean_capacity_factor':float(a.mean()),'minimum':float(a.min()),'maximum':float(a.max()),
                'p_nom_max_source_assumption_MW':float(ds.p_nom_max.sel(bus=bus)),
                'mean_diurnal_peak_hour_UTC_plus_8':int(a.groupby(a.index.hour).mean().idxmax())})
pd.DataFrame(profile_stats).to_csv(OUT/'archive_2020_renewable_profile_audit.csv',index=False)
hydro=primitive_hdf_frame(p/'data/p_nom/hydro_p_max_pu.h5','hydro_p_max_pu')[names]
assert len(hydro)==8760 and not hydro.isna().any().any()
missing=expected.difference(hydro.index)
assert len(missing)==24 and all(t.month==2 and t.day==29 for t in missing)
hydro_common=float(np.ptp(hydro.to_numpy(),axis=1).max())
hydro_full=hydro.reindex(expected)
# Arrays retain all 8784 hours. Missing hydro/technology cells remain NaN.
# pandas 3 may infer microseconds. Serialize the declared unit explicitly.
timestamps_ns=expected.tz_convert('UTC').as_unit('ns').asi8
assert pd.to_datetime(timestamps_ns,unit='ns',utc=True).tz_convert('Asia/Shanghai').equals(expected.as_unit('ns'))
assert np.all(np.diff(timestamps_ns)==3_600_000_000_000)
np.savez_compressed(PREP/'archive_2020_source_inputs_NOT_calibrated.npz',
    timestamps_UTC_ns=timestamps_ns,provinces=np.array(names,dtype='U20'),
    load_MW=load.to_numpy()*1e6,solar_pu=profiles['solar'].to_numpy(),
    onwind_pu=profiles['onwind'].to_numpy(),offwind_pu=profiles['offwind'].to_numpy(),
    other_hydro_pu=hydro_full.to_numpy(),hydro_valid_hours=hydro_full.notna().all(axis=1).to_numpy())

proj=pd.read_csv(p/'data/load/Province_Load_2020_2060.csv',index_col=0)
assert np.allclose(load.sum(),proj.loc[names,'2020']/10)
historical=pd.read_csv(PREP/'china_load_2018_reconstructed_MWh_per_hour.csv',index_col=0)
load365=load[~((load.index.month==2)&(load.index.day==29))]
shape_stats=[]
for name in names:
    a=load365[name].to_numpy();b=historical[mapping[name]].to_numpy()
    shape_stats.append({'province':name,'correlation_2020_source_vs_2018_row_order':float(np.corrcoef(a,b)[0,1]),
       'max_mean_normalized_shape_difference':float(np.max(abs(a/a.mean()-b/b.mean()))),
       'interpretation':'similarity_check_not_proof_of_independent_validation'})
pd.DataFrame(shape_stats).to_csv(OUT/'archive_load_shape_comparison.csv',index=False)

rows=[]
for tech in ['onwind','offwind','solar','coal','CHP coal','OCGT','nuclear']:
    f=p/f'data/existing_infrastructure/{tech} capacity.csv'
    frame=pd.read_csv(f,index_col=0)
    for name,value in frame.select_dtypes('number').sum(axis=1).items():
        rows.append({'province':str(name).strip(),'technology':tech,'source_vintage_sum_MW':float(value),
                     'not_verified_as_2020_installed_capacity':True})
assets=pd.DataFrame(rows);assets.to_csv(OUT/'archive_capacity_vintage_sums_UNVERIFIED.csv',index=False)
totals=assets.groupby('technology').source_vintage_sum_MW.sum()
comparison=[('total_electricity_TWh',float(load.sum().sum()),7511.),
    ('wind_installed_MW',float(totals['onwind']+totals['offwind']),281530.),
    ('solar_installed_MW',float(totals['solar']),253430.),
    ('nuclear_installed_MW',float(totals['nuclear']),49890.)]
source_load='https://www.nea.gov.cn/2021-04/16/c_139884169.htm'
source_cap='https://www.stats.gov.cn/sj/zxfb/202302/t20230203_1901004.html'
comparison=[dict(metric=k,source_model_value=v,official_2020_value=o,
                relative_difference_pct=100*(v/o-1),official_source=source_load if i==0 else source_cap,
                interpretation='scope_and_year_reconciliation_required_not_a_passed_backtest') for i,(k,v,o) in enumerate(comparison)]
pd.DataFrame(comparison).to_csv(OUT/'archive_2020_official_aggregate_comparison.csv',index=False)
summary={'status':'source_inputs_prepared_NOT_calibrated_base_year','archive_doi':'10.5281/zenodo.13987282',
    'selected_member_count':len(json.loads((SRC/'selected_members_manifest.json').read_text())),
    'verification':'member CRC32/size and local SHA256; full 16.9GB archive not downloaded or hash-verified',
    'weather_profiles':{'year':2020,'hours':8784,'land_wind_provinces':31,'solar_provinces':31,'offshore_provinces':11,
        'timezone':'interpreted as UTC+8 from source build script +8h and consuming code localization; source numeric profiles have no timezone metadata'},
    'load':{'type':'source_model_scaled_input_not_independent_metered_2020',
        'annual_TWh':float(load.sum().sum()),'matches_source_annual_table':True,
        'min_shape_correlation_to_2018':min(x['correlation_2020_source_vs_2018_row_order'] for x in shape_stats)},
    'other_hydro':{'hours':8760,'missing_leapday_hours':24,'cross_province_profile_max_difference':hydro_common,
        'scope':'source script other existing hydro; major dam reservoirs handled separately, not all hydro'},
    'official_aggregate_comparison':comparison,
    'outstanding':['asset vintage inclusion/retirement and official provincial capacity reconciliation',
       'grid edge physical identity and available transfer capacity','major hydro inflows/reservoir constraints',
       'load regional/year scope and base-year dispatch calibration','independent weather years and uncertainty']}
(OUT/'archive_input_audit.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
