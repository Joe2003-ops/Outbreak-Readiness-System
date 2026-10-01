# Outbreak-Readiness-System
A Machine Learning-driven analytics platform designed to assess county-level outbreak readiness, identify vulnerability gaps, and provide actionable, data-informed intervention strategies for local health authorities.

## Project Overview
During public health emergencies, resource allocation and operational response times vary drastically across administrative regions. Standard outbreak models often focus solely on epidemiological forecasting (predicting case counts) rather than **operational readiness**—measuring whether a county's healthcare system can withstand an surge.

This project addresses this gap by combining healthcare infrastructure, demographic vulnerability, climate factors, and historical surveillance metrics into an **Outbreak Readiness Score**. Beyond risk scoring, the system acts as a prescriptive engine, generating tailored recommendations to help decision-makers prioritize resource distribution before an outbreak escalates

## Key Features
- **Multi-Variable Readiness Scoring:** Evaluates counties across healthcare capacity, population vulnerability, WASH (Water, Sanitation, and Hygiene) access, and environmental risk drivers.
- **Vulnerability Gap Identification:** Highlights specific operational bottlenecks (e.g., ICU bed shortages, oxygen supply gaps, or low vaccination coverage) per county.
- **Prescriptive Recommendation Engine:** Provides rule- and ML-backed priority actions for local public health officers.
- **Interactive Dashboard:** Built with Streamlit to enable intuitive spatial mapping, risk filtering, and comparative county analytics.

## Data Sources
This system aggregates open datasets across four core pillars:

| Domain | Key Variables / Metrics | Source |
| :--- | :--- | :--- |
| **Healthcare Capacity** | Facility distribution, bed capacity, oxygen availability, health personnel density | Kenya Master Health Facility List (KMHFL) / DHIS2 |
| **Surveillance & History** | Historical disease outbreaks (Cholera, Dengue, Mpox), reporting timeliness | OCHA HDX / WHO AFRO Bulletins |
| **Demographics & WASH** | Population density, age distribution, clean water access, poverty index | KNBS Census / WorldPop |
| **Climate & Environment** | Anomaly rainfall indices, temperature trends, flood risk maps | CHIRPS / Copernicus Climate Data|

## System Architecture & Workflow
```
┌────────────────────────────────────────────────────────┐
│                      Data Pipeline                     │
│  [KMHFL] ───► [HDX / WHO] ───► [KNBS] ───► [CHIRPS]    │
└──────────────────────────┬─────────────────────────────┘
│ Data Preprocessing & Merging
▼
┌────────────────────────────────────────────────────────┐
│                   Feature Engineering                  │
│   • Infrastructure Density Index   • Climate Exposure  │
│   • Population Vulnerability Score  • Historical Risk  │
└──────────────────────────┬─────────────────────────────┘
│ Model Training & Evaluation
▼
┌────────────────────────────────────────────────────────┐
│                    ML Model & Logic                    │
│   • Classification / Risk Scoring Engine               │
│   • Prescriptive Action Mapping Engine                 │
└──────────────────────────┬─────────────────────────────┘
│ Output Pipeline
▼
┌────────────────────────────────────────────────────────┐
│                 Streamlit Interactive UI               │
│     Spatial Maps | County Profiles | Priority Actions  │
└────────────────────────────────────────────────────────┘
```
## Tech Stack

- **Language:** Python 3.10+
- **Data Manipulation & Analysis:** `pandas`, `numpy`, `geopandas`
- **Machine Learning & Analytics:** `scikit-learn`, `xgboost`
- **Data Visualization & Geospatial:** `matplotlib`, `seaborn`, `folium`, `plotly`
- **Web Interface:** `streamlit`

---

## Getting Started

### Prerequisites

Ensure you have Python 3.10 or higher installed.
