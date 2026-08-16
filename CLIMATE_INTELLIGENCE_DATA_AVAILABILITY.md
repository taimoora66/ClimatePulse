# ORBIDENSE AI — Climate Intelligence Data Availability

## Phase 1 — Country climate intelligence

| Product element | Source | Coverage | Refresh strategy | Implementation status |
|---|---|---|---|---|
| Historical national temperature / precipitation | World Bank CCKP / CRU pipeline already in ORBIDENSE | Broad global country coverage | Cache 24h+ | Implemented |
| CMIP6 country projections | World Bank CCKP | Broad global country coverage | Cache 24h; one SSP at a time | Implemented |
| Official NDC document status | UNFCCC NDC Registry | Paris Agreement Parties | Link/metadata source; do not scrape PDFs on page load | Provenance rule implemented |
| Structured quantified NDC fields | Climate Watch / WRI API | Broad but may lag the newest submission | Cache 6h; show missing honestly | Implemented |
| Independent country rating | Climate Action Tracker | Major emitters + CAT countries, not universal | Curated downloadable snapshot with update date | Implemented snapshot |
| Historical GHG emissions | Climate Watch / CAIT API | Broad global | Cache 6h | Implemented best-effort |
| Sector GHG emissions | EDGAR/JRC 2025 workbook | Global country-sector totals through 2024 | Cache workbook 24h | Implemented defensive parser |

## Phase 2 — City climate intelligence

| Product element | Source | Coverage | Refresh strategy | Implementation status |
|---|---|---|---|---|
| City/place physical climate projection | Open-Meteo Climate / CMIP6 HighResMIP point ensemble | Geographic point coverage | Cache 24h | Implemented |
| City emissions / target / target progress / climate risks | CDP Open Data 2025 | Reporting cities only; self-reported | Preprocess workbook offline, refresh by annual release | Sync pipeline implemented |
| City policy coverage badge | ORBIDENSE derived from CDP dataset presence | Exact disclosed city coverage | Static until sync | Implemented |

## Phase 3 — Sector transition intelligence

| Product element | Source | Coverage | Refresh strategy | Implementation status |
|---|---|---|---|---|
| Country sector emissions structure | EDGAR/JRC | Global | Annual release / cached workbook | Implemented |
| Sector indicators vs 1.5°C benchmarks | Climate Action Tracker Data Explorer | CAT-covered countries / indicators | Explicit dataset download and sync | Sync adapter implemented |
| Sector gap label | ORBIDENSE transparent arithmetic | Only where current value and benchmark share comparable units/direction | Recompute on sync | Implemented adapter; requires synced CAT dataset |

## Scientific guardrails

1. No current-weather observation is described as evidence of long-term climate change.
2. City point climate is not labelled as a city-boundary average.
3. National target ambition, policy implementation, emissions trend and physical climate risk are not collapsed into one opaque score.
4. CAT ratings are shown only for CAT-covered countries and carry an update date.
5. CDP city data is clearly identified as self-reported and shown only where a city appears in the public dataset.
6. CCKP p10/median/p90 is presented as model-ensemble spread, not as a probability forecast.
7. Missing provider data remains missing; ORBIDENSE does not substitute another geography.

## Recommended refresh jobs

- Live weather / AQI: existing minute-scale app cache.
- CCKP projection aggregates: 24 hours or longer.
- Climate Watch structured NDC: daily/weekly production refresh is sufficient.
- CAT ratings / emissions / sector downloads: refresh after CAT release/update, not per user request.
- EDGAR: refresh when a new annual EDGAR release is published.
- CDP cities: refresh when the annual public cities dataset is released.

## Production performance rule

Never download EDGAR, CAT or CDP bulk files on a user's critical Home request. Bulk datasets should be pre-synced or cached. The public analytical page may make small API requests, but failure must degrade to a coverage notice rather than blocking navigation.
