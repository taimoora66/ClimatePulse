# ORBIDENSE

### Earth Intelligence for Climate and Environmental Exploration

ORBIDENSE is an independent environmental and climate intelligence platform that brings together environmental conditions, historical climate information, climate projections, population exposure, greenhouse-gas emissions, climate-action information, and geographic exploration within a single interactive application.
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/b57346ff-77a2-4a80-9e82-b03908798ad6" />

The project combines environmental data engineering, geospatial analysis, climate-data processing, database-backed services, interactive visualization, and cloud deployment.
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/293cc752-75b9-4a54-965e-20931f4552fb" />

**Live platform:** https://orbidense.com

---

## Overview

Environmental and climate information is distributed across many datasets, APIs, institutional portals, geographic systems, and modelling frameworks.

ORBIDENSE provides a common interface for exploring selected environmental and climate information while retaining distinctions between different forms of evidence.

The current platform includes:

- geographic and location-based environmental exploration;
- live environmental conditions;
- historical climate context;
- CMIP6-based climate projections;
- population exposure;
- greenhouse-gas emissions;
- national climate targets and action information;
- country-level climate intelligence;
- comparative and global environmental views;
- source and methodology information.

ORBIDENSE separates current environmental observations, historical climate information, future climate-model projections, emissions data, and climate-policy information rather than presenting them as equivalent measures.

---

## Platform

The application is organized around several connected areas:

- **Home**
- **Climate Outlook**
- **Population Exposure**
- **Climate Action**
- **Compare**
- **Global**
- **About**

Each section uses a shared geographic and environmental context while addressing a different part of the climate-information system.

---

## Home and Earth Exploration

The Home interface provides the main geographic entry point into ORBIDENSE.

Users can search for locations and connect geographic information with environmental conditions through the interactive Earth interface.

The implemented workflow includes:

```text
Location Search
      ↓
Geocoding
      ↓
Geographic Resolution
      ↓
Environmental Data Retrieval
      ↓
Processing
      ↓
Interactive Visualization
```

The application contains dedicated modules for geographic search, location handling, environmental retrieval, and interactive Earth visualization.

---

## Environmental Conditions

ORBIDENSE integrates selected environmental information into a location-oriented interface.

Depending on source and geographic availability, the platform processes information related to:

- temperature;
- precipitation;
- atmospheric conditions;
- weather;
- air-quality context;
- geographic characteristics;
- environmental indicators.

Source-specific API responses are processed before presentation so that external service structures do not directly determine the application interface.

---

## Climate Outlook

Climate Outlook connects historical climate information with future climate projections.

The implemented climate-intelligence system includes:

- historical temperature information;
- historical precipitation information;
- climate anomalies;
- future climate periods;
- CMIP6 scenarios;
- projected temperature change;
- projected precipitation change;
- hot-day indicators;
- climate-model ensemble information where available.

Climate projections are presented as model-derived information under defined scenarios and periods rather than as deterministic weather forecasts.

---

## Climate Projection Data

ORBIDENSE contains a processed country-level climate projection pipeline based on World Bank Climate Change Knowledge Portal data.

The climate-intelligence data layer contains processed projection datasets including:

```text
cckp_country_projections.parquet
cckp_country_projections_smoke.csv
cckp_country_projections_smoke.parquet
cckp_country_projections_smoke_v2.csv
cckp_country_projections_smoke_v2.parquet
cckp_pr_repair.csv
cckp_pr_repair.parquet
```

Projection information is structured by climate variable, scenario, future period, statistic, and geography.

Where ensemble percentiles are available, they are interpreted as climate-model ensemble spread rather than probabilities of future weather events.

---

## Country Climate Intelligence

ORBIDENSE combines several types of country-level information within a common climate-intelligence framework.

Depending on source coverage, country views can incorporate:

- historical climate;
- climate projections;
- population information;
- greenhouse-gas emissions;
- climate targets;
- climate-action information;
- geographic context.

This allows physical climate information to be examined alongside emissions and policy-related information without collapsing those dimensions into a single indicator.

