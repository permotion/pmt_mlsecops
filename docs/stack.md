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

Lenguaje principal para ML, API, scripts, pipelines.

Ecosistema maduro: pandas, scikit-learn, lightgbm, mlflow, crewai, fastapi.

---

## LightGBM

Gradient boosting rápido y eficiente. Maneja datos desbalanceados con `scale_pos_weight`.

---

## MLflow 3.x

Experiment tracking + Model Registry. Versiones y aliases (staging/production/archived) en vez de stages deprecated.

---

## Apache Airflow

Orquestación de pipelines con DAGs: `verify_data → preprocess → train → register → evaluate`

---

## FastAPI

API de inferencia ligera. Endpoints: `GET /health`, `GET /features`, `POST /predict`

---

## CrewAI

Red Team Agent con 3 agents: PayloadHunter → AttackSimulator → Reporter