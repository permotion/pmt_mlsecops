# Ciclo de Vida MLOps y Separación de Responsabilidades

En este proyecto existe una división clara entre el entorno de **investigación** (donde los Data Scientists diseñan features y evalúan algoritmos), el entorno de **producción** (donde MLOps automatiza el pipeline), y el perímetro de **seguridad** (donde Blue Team y Red Team auditan y atacan).

Principio rector: **los modelos en producción no se entrenan a mano** — el notebook experimenta; el DAG entrena y registra.

Ver también: [Visión general del pipeline](arquitectura.md) · [Stack Tecnológico](stack.md) · [Dataset CSIC 2010](dataset.md)

---

## Numeración Steps ↔ Stages

| Step | Stage | Componente |
|------|-------|------------|
| 1 | 0 | `dag_curate_dataset` |
| 2 | 1 | `csic2010_eda.ipynb` |
| 3 | 2 | `dag_preprocess` |
| 4 | 3 | `model_csic_experiments.ipynb` |
| 5 | 4 | `dag_train` |
| 6 | 5 | `dag_promote_model` |
| 7 | 6 | Blue Team + FastAPI |
| 8 | 7 | `dag_deploy_prod` |
| — | 8–10 | API prod · Monitoreo · Red Team |

---

## Diagrama de flujo de datos y promoción

```text
[data/raw/csic2010/csic_database.csv]
      │
      ▼
+------------------------------------+
| ⚙️ Step 1: dag_curate_dataset      | (MLOps)
+------------------------------------+
      │
      ├─► data/curated/csic2010/curation_report.md
      │   (escaneo PII — el CSV raw no se modifica)
      │
      ▼
+------------------------------------+
| 📓 Step 2: csic2010_eda.ipynb      | (Data Science)
+------------------------------------+
      │
      ├─► Hallazgos EDA (notebooks/eda/)
      │
      ▼
+------------------------------------+
| ⚙️ Step 3: dag_preprocess          | (MLOps)
+------------------------------------+
      │
      ├─► data/processed/csic2010/features_v5.parquet (27 features)
      │
      ▼
+------------------------------------+
| 📓 Step 4: model_csic_experiments  | (Data Science)
+------------------------------------+
      │
      ├─► Runs MLflow (skip_promote=True)
      │
      ▼
+------------------------------------+
| ⚙️ Step 5: dag_train               | (MLOps)
+------------------------------------+
      │
      ├─► 4 runs MLflow (LR, RF, XGBoost, LightGBM)
      │
      ▼
+------------------------------------+
| ⚙️ Step 6: dag_promote_model       | (MLOps)
+------------------------------------+
      │
      ├─► MLflow alias @staging + tag candidate
      ├─► Alerta SNS → Blue Team
      │
      ▼
+------------------------------------+
| 🛡️ Step 7: Auditoría Blue Team     |
|   FastAPI http://localhost:5082    |
+------------------------------------+
      │
      ├─► POST /model/approve → tag approved
      │
      ▼
+------------------------------------+
| ⚙️ Step 8: dag_deploy_prod         | (MLOps)
+------------------------------------+
      │
      ├─► MLflow alias @production
      ├─► Alerta SNS → Red Team
      │
      ▼
+------------------------------------+
| 🚀 Stage 8: API en producción      | model_serving @production
+------------------------------------+
      │
      ├─► Stage 9: Monitoreo (FP rate, latencia)
      └─► Stage 10: Red Team CrewAI → reports/ → feedback loop
```

---

## Detalle paso a paso (entradas y salidas)

### Step 1 — Curado de datos (`dag_curate_dataset`)

Escanea el dataset en busca de PII y referencias a organizaciones. **No modifica ni ingesta datos** — solo genera un reporte para revisión humana.

- **Input:** `data/raw/csic2010/csic_database.csv` (descargado previamente, p. ej. desde Kaggle)
- **Output:** `data/curated/csic2010/curation_report.md`
- **Script:** `src/mlsec/data/curate_dataset.py`
- **Detalle:** [Stage 0 — Curado del dataset](stage_0_curation.md)

### Step 2 — Exploración de datos (`notebooks/eda/csic2010_eda.ipynb`)

Primera fase humana. Análisis de distribución de clases, métodos HTTP, patrones de ataque y diseño de features.

- **Input:** `data/raw/csic2010/csic_database.csv`
- **Output:** Decisiones documentadas en el notebook (columnas a descartar, indicadores de texto, estrategia de nulos)

### Step 3 — Preprocess (`dag_preprocess`)

Traduce los hallazgos del EDA en una tubería reproducible de feature engineering.

- **Input:** `data/raw/csic2010/csic_database.csv`
- **Output:** `data/processed/csic2010/features_v5.parquet` (27 features + label)
- **Script:** `src/mlsec/data/preprocess_csic.py`
- **Detalle:** [Stage 2 — Preprocess](stage_2_preprocess.md)

### Step 4 — Prototipado (`notebooks/experiments/model_csic_experiments.ipynb`)

