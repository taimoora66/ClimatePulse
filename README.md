
<img width="1920" height="1080" alt="climatepulse-home" src="https://github.com/user-attachments/assets/5241cb03-021f-46dd-a686-094b85e0e162" />
<img width="1920" height="1080" alt="climate trends" src="https://github.com/user-attachments/assets/7315a3c2-4f5b-43f5-a8b6-874b4f24bf67" />
<img width="1920" height="1080" alt="climatepulse-Country Comparison" src="https://github.com/user-attachments/assets/a6a706cc-85a3-42d1-9e15-09060708b2e8" />






# 🌍 ClimatePulse

### Global Climate Intelligence

**ClimatePulse** is an interactive climate and environmental intelligence platform designed to bring together current environmental conditions, historical climate observations, climate trends, future climate projections, spatial exploration and AI-assisted interpretation in one accessible application.

The project aims to make complex climate information easier to explore and understand across locations, countries and time periods.

### 🚀 Live Application

**Open ClimatePulse:**

https://climatepulse-global.streamlit.app

---

## 🌎 About ClimatePulse

Climate information is often distributed across different datasets, portals, scientific products and modelling systems.

ClimatePulse brings multiple layers of environmental information into a single interactive interface.

The platform allows users to explore:

- current weather and environmental conditions;
- historical climate behaviour;
- long-term climate trends;
- future climate-model projections;
- country and location comparisons;
- global warming patterns;
- climate-health indicators;
- compound environmental risks;
- interactive geographic visualisations;
- climate timelines;
- AI-assisted explanations and interpretation.

ClimatePulse is designed as an **exploratory climate-intelligence platform**, rather than simply a weather dashboard.

---

## ✨ Main Features

### 🌐 Live Earth Intelligence

Explore a global interactive climate globe showing current environmental conditions across countries and locations.

Current visual layers can include indicators such as:

- temperature;
- apparent temperature;
- recent temperature change;
- precipitation;
- wind;
- cloud cover.

The globe can automatically focus on the currently selected location or country.

---

### 📍 Current Location

ClimatePulse can use browser geolocation, with user permission, to identify the user's approximate location.

The detected location can then be used to retrieve relevant:

- live weather;
- local environmental conditions;
- historical climate context;
- climate trends.

Location access occurs only after user interaction with the location control.

---

## 📊 Climate Dashboard

The dashboard provides a more detailed environmental profile for the selected location.

Depending on data availability, this can include:

- temperature;
- precipitation;
- humidity;
- wind;
- apparent temperature;
- air-quality information;
- climatic normals;
- recent environmental conditions;
- historical climate indicators.

---

## 🗺️ Map Explorer

The Map Explorer provides spatial exploration of environmental information.

It is designed to help users investigate climate and environmental patterns geographically rather than only through charts and tables.

---

## 🕰️ Climate Timeline

ClimatePulse provides a long-term climate timeline extending from historical observations toward future climate projections.

The objective is to connect:

```text
Historical climate
        ↓
Observed change
        ↓
Present conditions
        ↓
Future climate projections
```

This allows climate change to be explored as a continuous temporal process rather than as disconnected datasets.

---

## 📈 Climate Trends

ClimatePulse analyses longer-term changes in environmental variables.

Climate trend views may include:

- long-term temperature evolution;
- temperature anomalies;
- warming rates;
- precipitation change;
- climate variability;
- historical records;
- model-based future trajectories.

---

## 🔮 Future Climate Projections

Future climate information is based on climate-model projections where available.

ClimatePulse is designed to support the interpretation of climate scenarios from datasets such as **CMIP6**.

Future climate values should be interpreted as **model projections**, not deterministic weather forecasts.

The platform therefore distinguishes between:

- current weather observations;
- historical climate datasets;
- reanalysis;
- long-term trends;
- future climate projections.

---

## 🌍 Compare Places

Users can compare climate characteristics between different places or countries.

Potential comparison dimensions include:

- historical temperature;
- temperature trends;
- precipitation;
- recent climate conditions;
- projected future change;
- environmental risk indicators.

Where a value represents a geographic proxy rather than a national spatial average, ClimatePulse aims to label this clearly.

---

## 🏆 Global Rankings

Global Rankings provide a comparative view of climate indicators across countries.

Examples may include:

- warming trends;
- current temperature;
- environmental conditions;
- climate-change indicators.

Rankings should be interpreted according to the methodology and spatial scope associated with each variable.

---

## 🛂 Climate Passport

Climate Passport provides a compact environmental and climate profile for a selected place.

The objective is to give users a quick overview of:

- current conditions;
- historical climate;
- long-term change;
- future climate context;
- environmental indicators.

---

## ❤️ Climate & Health Context

ClimatePulse also explores environmental conditions that may have implications for human health.

