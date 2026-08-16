import argparse
from pathlib import Path
import pandas as pd

def main(path):
    df = pd.read_parquet(path)
    failures=[]
    for iso3 in ["ITA","DEU","FRA","USA","CHN"]:
        if df[df.iso3==iso3].empty: failures.append(f"{iso3}: no rows")
    tas_abs=df[(df.indicator=="tas")&(df.value_type=="climatology")]
    tas_anom=df[(df.indicator=="tas")&(df.value_type=="anomaly")]
    hot=df[df.indicator.isin(["hd30","hd35"])&(df.value_type=="climatology")]
    if not tas_abs.empty and not tas_abs.value.between(-60,50).all(): failures.append("tas climatology range")
    if not tas_anom.empty and not tas_anom.value.between(-2,10).all(): failures.append("tas anomaly range")
    if not hot.empty and not hot.value.between(0,366).all(): failures.append("hot days range")
    piv=df.pivot_table(index=["iso3","indicator","scenario","period","value_type"],columns="statistic",values="value",aggfunc="first").reset_index()
    if {"p10","median","p90"}.issubset(piv.columns):
        bad=piv[(piv.p10>piv["median"])|(piv["median"]>piv.p90)]
        if len(bad): failures.append(f"percentile ordering failures={len(bad)}")
    print("rows=",len(df),"countries=",df.iso3.nunique())
    print("indicators=",sorted(df.indicator.unique()))
    print("scenarios=",sorted(df.scenario.unique()))
    print("periods=",sorted(df.period.unique()))
    if failures:
        print("VALIDATION: FAIL")
        for f in failures: print("-",f)
        raise SystemExit(1)
    print("VALIDATION: PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",nargs="?",default="data/climate_intelligence/cckp_country_projections.parquet")
    main(p.parse_args().path)
