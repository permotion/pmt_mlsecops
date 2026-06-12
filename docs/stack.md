# Stack Tecnológico

---

## Visión general

```
Curación → Preprocess → Train → Registry → Staging → Blue Team → Production → Red Team
     │           │          │         │          │          │            │          │
  Airflow    Airflow    Airflow   MLflow    MLflow    FastAPI     Airflow    CrewAI
```

**Stack principal:** Python, scikit-learn, LightGBM, XGBoost, Airflow, MLflow, PostgreSQL, FastAPI, CrewAI.

---

## Herramientas principales

| Herramienta | Rol |
|-------------|-----|
| **Python 3.11+** | Lenguaje principal (3.11 en imágenes Docker; compatible con 3.11–3.13 en local) |
| **scikit-learn** | Preprocess, métricas, split train/val/test, StandardScaler |
| **XGBoost** | Modelo seleccionado en el run canónico v5 (mayor precision con recall ≥ 0.95) |
| **LightGBM** | Candidato evaluado en cada run de training (segundo en precision en v5) |
| **MLflow 3.x** | Experiment tracking y Model Registry (aliases `@staging` / `@production`) |
| **Apache Airflow 2.10** | Orquestación de DAGs del pipeline |
| **FastAPI + uvicorn** | API de inferencia y aprobación Blue Team |
| **PostgreSQL 15** | Metastore compartido (Airflow + MLflow) |
| **CrewAI + LiteLLM** | Red Team automatizado (PayloadHunter + AttackSimulator) |
| **MkDocs + Material** | Documentación del proyecto |
| **Docker Compose** | Infra local (Postgres, MLflow, Airflow) |

---

## Python

Lenguaje base para ML, API, scripts de preprocess/train y agentes Red Team.

### Dependencias ML (`requirements-ml.txt`)

Usadas en la imagen Airflow y en entrenamiento local:

```
pandas>=2.2
numpy>=1.26
scikit-learn>=1.4
lightgbm>=4.0
xgboost>=2.0
mlflow>=3.0,<4.0
psycopg2-binary>=2.9
python-dotenv>=1.0
pyarrow>=15.0
requests>=2.31
hyperopt>=0.2
joblib>=1.3
crewai
crewai-tools
langchain-openai
litellm
```

### Dependencias API (`src/mlsec/api/requirements.txt`)

Usadas para levantar `model_serving.py` en local:

```
fastapi>=0.100
uvicorn[standard]>=0.23
mlflow>=3.0
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
xgboost>=2.0
pydantic>=2.0
```

### Dependencias documentación (`requirements-docs.txt`)

```
mkdocs>=1.5.0
mkdocs-material>=9.0.0
mkdocstrings[python]>=0.20.0
```

---

## Modelos ML

En cada run de `dag_train`, se entrenan **4 algoritmos** (LogisticRegression, RandomForest, XGBoost, LightGBM) sobre `features_v5.parquet` (27 features).

**Criterio de selección:** entre modelos con recall ≥ 0.95, gana el de **mayor precision** (`train_model_a.py` y `dag_promote_model.py`).

**Run canónico (features v5):** **XGBoost** — recall 0.9535, precision 0.7944, threshold 0.2502, FP 928.

| Algoritmo | Uso de desbalance | Run v5 (test) |
|-----------|-------------------|---------------|
| LogisticRegression | `class_weight='balanced'` | recall 0.9649, precision 0.4808 |
| RandomForest | `class_weight='balanced'` | recall 0.9492, precision 0.7776 |
| **XGBoost** | `scale_pos_weight` | recall **0.9535**, precision **0.7944** ✅ |
| LightGBM | `scale_pos_weight` | recall 0.9553, precision 0.7917 |

Ver resultados completos en [Stage 3 — Resultados](results/stage_3_results.md).

---

## MLflow 3.x

- **Tracking**: runs, métricas (recall, precision, ROC-AUC, threshold), parámetros y artefactos.
- **Model Registry**: modelo registrado como `model-csic`.
- **Aliases** (reemplazan stages deprecated):
  - `@staging` — candidato para revisión del Blue Team
  - `@production` — modelo desplegado tras aprobación
- **Tags de gobernanza**: `deployment_stage` (`candidate` → `approved` → `production`).

**UI:** http://localhost:5081

---