---

## Population Exposure

The platform includes a dedicated population-exposure layer.

The repository contains processed exposure information including:

```text
population_exposure.parquet
```

and corresponding application logic for presenting population information alongside environmental and climate context.

The architecture keeps environmental hazard information and population exposure conceptually separate.

This distinction provides a foundation for analysing how environmental conditions intersect with human populations without treating population alone as a complete measure of vulnerability or risk.

---

## Climate Action

Climate Action connects physical climate information with emissions, targets, and transition-related information.

Implemented country-level integrations include:

- structured Nationally Determined Contribution information;
- official NDC provenance;
- greenhouse-gas emissions;
- Climate Action Tracker ratings for covered countries;
- national and sector emissions information where available.

The platform maintains distinctions between:

```text
Physical Climate
       ≠
Greenhouse-Gas Emissions
       ≠
Climate Targets
       ≠
Policy Implementation
       ≠
Independent Climate Assessment
```

These components are therefore presented as related but distinct dimensions of climate information.
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/b6e59ae4-50ac-4ec0-9b52-6bebae6a5fe4" />

---

## National Climate Targets

Structured national climate-target information is incorporated through Climate Watch / World Resources Institute data where available.

Official NDC submission provenance is associated with the UNFCCC NDC Registry.

Processed target datasets include:

```text
climatewatch_targets.csv
climatewatch_targets.parquet
```

Where structured information is unavailable for a geography, the system retains an unavailable or missing state rather than substituting information from another geography.

---

## Climate Action Tracker

ORBIDENSE incorporates a curated Climate Action Tracker rating snapshot for countries covered by CAT.

The climate-intelligence data directory contains:

```text
cat_ratings_2026_07.csv
```

Coverage follows the countries assessed by Climate Action Tracker and is not treated as universal country coverage.

---

## Emissions Intelligence

Country and sector greenhouse-gas information is incorporated through processed emissions datasets.

The current data layer includes:

```text
edgar_country_emissions.parquet
edgar_sector_emissions.parquet
```

EDGAR / Joint Research Centre data provides country- and sector-level emissions structure used by the climate-intelligence system.

Large emissions datasets are processed or synchronized outside the normal interactive page request rather than downloaded whenever a user opens a page.

---

## Compare

ORBIDENSE provides comparative environmental and climate views for examining geographic differences.

Comparison tools place individual indicators in a broader context rather than presenting each location independently.

Comparisons remain dependent on the geographic resolution, temporal period, units, and coverage of the underlying datasets.

---

## Global Exploration

The Global section provides broader geographic exploration of available environmental and climate indicators.

It supports examination of patterns across multiple locations while preserving the geographic meaning of the underlying data.

Country-level values, city-level information, and coordinate-based measurements are not automatically treated as equivalent geographic observations.

---

## City Climate Intelligence

The repository contains a framework for city-level climate intelligence using available point-based climate and city-reporting datasets.

### Physical Climate

Open-Meteo Climate / CMIP6 HighResMIP information is used for selected place-level climate projections.

Coordinate-based climate information is treated as a point estimate rather than labelled as a spatial average across an administrative city boundary.

### CDP City Information

The project contains preprocessing and integration logic for public CDP city data.

Depending on reporting coverage, available information may include:

- city emissions;
- climate targets;
- reported target progress;
- reported climate risks;
- climate-policy information.

CDP information is used only for cities represented in the underlying dataset.

Missing reporting remains missing rather than being inferred from nearby or similar cities.

---

## Sector Transition Intelligence

ORBIDENSE also contains a framework for examining sector-level emissions and transition context.

Implemented components include:

- EDGAR/JRC sector-emissions structures;
- Climate Action Tracker sector benchmark adapters;
- benchmark synchronization tooling;
- sector-gap calculations where compared values use compatible definitions and units.

Comparisons are not calculated when current values and benchmark values are not meaningfully comparable.

---

# Data Architecture

A substantial part of ORBIDENSE concerns the integration of environmental datasets that differ in structure and methodology.

Sources can vary by:

- geographic identifiers;
- coordinate systems;
- spatial resolution;
- temporal resolution;
- units;
- update frequency;
- variable definitions;
- missing-data conventions;
- API structure;
- institutional methodology.

The application therefore separates acquisition from processing and presentation.

```text
External Data Sources
         ↓
Data Acquisition
         ↓
Validation
         ↓
Normalization
         ↓
Transformation
         ↓
Processed Data / Database
         ↓
Service Layer
         ↓
Application Logic
         ↓
Visualization
```

This architecture allows individual data providers to be maintained separately from the user interface.

---

## Database Layer

ORBIDENSE uses persistent database infrastructure alongside processed local datasets and external APIs.

The database architecture supports storage and retrieval of information used by the application.

```text
External Source
      ↓
Acquisition
      ↓
Processing
      ↓
Persistent Storage
      ↓
Application Query
      ↓
Environmental Intelligence
      ↓
Visualization
```

This separates external data acquisition from normal application interaction and provides infrastructure for historical and analytical workflows.

---

## Geographic Search

Geographic search connects user location queries with environmental information.

The workflow includes:

```text
User Query
    ↓
Geocoding
    ↓
Location Resolution
    ↓
Coordinates / Geographic Context
    ↓
Environmental Services
    ↓
ORBIDENSE
```

Dedicated geographic modules handle location search and normalization before environmental information is retrieved.

---

# Data Sources

ORBIDENSE integrates or contains adapters for several established environmental and climate information providers.

## World Bank Climate Change Knowledge Portal

Used within the climate-intelligence system for historical national climate information and processed CMIP6 country projections.

## CRU

Used within the historical climate-data workflow where applicable.

## Open-Meteo

Used for selected environmental and climate services, including location-oriented environmental information and selected CMIP6/HighResMIP climate data.

## Climate Watch / World Resources Institute

Used for structured national climate-target information and related climate-policy data.

## UNFCCC NDC Registry

Used as an official provenance reference for Nationally Determined Contribution submissions.

## Climate Action Tracker

Used for country rating snapshots and selected sector-transition benchmark information.

Coverage is limited to the countries and indicators represented by Climate Action Tracker.

## EDGAR / Joint Research Centre

Used for processed country- and sector-level greenhouse-gas emissions information.

## CDP Open Data

Used within the city climate-intelligence preprocessing pipeline for cities represented in the public dataset.

CDP city information is treated as reported city information.

## Geographic and Mapping Services

The project includes geographic and mapping components associated with services such as:

- OpenStreetMap;
- CARTO;
- MapTiler;
- geocoding services.

Availability of individual layers depends on the relevant service and configuration.

---

# Scientific Interpretation

ORBIDENSE includes several explicit interpretation rules for environmental and climate information.

## Weather and Climate

Individual weather conditions are not treated as evidence of long-term climate change.

Historical climate information and current environmental conditions are presented as different forms of information.

## Observations and Projections

Observed or historical information is kept conceptually separate from future climate-model projections.

Future model output is associated with its scenario and projection period.

## Point and Area Measurements

A climate value associated with one coordinate is not automatically presented as an administrative-area average.

## Ensemble Information

Climate-model ensemble spread is not described as a probability forecast for future weather.

## Missing Data

Missing provider coverage remains unavailable rather than being replaced with values from another geography.

## Geographic Coverage

Information from sources with limited geographic coverage is shown only where corresponding source data exists.

## Climate Dimensions

Physical climate, emissions, exposure, targets, policy information, and external ratings remain separate analytical dimensions.

---

# Application Architecture

ORBIDENSE uses a modular Python application structure.

At a simplified level:

```text
                         ORBIDENSE
                             │
                      Application Router
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
        Home           Climate Views      Global / Compare
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                       Service Layer
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
        APIs            Local Data          Database
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                     External Sources
```

Application routing, environmental data services, climate processing, geographic functionality, and visualization are maintained in separate modules.

---

# Repository Structure

A simplified view of the current repository:

```text
ORBIDENSE-AI/
│
├── app.py
│
├── src/
│   │
│   ├── api/
│   ├── climate_intelligence/
│   ├── queries/
│   ├── services/
│   │
│   ├── climate_projection_store.py
│   ├── exposure_action_pages.py
│   ├── home_page.py
│   ├── home_v2.py
│   ├── intelligence_pages.py
│   ├── live_globe.py
│   ├── location_widget.py
│   ├── map_explorer.py
│   ├── population_exposure_v7.py
│   ├── orbidense_router.py
│   ├── orbidense_shell.py
│   ├── orbidense_theme.py
│   ├── db.py
│   └── ...
│
├── data/
│   └── climate_intelligence/
│
├── database/
├── scripts/
├── tests/
│
├── seo/
│   ├── about.html
│   ├── research.html
│   ├── methodology.html
│   ├── data.html
│   ├── robots.txt
│   ├── sitemap.xml
│   └── site.css
│
├── Dockerfile
├── nginx.conf
├── start.sh
├── requirements.txt
└── README.md
```

---

# Technology Stack

### Application

- Python
- Streamlit

### Data Processing

- pandas
- NumPy
- Python-based data transformation
- API-based acquisition workflows

### Visualization

- Plotly
- Streamlit visualization components
- geographic and environmental visualization

### Database

- PostgreSQL
- database-backed application services

### Data Formats

- Parquet
- CSV
- structured API responses
- processed environmental datasets

### Infrastructure

- Docker
- Google Cloud Build
- Google Cloud Run
- Nginx
- custom domain deployment

### Development

- Git
- GitHub
- Python virtual environments
- modular Python architecture
- validation and backtesting scripts

---

# Production Architecture

The public ORBIDENSE application is containerized and deployed through Google Cloud infrastructure.

```text
Source Repository
       ↓
Google Cloud Build
       ↓
Container Image
       ↓
Cloud Run Revision
       ↓
Nginx Gateway
       ↓
Streamlit Application
       ↓
orbidense.com
```

The Streamlit application runs internally behind the gateway.

During container startup, the application health endpoint is checked before the gateway begins normal request handling.

---

## Revision-Based Deployment

Cloud Run revisions are used to test application releases independently before production traffic is moved.

The deployment workflow follows:

```text
Production Revision
        │
        ├──────── continues serving traffic
        │
        ▼
New Revision
        │
        ▼
Zero-Traffic Deployment
        │
        ▼
Direct Revision Testing
        │
        ▼
Health and Application Checks
        │
        ▼
Production Traffic Migration
```

This provides a controlled workflow for validating changes before they become the active production revision.

---

# Search and Crawlable Information Layer

ORBIDENSE includes a static information layer alongside the interactive application.

The repository contains:

```text
seo/
├── about.html
├── research.html
├── methodology.html
├── data.html
├── robots.txt
├── sitemap.xml
└── site.css
```

Public information routes include:

```text
/about
/research
/methodology
/data
```

The deployment also serves:

```text
/robots.txt
/sitemap.xml
```

The homepage HTML contains ORBIDENSE-specific title and descriptive fallback content independently of the fully rendered Streamlit interface.

The production homepage title is:

```html
<title>ORBIDENSE | Climate Risk, Earth Intelligence & Environmental Data</title>
```

---

# Validation and Backtesting

The repository contains testing and validation workflows for application and climate-intelligence components.

Basic source validation can be performed with:

```bash
python -m py_compile app.py
python -m compileall -q src scripts tests
```

Climate-intelligence validation includes:

```bash
python scripts/backtest_climate_intelligence.py
```

The validation workflow distinguishes between deterministic calculation checks and external data/integration availability.

A failed external provider request is treated as an integration or coverage issue rather than replaced with an invented result.

Recorded climate-intelligence validation output is also maintained in:

```text
backtest_report.json
```

---

# Tests

The repository contains a dedicated test suite covering parts of the application and data system.

Testing has been used for components including:

- geographic search;
- geocoding;
- city handling;
- environmental retrieval;
- historical information;
- database interaction;
- climate-intelligence functionality.