Examples can include:

- thermal stress;
- high apparent temperature;
- tropical nights;
- heat exposure;
- air pollution;
- compound heat and air-quality conditions.

These indicators are intended for environmental interpretation and **do not provide medical diagnosis or personalised medical advice**.

---

## ⚠️ Compound Climate Risk

Environmental hazards often occur together.

ClimatePulse is designed to explore combinations such as:

- heat × humidity;
- heat × air pollution;
- heat × warm nights;
- heat × drought;
- intense rainfall × antecedent wetness;
- drought × heatwave conditions.

The objective is to avoid reducing complex environmental risks to a single arbitrary score where scientifically meaningful relationships can instead be shown directly.

---

## 🤖 ClimatePulse AI

ClimatePulse includes a persistent AI assistant.

The assistant can help users:

- understand ClimatePulse;
- explain the purpose of individual pages;
- interpret climate indicators;
- understand environmental terminology;
- ask questions about the selected location;
- learn about climate science;
- ask general science, programming, data-analysis and educational questions.

ClimatePulse AI is intended to improve accessibility and interpretation of environmental information.

AI-generated responses should not be treated as substitutes for authoritative scientific, medical, legal, emergency or meteorological information.

---

# 🧠 Data Sources

ClimatePulse integrates or is designed around several established environmental and climate data sources.

## Open-Meteo

Used for selected live meteorological and environmental information.

Typical variables may include:

- temperature;
- precipitation;
- cloud cover;
- wind;
- apparent temperature;
- current conditions.

---

## ERA5

ERA5 is a global atmospheric reanalysis dataset produced by the European Centre for Medium-Range Weather Forecasts.

Within ClimatePulse, ERA5 can support historical climate analysis and contextualisation.

---

## CRU

Climate Research Unit datasets can provide long-term historical climate information.

These datasets are useful for studying longer climatic time periods beyond modern operational weather observations.

---

## CMIP6

CMIP6 is the sixth phase of the Coupled Model Intercomparison Project.

ClimatePulse uses or is designed to use CMIP6 climate-model output for future climate projections and scenario-based analysis.

---

## OpenStreetMap / CARTO / MapTiler

Geospatial basemaps and mapping infrastructure may use services such as:

- OpenStreetMap;
- CARTO;
- MapTiler.

Availability can depend on configuration and API access.

---

# 🗄️ Data Architecture

ClimatePulse uses a combination of:

- external environmental APIs;
- historical climate datasets;
- climate-model data;
- cached data;
- local processing;
- database-backed information.

The broader architecture includes technologies such as:

- Python;
- PostgreSQL;
- Neon;
- Streamlit;
- Plotly.

---

# 🛠️ Technology Stack

## Application

- **Python**
- **Streamlit**

## Data Processing

- pandas
- NumPy
- requests
- scientific Python libraries

## Visualisation

- Plotly
- Streamlit visual components
- geospatial visualisation tools

## Database

- PostgreSQL
- Neon

## Data Sources / Environmental Services

- Open-Meteo
- ERA5
- CRU
- CMIP6
- OpenStreetMap
- CARTO
- MapTiler

## AI

ClimatePulse includes an AI-assistant architecture using an external inference provider where configured.

API keys and credentials are stored through secure environment variables or Streamlit Secrets and are not intended to be committed to the public repository.

---

# 📁 Project Structure

A simplified representation of the project structure is:

```text
ClimatePulse/
│
├── app.py
├── requirements.txt
├── README.md
│
├── assets/
│
├── src/
│   ├── home_page.py
│   ├── live_globe.py
│   ├── location_widget.py
│   ├── ai_assistant.py
│   ├── profile.py
│   ├── ui_v27.py
│   │
│   ├── api/
│   │   ├── country_live_field.py
│   │   ├── global_field.py
│   │   ├── home_environment.py
│   │   └── point_history.py
│   │
│   └── services/
│       └── context_engine.py
│
└── ...
```

The precise structure may evolve as ClimatePulse continues to develop.

---

# ▶️ Running ClimatePulse Locally

## 1. Clone the repository

```bash
git clone https://github.com/taimoora66/ClimatePulse.git
```

Move into the project directory:

```bash
cd ClimatePulse
```

---

## 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure optional secrets

Some features may require external API credentials.

Do **not** commit secrets to GitHub.

For local development, configure environment variables or an appropriate local secrets file.

For example:

```text
HF_TOKEN=your_token
HF_MODEL=your_model
```

Other map or database services may require their own credentials.

---

## 5. Start ClimatePulse

```bash
streamlit run app.py
```

The local application will normally become available at:

```text
http://localhost:8501
```

---

# ☁️ Deployment

ClimatePulse is deployed using **Streamlit Community Cloud**.

Live application:

