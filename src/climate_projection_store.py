from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import pandas as pd

DEFAULT_PARQUET = Path('data/climate_intelligence/cckp_country_projections.parquet')
DEFAULT_CSV = Path('data/climate_intelligence/cckp_country_projections.csv')
SCENARIOS = {'ssp126':'SSP1–2.6 · Low emissions','ssp245':'SSP2–4.5 · Intermediate','ssp370':'SSP3–7.0 · High','ssp585':'SSP5–8.5 · Very high'}
PERIODS = ('2020-2039','2040-2059','2060-2079','2080-2099')
STATS = ('p10','median','p90')

@lru_cache(maxsize=4)
def _read(path_string: str) -> pd.DataFrame:
    p = Path(path_string)
    d = pd.read_parquet(p) if p.suffix.lower()=='.parquet' else pd.read_csv(p)
    required={'iso3','country','indicator','scenario','period','statistic','value_type','value','unit'}
    missing=required-set(d.columns)
    if missing: raise ValueError('Missing CCKP columns: '+', '.join(sorted(missing)))
    d=d.copy(); d['iso3']=d.iso3.astype(str).str.upper().str.strip(); d['value']=pd.to_numeric(d.value,errors='coerce')
    for c in ['indicator','scenario','period','statistic','value_type']: d[c]=d[c].astype(str).str.lower().str.strip()
    d['country']=d.country.astype(str).str.strip()
    return d

def load_cckp(path=None):
    candidates=[Path(path)] if path else []
    candidates += [DEFAULT_PARQUET,DEFAULT_CSV]
    for p in candidates:
        if p.exists(): return _read(str(p.resolve())),p
    raise FileNotFoundError('Validated CCKP production dataset not found at data/climate_intelligence/cckp_country_projections.parquet (or CSV fallback).')

def catalog(d): return d[['iso3','country']].drop_duplicates().sort_values(['country','iso3']).reset_index(drop=True)

def default_iso3(d, preferred=None):
    codes=set(d.iso3)
    if preferred and str(preferred).upper() in codes: return str(preferred).upper()
    return 'ITA' if 'ITA' in codes else sorted(codes)[0]

def slice_data(d, **filters):
    out=d
    for key,val in filters.items():
        if val is None: continue
        if key=='iso3' and isinstance(val,(list,tuple,set)): out=out[out.iso3.isin([str(x).upper() for x in val])]
        elif key=='iso3': out=out[out.iso3.eq(str(val).upper())]
        else: out=out[out[key].eq(val)]
    return out.copy()

def triplet(d, iso3, indicator, scenario, period, value_type):
    x=slice_data(d,iso3=iso3,indicator=indicator,scenario=scenario,period=period,value_type=value_type)
    result={'p10':None,'median':None,'p90':None}
    for s in result:
        v=x.loc[x.statistic.eq(s),'value']
        if not v.empty: result[s]=float(v.iloc[0])
    return result

def trajectory(d, iso3, indicator, scenario, value_type):
    x=slice_data(d,iso3=iso3,indicator=indicator,scenario=scenario,value_type=value_type)
    if x.empty: return x
    p=x.pivot_table(index='period',columns='statistic',values='value',aggfunc='first').reset_index()
    order={v:i for i,v in enumerate(PERIODS)}; p['_o']=p.period.map(order)
    return p.sort_values('_o').drop(columns='_o')
