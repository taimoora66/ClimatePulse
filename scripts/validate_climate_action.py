from pathlib import Path
import pandas as pd
p=Path('data/climate_intelligence/edgar_country_emissions.parquet'); d=pd.read_parquet(p); assert {'iso3','year','value_mtco2e'}.issubset(d.columns); assert d.year.between(1970,2024).all(); assert d.value_mtco2e.ge(0).all(); assert d.duplicated(['iso3','year']).sum()==0; print('COUNTRY',len(d),'rows',d.iso3.nunique(),'entities',int(d.year.min()),int(d.year.max())); s=Path('data/climate_intelligence/edgar_sector_emissions.parquet'); print('SECTOR',len(pd.read_parquet(s)) if s.exists() else 'missing'); print('VALIDATION COMPLETE')
