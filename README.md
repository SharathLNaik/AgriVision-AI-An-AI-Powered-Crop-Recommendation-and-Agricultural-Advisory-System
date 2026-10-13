# AgriVision AI: South India Crop & Yield Advisory System
> An Empirical Machine Learning & Agro-Climatic Decision-Support Platform

AgriVision AI is an intelligent agricultural advisory web platform specifically engineered for South Indian agro-climatic zones (Karnataka, Tamil Nadu, Andhra Pradesh, Telangana, and Kerala). It bridges historical regional agricultural statistics, machine learning models, and real-time meteorological forecasts to guide farmers and agronomists through a transparent 10-step planning workflow.

---

## 1. Machine Learning Models & Evaluation Rigor

The system incorporates three supervised machine learning classifiers evaluated with strict separation between training and test sets, audited by [`evaluate_models.py`](./evaluate_models.py):

### Classification Performance (Dataset A — 2,500 Samples, 25 Crops)
* **Random Forest Classifier (100 Trees, Depth 15):**
  - **Stratified 5-Fold Cross-Validation:** **99.16% Mean Accuracy** (Folds: 99.2%, 99.2%, 99.4%, 99.2%, 98.8%)
  - **Holdout Test Set (80/20 Stratified Split, 500 Test Samples):** **98.80% Accuracy**
  - **Weighted Precision:** 98.80% | **Weighted Recall:** 98.80% | **Weighted F1-Score:** 0.9878
  - **Test Misclassifications:** Only 6 out of 500 samples (1.20%), occurring at borderline agro-climatic thresholds (e.g., Ragi vs. Coffee under borderline elevation/rainfall).
* **Support Vector Machine (RBF Kernel, C=10.0):**
  - **Stratified 5-Fold Cross-Validation:** **98.40% Mean Accuracy**
  - **Weighted F1-Score:** 0.9839
* **Deep Neural Network (MLP: 128 -> 64 Hidden Units, Early Stopping):**
  - **Stratified 5-Fold Cross-Validation:** **98.32% Mean Accuracy**
  - **Weighted F1-Score:** 0.9838

### Data Leakage & Feature Importance Audit
* **Duplicate Rows:** 0 (Zero duplicate leakage across feature vectors).
* **Data Scaling:** Scaler is fitted strictly on training folds and applied to test folds.
* **Top Predictive Features (Random Forest Gini Importance):**
  1. Rainfall: 22.13%
  2. Relative Humidity: 21.15%
  3. Potassium (K): 17.57%
  4. Phosphorus (P): 14.68%
  5. Nitrogen (N): 11.50%
  6. Temperature: 7.52%
  7. Soil pH: 5.45%

---

## 2. Dataset Provenance & Separation

To maintain scientific integrity, the project strictly distinguishes between the two datasets:

| Metric | Dataset A: Crop Recommendation | Dataset B: South India APY Statistics |
| :--- | :--- | :--- |
| **Primary File** | `data/Crop_recommendation.csv` | `data/south_india_crop_production.csv` |
| **Size / Records** | 2,500 observations | 64,275 records |
| **Target Variable** | Crop Label (25 crop classes) | Yield (Tonnes per Hectare) / Production |
| **Features** | N, P, K, Temp, Humidity, pH, Rainfall | State, District, Crop Year, Season, Crop, Area |
| **Role in System** | Trains ML Classifiers (RF, SVM, DNN) | District agro-climatic baselines & historical yield distributions |
| **Temporal Coverage** | Controlled ICAR / Agro-Ecological vectors | 1997–2020 (Completed census) + 2021–2025 (KSDA Raitamitra periodic reports) |

---

## 3. Crop Suitability vs. Yield Estimation Architecture

* **Crop Recommendation (Classification):** Evaluates whether the soil biochemical matrix (NPK, pH) and micro-climate (temperature, humidity, rainfall) satisfy the biological requirements of a crop. The percentage shown is the **classifier's predicted probability** (Random Forest tree voting proportion or Softmax output), representing feature affinity rather than a guaranteed agronomic promise.
* **Yield Estimation (Regression & Statistical Benchmarking):** A classification model cannot directly predict harvest tonnage. In AgriVision AI, expected yield is determined using:
  1. **Historical APY Yield Distribution:** Evaluated against 62,372 cleaned historical records (min, median, max tonnes/ha per crop).
  2. **Yield Regressor:** A dedicated Random Forest Regressor trained on historical district area and production records, achieving **$R^2 = 0.9585$** with a Mean Absolute Error (MAE) of **1.08 tonnes/ha**.
  3. **Water Availability Adjustment:** Modulates expected harvest based on irrigation access (High: +15%, Low: -25%).

---

## 4. Regional Soil Baselines & Field Test Overrides

* **District Baselines:** The default soil values (N, P, K, pH) populated upon selecting a district are **Regional Macro-Averages** derived from ICAR and Karnataka State Remote Sensing Applications Centre (KSRSAC) soil health surveys.
* **Laboratory Overrides:** Because individual farmer plots vary in fertility, the application provides an explicit **"Custom Soil Test"** input mode where farmers can enter actual laboratory-tested N, P, K, and pH values.