https://climatepulse-global.streamlit.app

Streamlit Community Cloud connects directly with GitHub repositories and can redeploy the application when changes are pushed to the configured branch. Public Streamlit applications can then be shared through their `streamlit.app` URL.

---

# 🔐 Security & Secrets

Private credentials should never be stored directly in the public source code.

Examples include:

- API keys;
- database credentials;
- Hugging Face tokens;
- map-service tokens;
- private connection strings.

These should be stored using:

- environment variables;
- `.env` files excluded by `.gitignore`;
- Streamlit Community Cloud Secrets.

---

# 🔬 Scientific Interpretation

ClimatePulse combines datasets that represent different components of the climate system.

These should not be interpreted as interchangeable.

### Weather

Weather describes short-term atmospheric conditions.

Examples:

- today's temperature;
- current rainfall;
- current wind speed.

### Climate

Climate describes longer-term statistical characteristics of atmospheric conditions.

### Reanalysis

Reanalysis combines historical observations with numerical modelling to reconstruct past atmospheric conditions.

### Climate Projections

Climate-model projections represent possible future climate conditions under particular assumptions and scenarios.

They are not weather forecasts.

ClimatePulse aims to maintain this distinction throughout the application.

---
<img width="1920" height="1080" alt="climate projections" src="https://github.com/user-attachments/assets/7c4e771a-c98c-4ac6-ae83-8a2361574a4f" />
<img width="1920" height="1080" alt="climatepulse-globe" src="https://github.com/user-attachments/assets/9d3a7685-e5c1-4bc1-806d-945de62b0ca5" />
# ⚠️ Limitations

ClimatePulse is an evolving research and educational application.

Important limitations include:

- external APIs may occasionally be unavailable;
- geographic coverage differs between datasets;
- time coverage differs between datasets;
- spatial resolution differs between datasets;
- model projections contain uncertainty;
- representative geographic points should not automatically be interpreted as national spatial averages;
- historical datasets and live weather APIs may use different methodologies;
- environmental indicators do not constitute emergency warnings;
- AI responses may contain errors and should be independently verified for high-stakes decisions.

---

# 🚨 Disclaimer

ClimatePulse is provided for:

- climate-data exploration;
- education;
- research;
- environmental communication;
- analytical experimentation.

It is **not** an official meteorological warning system.

For severe weather warnings, emergencies or operational decisions, users should consult the relevant national meteorological and civil-protection authorities.

Climate-health information is informational only and should not replace professional medical guidance.

---

# 🎓 Project Creator

## Taimoor Ahmad

MSc student in:

**Environmental Change & Global Sustainability**

**University of Milan**

ClimatePulse was developed as an independent environmental and climate-data project combining interests in:

- climate change;
- environmental science;
- climate modelling;
- data analysis;
- geospatial visualisation;
- scientific communication;
- interactive environmental intelligence.

---

# 🌱 Project Vision

The long-term goal of ClimatePulse is to develop an accessible interface connecting:

```text
Weather
   +
Historical Climate
   +
Climate Trends
   +
Future Projections
   +
Environmental Risk
   +
Geospatial Intelligence
   +
AI-assisted Interpretation
```

into one coherent climate-intelligence environment.

The broader objective is to help transform complex environmental datasets into information that is easier to explore, compare and understand.

---

# 🚧 Development Status

ClimatePulse is under active development.

Current development areas include:

- improved spatial climate analysis;
- stronger climate-model integration;
- better uncertainty communication;
- improved country-level climate indicators;
- expanded climate-health analysis;
- compound climate-risk interpretation;
- enhanced AI-assisted environmental explanation;
- improved user interaction and visualisation.

---

# 🤝 Contributions

Suggestions, scientific feedback and technical improvements are welcome.

If you identify:

- a methodological issue;
- a data-quality problem;
- a software bug;
- a visualisation issue;
- a useful environmental dataset;

please open an issue in this repository.

---

# 📚 Citation

If ClimatePulse is used in academic or research work, please cite the repository and specify the date/version accessed.

A formal citation format and DOI may be added in a future release.

Suggested temporary citation:

```text
Ahmad, T. ClimatePulse: Global Climate Intelligence.
GitHub repository and interactive Streamlit application.
https://github.com/taimoora66/ClimatePulse
```

---

# 🔗 Links

### Live application

https://climatepulse-global.streamlit.app

### Source code

https://github.com/taimoora66/ClimatePulse

---

## ⭐ Support the Project

If you find ClimatePulse useful or interesting, consider starring the repository.

A GitHub star helps make the project easier for others to discover.
<img width="1920" height="1080" alt="climate passport" src="https://github.com/user-attachments/assets/28516f00-25a0-42bf-814b-956b1e4ef1e6" />

---

**ClimatePulse — Global Climate Intelligence**
