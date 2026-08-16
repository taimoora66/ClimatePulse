from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
OUT=Path('data/climate_intelligence/cat_country_ratings.parquet')
def pick(cols,terms):
    for t in terms:
        for c in cols:
            if t.lower() in str(c).lower(): return c
    return None
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); args=ap.parse_args(); d=pd.read_csv(args.input); iso=pick(d.columns,['iso3','iso code','country code']); country=pick(d.columns,['country']); rating=pick(d.columns,['overall rating','rating']); update=pick(d.columns,['update date','update'])
    if country is None or rating is None: raise RuntimeError(f'Cannot identify country/rating: {d.columns.tolist()}')
    out=pd.DataFrame({'iso3':d[iso].astype(str).str.upper().str.strip() if iso else '','country':d[country].astype(str).str.strip(),'overall_rating':d[rating].astype(str).str.strip(),'source':'Climate Action Tracker country ratings'})
    if update: out['update_date']=d[update]
    OUT.parent.mkdir(parents=True,exist_ok=True); out.to_parquet(OUT,index=False); out.to_csv(OUT.with_suffix('.csv'),index=False); print('[done]',OUT,len(out));
    if not iso: print('[note] source CSV lacks ISO3; add a crosswalk before app use')
if __name__=='__main__':main()