Entrena 4 algoritmos (LogisticRegression, RandomForest, XGBoost, LightGBM) con `skip_promote=True` para experimentar sin afectar staging.

- **Input:** `data/processed/csic2010/features_v5.parquet`
- **Output:** Runs en MLflow experiment `model-csic` (sin promoción a Registry)
- **Run canónico v5:** XGBoost — recall 0.9535, precision 0.7944

### Step 5 — Entrenamiento automatizado (`dag_train`)

Ejecuta la misma lógica de `train_model_a.py` de forma automatizada vía Airflow.

- **Input:** `data/processed/csic2010/features_v5.parquet`
- **Output:** 4 runs registrados en MLflow (uno por algoritmo)
- **Nota:** el tag `candidate` **no** se asigna aquí — lo hace Step 6
- **Detalle:** [Stage 4 — Train Model A](stage_4_train.md)

### Step 6 — Promoción a staging (`dag_promote_model`)

Consulta MLflow, filtra runs con `features_version=v5` y `recall >= 0.95`, selecciona el de **mayor precision** y lo promueve.

- **Input:** Runs MLflow del experiment `model-csic`
- **Output:**
  - Alias `@staging` en Model Registry (`model-csic`)
  - Tag `candidate`
  - Alerta SNS al Blue Team (simulada en logs si no hay ARN configurado)
- **Criterio:** `MIN_RECALL=0.95` → ordenar por precision descendente

### Step 7 — Aprobación Blue Team (FastAPI)

Fase humana de ciberseguridad. El equipo prueba la API que consume el modelo `@staging`.

- **Servicio:** `uvicorn src.mlsec.api.model_serving:app --port 5082` (fuera de Docker)
- **Input:** Endpoints `/predict`, `/predict/http`
- **Output:** `POST /model/approve` → tag `approved`
- **Guía:** [Blue Team Guide](blue_team.md)

### Step 8 — Despliegue a producción (`dag_deploy_prod`)

Verifica que el modelo en `@staging` tenga tag `approved` antes de promover.

- **Input:** Modelo `@staging` con tag `approved`
- **Output:**
  - Alias `@production`
  - Alerta SNS al Red Team (simulada en logs)
- **Guía:** [Manual de Aprobación y Deploy](README_deploy.md)

### Stage 8 — API en producción

FastAPI recarga el modelo con alias `@production` desde MLflow Registry.
Se encuentra protegida detrás de un WAF simulado (Nginx).
- **Endpoint principal:** `POST /predict/http`
- **Output Secundario:** Logs de peticiones estructuradas hacia `data/processed/production_logs.csv`
- **Nota:** en el MVP la API corre simulando un WAF local que enriquece los logs para el monitoreo.

### Stage 9 — Monitoreo (Data Drift)

Blue Team supervisa la degradación matemática del modelo en producción usando **Evidently AI**.
- **Orquestador:** `dag_stage9_monitoring`
- **Input:** `features_v5.parquet` (Reference) vs `production_logs.csv` (Current)
- **Output:** Reporte HTML interactivo (`reports/data_drift_report.html`)
- **Trigger de re-training:** Drift severo en características clave que afecten el Recall o Precision.

### Stage 10 — Red Team (Macro-GAN Semántica)

Agentes LLM autónomos (CrewAI) ejecutan pruebas de evasión operando bajo una arquitectura **Macro-GAN Semántica**.
- **Agente 1 (Payload Hunter):** Hace OSINT para generar el *Latent Space* (JSON de inyecciones base).
- **Agente 2 (Attack Simulator):** Muta iterativamente los payloads que son bloqueados por el WAF hasta lograr un Bypass.
- **Output:** `reports/red_team_report_*.md`
- **Feedback Loop:** Si se encuentran Falsos Negativos, los payloads exitosos se inyectan en el Data Lake y se fuerza un re-entrenamiento (Stage 1).
- **Guía:** [Red Team Guide](red_team.md)

---

## Arquitectura de servicios

| Servicio | Puerto | Entorno | Descripción |
|----------|--------|---------|-------------|
| PostgreSQL | 5432 | Docker | Metastore compartido |
| MLflow | 5081 | Docker | Tracking + Registry + artefactos |
| Airflow | 5080 | Docker | 5 DAGs (ejecución manual) |
| FastAPI | 5082 | Host local | Inferencia + `/model/approve` |

Todos los DAGs usan `schedule=None` — se disparan manualmente desde la UI de Airflow.

---

## Separación investigación vs. producción

| | Investigación (Notebooks) | Producción (DAGs) |
|---|---|---|
| **Steps** | 2, 4 | 1, 3, 5, 6, 8 |
| **Quién** | Data Science | MLOps |
| **Promueve a staging** | No (`skip_promote=True`) | Sí (`dag_promote_model`) |
| **Modifica Registry** | Solo logging de runs | Aliases y tags de gobernanza |
| **Cuándo cambia** | Cada experimento | Cuando MLOps ejecuta el DAG |
