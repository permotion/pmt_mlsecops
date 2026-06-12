# Stage 5 — Promoción a Staging

---

## Objetivo

Seleccionar automáticamente el **mejor run de MLflow** (recall ≥ 0.95, mayor precision) y promoverlo al alias `@staging` para revisión del Blue Team.

**Responsable:** MLOps  
**Componente:** `dag_promote_model` (Airflow, ejecución manual)

---

## DAG

| | |
|---|---|
| **Archivo** | `dags/dag_promote_model.py` |
| **Tag Airflow** | `stage-6` |
| **Trigger** | Manual (`schedule=None`) |

### Pipeline de tasks

```
find_best_candidate → promote_to_staging → notify_blue_team
```

---

## Criterios de selección

```python
FEATURES_VERSION = "v5"
MIN_RECALL = 0.95
# Ordenar candidatos por precision descendente → elegir el primero
```

| Paso | Acción |
|------|--------|
| 1 | Buscar runs en experiment `model-csic` con `features_version=v5` |
| 2 | Filtrar `recall >= 0.95` |
| 3 | Ordenar por `precision` descendente |
| 4 | Registrar en Model Registry + alias `@staging` |
| 5 | Tag `deployment_stage=candidate` |
| 6 | Alerta SNS al Blue Team (simulada en logs si no hay ARN) |

---

## Outputs

| Output | Ubicación |
|--------|-----------|
| Modelo registrado | MLflow Registry → `model-csic` |
| Alias | `@staging` |
| Tag | `deployment_stage=candidate` |
| Alerta | Print JSON → topic SNS `AIRFLOW_VAR_SNS_BLUE_TEAM_TOPIC_ARN` |

**Resultado esperado (run v5):** XGBoost run `d234a90a` — precision 0.7944.

---

## Variables de entorno

```bash
MLFLOW_TRACKING_URI=http://localhost:5081
MLFLOW_MODEL_NAME=model-csic
MLFLOW_FEATURES_VERSION=v5
MIN_RECALL=0.95
```

---

## Prerrequisitos

1. `dag_train` ejecutado (Stage 4) con runs en MLflow
2. MLflow accesible desde Airflow (`http://mlflow:5000` en Docker)

---

## Siguiente paso

Blue Team revisa el modelo en staging → [Stage 6 — Auditoría Blue Team](stage_6_blue_team_audit.md)

---

## Navegación

← [Stage 4 — Train](stage_4_train.md) · [Stage 6 — Blue Team](stage_6_blue_team_audit.md) →