---

## 5. Live Weather Integration (Open-Meteo NWP)

* **Provider & Licensing:** Powered by the **Open-Meteo High-Resolution NWP API** under Creative Commons Attribution 4.0 International (CC BY 4.0) with free access for non-commercial research and agricultural use.
* **Precipitation Metrics:** Clearly distinguishes between **Precipitation Probability** (percentage likelihood, e.g. 80%) and **Precipitation Quantity** (expected volume in millimeters, e.g. 12.4 mm).
* **Fault-Tolerant Fallback:** In the event of network timeouts or offline execution, the service falls back gracefully to regional climatological averages and timestamps the advisory.

---

## 6. Sourced APMC Market Economics & Agronomic Crop Rotation

* **Market Pricing:** Base commodity prices reflect regional modal APMC Mandi rates (Agmarknet 2024–2025 seasonal benchmarks).
* **Financial Calculations:** Cultivation costs, gross revenue, net profit margin, and return-on-investment (ROI) are calculated and displayed with transparent breakdowns.
* **Scientific Crop Rotation Rationale:**
  - **Kharif (Monsoon):** Primary staple/cereal (e.g. Rice or Maize).
  - **Rabi (Winter):** Legume / Pulse (e.g. Black Gram or Chickpea) harboring symbiotic *Rhizobium* bacteria to fix 30–50 kg of atmospheric nitrogen per hectare into the soil and break monotypic insect pest cycles.
  - **Zaid (Summer):** Drought-hardy green manure / pulse (e.g. Mung Bean) for residue cover and soil organic carbon preservation.

---

## 7. Full-Stack Architecture & Production Roadmap

### Implemented Enterprise Database Architecture (`database.py`)
The system features a **production-ready database layer built with SQLAlchemy 2.0 ORM**, supporting PostgreSQL, MySQL, and SQLite via the configurable `DATABASE_URL` environment variable:

```mermaid
erDiagram
    USERS ||--o{ FARM_PLOTS : owns
    USERS ||--o{ RECOMMENDATION_HISTORY : receives
    FARM_PLOTS ||--o{ SOIL_TEST_REPORTS : tracks
    FARM_PLOTS ||--o{ RECOMMENDATION_HISTORY : generates

    USERS {
        int id PK
        string username UK
        string email UK
        string full_name
        string phone
        string role "farmer | agronomist | admin"
    }

    FARM_PLOTS {
        int id PK
        int user_id FK
        string plot_name
        string state
        string district
        float land_size
        string land_unit
        string water_source
        string soil_type
    }

    SOIL_TEST_REPORTS {
        int id PK
        int plot_id FK
        date test_date
        float nitrogen_n
        float phosphorus_p
        float potassium_k
        float ph
        float organic_carbon
        string lab_name
    }

    RECOMMENDATION_HISTORY {
        int id PK
        int user_id FK
        int plot_id FK
        string district
        string season
        string recommended_crop
        float confidence_score
        float estimated_yield_tons
        float cultivation_cost_inr
        float gross_revenue_inr
        float net_profit_inr
        string weather_temp
        timestamp created_at
    }

    APMC_PRICE_HISTORY {
        int id PK
        string crop
        string state
        string district
        float modal_price_per_ton
        date record_date
    }
```

* **Environment Configuration:**
  - **PostgreSQL:** `export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/agrivision_db"`
  - **MySQL:** `export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/agrivision_db"`
  - **Local Default:** Automatically provisions zero-setup `agrivision_enterprise.db` (SQLite) if no remote connection string is supplied.
* **Production DDL Scripts Provided:**
  - [`schema_postgres.sql`](./schema_postgres.sql): PostgreSQL 13+ DDL script with constraints, UUID support, foreign keys, and indexes.
  - [`schema_mysql.sql`](./schema_mysql.sql): MySQL 8.0+ / MariaDB InnoDB DDL script with `utf8mb4` collation.
* **REST API Endpoints:**
  - `GET /api/database-status`: Live database dialect, engine status, and table record counts.
  - `GET /api/history`: Paginated audit log of saved recommendations.
* **Production Deployment:** Containerize using Docker, serve via Gunicorn WSGI workers behind an Nginx reverse proxy with SSL termination (Let's Encrypt).

---

## 8. Quick Start & Local Execution

### Prerequisites
* Python 3.10+
* Virtual environment (recommended)

### Installation & Launch
```bash
# Clone or navigate to repository
cd "crop prediction"

# Install required dependencies
pip install flask flask-cors scikit-learn pandas numpy requests joblib

# Run model evaluation and verification script
python evaluate_models.py

# Launch application bootstrapper
python run.py
```

The application will launch on:
**`http://127.0.0.1:5000`**

---

## 9. Agronomic Advisory Disclaimer

*AgriVision AI is an educational and decision-support prototype. Field decisions should incorporate local Krishi Vigyan Kendra (KVK) guidelines, physical soil testing, and current mandi spot prices.*