## Apache Airflow

Orquestación manual de los DAGs del pipeline (`schedule=None` en todos).

### DAGs

| DAG | Stage | Función |
|-----|-------|---------|
| `dag_curate_dataset` | 0 | Escaneo PII y reporte de curación |
| `dag_preprocess` | 2 | Genera `features_v5.parquet` |
| `dag_train` | 4 | Entrena 4 modelos y registra en MLflow |
| `dag_promote_model` | 5 | Asigna alias `@staging` al mejor candidato |
| `dag_deploy_prod` | 7 | Valida tag `approved` y promueve a `@production` |

### Flujo simplificado

```
dag_curate_dataset → dag_preprocess → dag_train → dag_promote_model
                                                          │
                                                    [Blue Team]
                                                          │
                                                   dag_deploy_prod
```

### Configuración

- **Executor:** LocalExecutor
- **Webserver:** puerto **5080** (mapeado desde 8080 interno)
- **Scheduler:** corre continuamente
- **DAGs folder:** `/opt/airflow/dags` (montado desde `dags/`)
- **Código Python:** `/opt/airflow/src` (montado desde `src/`)

**UI:** http://localhost:5080 (admin / admin)

---

## FastAPI

API de inferencia que carga el modelo desde MLflow Registry (alias `@staging` por defecto).

**No está incluida en Docker Compose** — se levanta en el host:

```bash
pip install -r src/mlsec/api/requirements.txt
export MLFLOW_TRACKING_URI=http://localhost:5081
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check + modelo cargado |
| GET | `/model/info` | Versión, métricas, threshold |
| POST | `/predict` | Predicción con 27 features en JSON |
| POST | `/predict/http` | Predicción desde request HTTP crudo |
| POST | `/model/approve` | Firma Blue Team (`deployment_stage=approved`) |

**URL:** http://localhost:5082

---

## Docker Compose — Infraestructura local

Servicios definidos en `docker/docker-compose.yml`:

| Servicio | Base | Puerto | Descripción |
|----------|------|--------|-------------|
| **postgres** | postgres:15 | 5432 | Metastore compartido (Airflow + MLflow) |
| **mlflow** | python:3.11-slim (custom) | 5081 | MLflow tracking server + artefactos |
| **airflow-init** | apache/airflow:2.10.4 (custom) | — | Migración DB + usuario admin (one-shot) |
| **airflow-webserver** | apache/airflow:2.10.4 (custom) | 5080 | Airflow UI |
| **airflow-scheduler** | apache/airflow:2.10.4 (custom) | — | Ejecutor de DAGs |

La imagen Airflow instala `requirements-ml.txt` (incluye LightGBM, XGBoost, MLflow, CrewAI).

### Quick start

```bash
cd docker
cp .env.example .env
docker compose up -d
docker compose ps
```

### URLs de acceso

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| MLflow | http://localhost:5081 | — |
| Airflow | http://localhost:5080 | admin / admin |
| PostgreSQL | localhost:5432 | airflow / airflow |

---

## PostgreSQL

Metastore compartido entre Airflow y MLflow (bases `airflow` y `mlflow` creadas en `docker/init-dbs.sql`).

- **Airflow:** metadata de DAGs, task runs, conexiones
- **MLflow:** experiments, metrics, model registry

---

## CrewAI — Red Team

Dos agentes orquestados secuencialmente (`src/mlsec/red_team/red_team_crew.py`):

1. **PayloadHunter** — extrae payloads de PayloadsAllTheThings (SQLi, XSS, Path Traversal)
2. **AttackSimulator** — dispara payloads contra `http://localhost:5082/predict/http` y genera reporte Markdown en `reports/`

**LLM:** LiteLLM apuntando a API compatible Anthropic (configurable vía `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`).

**Ejecución** (requiere API levantada y token configurado):

```bash
export ANTHROPIC_AUTH_TOKEN=<token>
python -m src.mlsec.red_team.red_team_crew
```

Ver guía completa en [Red Team Guide](red_team.md).

---

## MkDocs

Documentación del proyecto con tema Material. Publicada en GitHub Pages vía GitHub Actions.

```bash
pip install -r requirements-docs.txt
mkdocs serve   # → http://localhost:8000
```

**Sitio publicado:** https://permotion.github.io/PMT_MLSecOps
