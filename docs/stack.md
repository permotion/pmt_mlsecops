# Stack Tecnológico

---

## Visión general

```
Development → Training → Deployment → Monitoring
```

Stack: Python, LightGBM, Airflow, MLflow, FastAPI

---

## Herramientas principales

| Herramienta | Rol |
|-------------|-----|
| **Python 3.11** | Lenguaje principal |
| **LightGBM** | Gradient boosting para clasificación binaria |
| **MLflow 3.x** | Experiment tracking y Model Registry |
| **Apache Airflow** | Orquestación del pipeline de entrenamiento |
| **FastAPI** | API de inferencia |
| **PostgreSQL** | Metastore compartido |
| **CrewAI** | Red Team Agent autónomo |
| **MkDocs + Material** | Documentación navegable |

---

## Python 3.11

Lenguaje principal para ML, API, scripts y pipelines.

Dependencias principales:
```
pandas>=2.2
numpy>=1.26
scikit-learn>=1.4
lightgbm>=4.0
mlflow>=3.0,<4.0
psycopg2-binary>=2.9
python-dotenv>=1.0
pyarrow>=15.0
requests>=2.31
hyperopt>=0.2
joblib>=1.3
```

---

## LightGBM

Gradient boosting rápido y eficiente. Maneja datos desbalanceados con `scale_pos_weight`.

---

## MLflow 3.x

Experiment tracking + Model Registry. Versiones y aliases (staging/production/archived) en vez de stages deprecated.

---

## Apache Airflow

Orquestación de pipelines con DAGs: `verify_data → preprocess → train → register → evaluate`

Configuración:
- **Executor**: LocalExecutor
- **Webserver**: puerto 5080
- **Scheduler**: corre continuamente
- **DAGs folder**: `/opt/airflow/dags`

---

## FastAPI

API de inferencia ligera. Endpoints: `GET /health`, `GET /features`, `POST /predict`

---

## Docker Compose — Infraestructura local

Todo el entorno corre en Docker Compose con los siguientes servicios:

| Servicio | Imagen | Puerto | Descripción |
|----------|--------|--------|-------------|
| **postgres** | postgres:15 | 5432 | Metastore compartido (Airflow + MLflow) |
| **mlflow** | custom (python:3.11-slim) | 5081 | MLflow tracking server |
| **airflow-webserver** | apache/airflow:2.10.4 | 5080 | Airflow UI |
| **airflow-scheduler** | apache/airflow:2.10.4 | — | Airflow scheduler |

### Quick start

```bash
cd docker
cp .env.example .env
docker compose up -d
```

### URLs de acceso

- **MLflow**: http://localhost:5081
- **Airflow**: http://localhost:5080 (admin / admin)

---

## PostgreSQL

Metastore compartido entre Airflow y MLflow.

- Airflow guarda metadata de DAGs y task runs
- MLflow guarda experiments, metrics, y model registry

---

## CrewAI

Red Team Agent con 3 agents: PayloadHunter → AttackSimulator → Reporter