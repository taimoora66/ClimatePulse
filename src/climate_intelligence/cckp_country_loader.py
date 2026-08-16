from functools import lru_cache
from pathlib import Path
import pandas as pd

DEFAULT_PATH = Path("data/climate_intelligence/cckp_country_projections.parquet")

@lru_cache(maxsize=1)
def load_cckp_country_projections(path=str(DEFAULT_PATH)):
    p=Path(path)
    return pd.DataFrame() if not p.exists() else pd.read_parquet(p)

def get_country_projection(iso3, scenario="ssp245", indicator="tas", value_type="anomaly", path=str(DEFAULT_PATH)):
    df=load_cckp_country_projections(path)
    if df.empty: return df
    out=df[(df.iso3.str.upper()==iso3.upper())&(df.scenario==scenario)&(df.indicator==indicator)&(df.value_type==value_type)].copy()
    return out

def country_projection_wide(iso3, scenario="ssp245", indicator="tas", value_type="anomaly", path=str(DEFAULT_PATH)):
    d=get_country_projection(iso3,scenario,indicator,value_type,path)
    if d.empty: return d
    return d.pivot_table(index=["iso3","country","indicator","scenario","period","unit"],columns="statistic",values="value",aggfunc="first").reset_index().sort_values("period")
