# ORBIDENSE AI — Climate Intelligence V4

## Product changes

- Removes **Map Explorer** from public navigation because Home already owns the live map/location-discovery job.
- Removes standalone **Data & Methods** from public navigation. Methodology is contextual and expandable inside each analytical page.
- Replaces **Climate Timeline** with **Country Climate Outlook**.
- Replaces **Climate Trends** with **Climate Action & Progress**.

## Phase 1 — Country intelligence (implemented)

- Historical national climate using the existing World Bank CCKP/CRU pipeline.
- CMIP6 country projection trajectory through existing CCKP client with one selected SSP at a time for speed.
- Structured NDC target retrieval through Climate Watch/WRI, while clearly identifying the UNFCCC NDC Registry as authoritative for official submissions.
- Climate Action Tracker rating snapshot for covered countries, with update dates.
- Historical emissions via Climate Watch/CAIT where available.
- EDGAR 2025 workbook best-effort sector extraction with defensive failure behavior.
- Contextual methods/provenance, no black-box composite climate score.

## Phase 2 — City intelligence (framework + sync pipeline implemented)

- Local physical climate lens via existing Open-Meteo Climate CMIP6 ensemble.
- CDP city policy/profile adapter reads a preprocessed parquet only when a city is actually present.
- `scripts/sync_cdp_cities.py` conservatively preprocesses the public CDP workbook. Missing city reporting remains explicitly missing.

## Phase 3 — Sector transition intelligence (framework + sync pipeline implemented)

- EDGAR/available emissions sector structure.
- CAT 1.5°C sector benchmark adapter uses an explicit downloaded CAT dataset after sync/provenance check.
- `scripts/sync_cat_sector_benchmarks.py` normalizes the current CAT sector download.

## Validation

Run:

```powershell
python -m py_compile app.py
python -m compileall -q src scripts tests
python scripts/backtest_climate_intelligence.py
```

The backtest separates deterministic calculation checks from online provider availability checks. Online failures are reported as coverage/integration failures rather than replaced with fabricated values.
