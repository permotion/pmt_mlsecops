# Conceptos Clave — MLOps y Gobernanza

---

## ¿Qué es MLOps?

**MLOps = Machine Learning + Operations**

Es la disciplina de integrar el desarrollo de modelos ML con las operaciones de software: orquestación, deployment, monitoreo, gobernanza y re-entrenamiento.

En **PMT MLSecOps**, MLOps no es solo entrenar un clasificador de ataques HTTP — es operar ese modelo con un ciclo de vida auditable y roles de seguridad integrados.

---

## Sin MLOps vs. con MLOps (en este proyecto)

| Sin MLOps | Con MLOps (PMT MLSecOps) |
|-----------|--------------------------|
| Notebook → copiar pickle a prod | Airflow ejecuta `dag_train` de forma repetible |
| Un solo entrenamiento | Registry con versiones; alias `@staging` / `@production` |
| Degradación silenciosa | Red Team + monitoreo Blue Team (Stages 9–10) |
| Sin trazabilidad | MLflow: métricas, threshold, run_id por versión |
| Aprobación informal | Gate Blue Team: tag `approved` antes de `@production` |

---

## Stack MLOps del proyecto

| Componente | Rol en PMT MLSecOps |
|------------|---------------------|
| **Apache Airflow** | 5 DAGs manuales (curate → preprocess → train → promote → deploy) |
| **MLflow 3.x** | Experiment tracking + Model Registry (`model-csic`) |
| **PostgreSQL** | Metastore compartido Airflow + MLflow |
| **FastAPI** | Inferencia + endpoint `/model/approve` (host `:5082`) |
| **Docker Compose** | MLflow, Airflow, Postgres (API fuera de Docker) |

Detalle: [Stack Tecnológico](stack.md)

---

## Separación investigación vs. producción

Principio del proyecto: **los modelos en producción no se entrenan a mano**.

| | Investigación | Producción |
|---|---|---|
| **Quién** | Data Science | MLOps |
| **Dónde** | Notebooks (`skip_promote=True`) | DAGs Airflow |
| **Stages** | 1 (EDA), 3 (experimentos) | 0, 2, 4, 5, 7 |
| **Registry** | Solo logging de runs | Aliases, tags, promoción |

Misma función de entrenamiento en ambos mundos:

```python
from src.mlsec.data.train_model_a import train_model_a

# Notebook: skip_promote=True
# DAG: skip_promote=False (default)
```

---

## Gobernanza de modelos (MLflow Registry)

### Modelo registrado

- **Nombre:** `model-csic`
- **Experiment:** `model-csic`
- **Features:** `features_v5.parquet` (27 variables)

### Aliases (MLflow 3.x)

Reemplazan los *stages* deprecated de MLflow:

| Alias | Significado | Cuándo se asigna |
|-------|-------------|------------------|
| `@staging` | Candidato para revisión Blue Team | `dag_promote_model` (Stage 5) |
| `@production` | Modelo activo en inferencia | `dag_deploy_prod` (Stage 7) |

### Tags de gobernanza

| Tag | Valores | Quién lo setea |
|-----|---------|----------------|
| `candidate` | (Presencia del tag) | `dag_train` (Step 4) |
| `approved` | (Presencia del tag) | Blue Team (`POST /model/approve`) |
| `selected_at` | Fecha de selección | `dag_promote_model` |
| `deployed_at` | Timestamp de deploy | `dag_deploy_prod` |

### Flujo de tags

```text
dag_train
    └── 4 runs MLflow + tag candidate

dag_promote_model
    └── alias @staging

Blue Team — POST /model/approve
    └── tag approved

dag_deploy_prod (valida approved)
    └── alias @production
```

Si `dag_deploy_prod` no encuentra `approved`, **aborta** — no hay deploy silencioso a producción.

---

## Criterios de selección del candidato

Implementados en `train_model_a.py` y `dag_promote_model.py`:

1. Filtrar runs con `features_version=v5` y `recall >= 0.95`
2. Entre esos, elegir **mayor precision**
3. Run canónico actual: **XGBoost** — recall 0.9535, precision 0.7944, threshold 0.2502

Ver [Stage 5 — Promote](stage_5_promote.md) y [Resultados Stage 3](results/stage_3_results.md).

---

## Ciclo de vida completo (Stages 0–10)

```text
Stage 0–4   Datos + entrenamiento
Stage 5     Promote → @staging
Stage 6     Blue Team → approved
Stage 7     Deploy → @production
Stage 8     API serving
Stage 9     Monitoreo (FP, latencia)
Stage 10    Red Team → FN reports → re-training
         └──────────────────────────────────┘
                        feedback loop
```

Índice: [Flujo completo 0–10](flujo_completo.md) · [Arquitectura](arquitectura.md)

---

## DAGs del pipeline

| DAG | Stage | Función |
|-----|-------|---------|
| `dag_curate_dataset` | 0 | Escaneo PII → reporte |
| `dag_preprocess` | 2 | CSV → `features_v5.parquet` |
| `dag_train` | 4 | 4 modelos → MLflow |
| `dag_promote_model` | 5 | Mejor run → `@staging` |
| `dag_deploy_prod` | 7 | `approved` → `@production` |

Todos con `schedule=None` — ejecución **manual** desde Airflow UI.

---

## Conceptos relacionados

- [Threshold calibration](conceptos_threshold.md) — cómo se elige el umbral de decisión
- [Blue Team y Red Team](conceptos_equipos.md) — roles de seguridad en el pipeline
- [Arquitectura](arquitectura.md) — visión general Stages 0–10