External-source and dataset validation is additionally handled through dedicated scripts where appropriate.

---

# Data Refresh and Caching

Environmental datasets have different publication and update schedules.

ORBIDENSE therefore uses source-specific data handling rather than applying one refresh interval to every dataset.

The climate-intelligence architecture distinguishes between:

- live environmental information;
- historical climate datasets;
- climate projections;
- NDC information;
- CAT assessments;
- EDGAR emissions releases;
- CDP city reporting.

Large or slowly changing datasets are processed or synchronized outside normal interactive requests where appropriate.

---

# Product Monitoring

ORBIDENSE includes an internal application-usage monitoring layer used during development to understand application interaction and technical usage patterns.

This functionality supports evaluation of platform behaviour and interface development but is separate from the environmental and climate-intelligence methodology.

---

# Local Development

## Clone

```bash
git clone https://github.com/taimoora66/ORBIDENSE-AI.git
cd ORBIDENSE-AI
```

## Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python -m streamlit run app.py
```

The local application normally becomes available at:

```text
http://localhost:8501
```

---

# Development Validation

Before committing application changes:

```bash
python -m compileall -q app.py src
```

Git whitespace and formatting problems can be checked with:

```bash
git diff --check
```

Climate-intelligence validation can additionally be run with:

```bash
python scripts/backtest_climate_intelligence.py
```

---

# Data Availability and Limitations

Environmental datasets have different geographic, temporal, and methodological coverage.

Current limitations include:

- some providers do not cover every country;
- CDP information is limited to cities represented in its public dataset;
- CAT assessments are limited to countries and sectors covered by CAT;
- climate datasets differ in spatial and temporal resolution;
- point climate projections are not equivalent to administrative-area averages;
- climate-model projections depend on scenario and model assumptions;
- environmental APIs may occasionally be unavailable;
- emissions, exposure, physical climate, climate targets, and policy indicators represent different dimensions of climate information.

These distinctions are retained in the application and supporting methodology.

---

# Documentation

Additional implementation and data information is maintained in repository documentation including:

```text
CLIMATE_INTELLIGENCE_V4_NOTES.md
CLIMATE_INTELLIGENCE_DATA_AVAILABILITY.md
```

These documents describe climate-intelligence integrations, data availability, source coverage, synchronization workflows, interpretation rules, and validation behaviour.

---

# Project Development

ORBIDENSE has developed through multiple iterations covering:

- environmental data acquisition;
- geographic search and location resolution;
- database integration;
- interactive Earth exploration;
- historical climate information;
- climate projections;
- population exposure;
- country climate intelligence;
- greenhouse-gas emissions;
- climate-action information;
- comparative environmental views;
- city climate-data integration;
- sector-transition data;
- data synchronization;
- validation and backtesting;
- application routing and interface development;
- containerized deployment;
- Cloud Run revision testing;
- production gateway configuration;
- crawlable information pages and sitemap infrastructure.

The repository retains parts of earlier development iterations where they remain referenced or useful during continued consolidation.

---

# Methodological Scope

ORBIDENSE is an environmental information and analytical software project.

Outputs depend on the characteristics and limitations of the underlying datasets.

The application does not treat:

- correlation as causation;
- model projections as observations;
- current weather as long-term climate evidence;
- point measurements as area averages;
- missing values as zero;
- model ensemble spread as forecast probability;
- self-reported climate information as independently verified measurement.

Interpretation should therefore consider the original data source, methodology, geographic resolution, temporal period, and uncertainty associated with each indicator.

---

# Current Status

ORBIDENSE is under active development.

The current deployed platform combines the environmental-data, climate-intelligence, geographic, database, visualization, and deployment components described above.

Further work continues through additional data validation, research development, interface refinement, and expansion of environmental analysis.

---

## Author

**Taimoor Ahmad**  
Environmental Change and Global Sustainability  
University of Milan

---

## Links

**Live Platform**  
https://orbidense.com

**GitHub Repository**  
https://github.com/taimoora66/ORBIDENSE-AI
