# Resultados — Stage 3: Train Model CSIC

---

Esta sección documenta los outputs y hallazgos del Stage 3 del pipeline.

---

## Objetivo del stage

Evaluar 4 algoritmos de ML (LogisticRegression, RandomForest, XGBoost, LightGBM) usando `features_v5.parquet` (27 features). Registrar el mejor en MLflow Model Registry con alias `staging` para revisión del Blue Team.

---

## Criterios de éxito

| Métrica | Target | Estado |
|---------|--------|--------|
| Recall | >= 0.95 | ✅ 3 de 4 modelos cumplen |
| Precision | >= 0.85 | ❌ Ninguno cumple (mejor: LGB 0.7918) |
| Gap val-test | <= 0.05 | ✅ Todos cumplen (mejor: LGB 0.0049) |

---

## Ejecución del notebook

**Notebook:** `notebooks/experiments/model_csic_experiments.ipynb`
**Modelo Registry:** `model-csic`
**Fecha ejecución:** 2026-05-21
**Features:** `features_v5.parquet` (27 features)

### Configuración de experimentación

```python
MODEL_NAME = 'model-csic'  # Nombre del modelo en MLflow Registry
FEATURES_PATH = 'data/processed/csic2010/features_v5.parquet'
MLFLOW_TRACKING_URI = 'http://localhost:5081'
```

### Pipeline de experimentación

```
┌─────────────────────────────────────────────────────────────────────┐
│  NOTEBOOK (experimentación)                                        │
│  notebooks/experiments/model_csic_experiments.ipynb                  │
│                                                                     │
│  1. Carga train_model_a() del módulo src.mlsec.data              │
│  2. Ejecuta con skip_promote=True                                 │
│  3. Entrena 4 modelos (LR, RF, XGB, LGB)                           │
│  4. Loggea métricas y modelos a MLflow                             │
│  5. Análisis comparativo                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Resultados obtenidos

### Runs registrados en MLflow

| Run ID | Modelo | Description | Recall | Precision | ROC-AUC | FP | Gap |
|--------|--------|-------------|--------|-----------|---------|-----|-----|
| — | LogisticRegression | LR - 2026-05-21 | 0.9697 | 0.4739 | 0.8195 | 4047 | 0.0022 |
| — | RandomForest | RF - 2026-05-21 | 0.9481 | 0.7782 | 0.9605 | 1016 | 0.0133 |
| — | XGBoost | XGB - 2026-05-21 | 0.9577 | 0.7716 | 0.9634 | 1066 | 0.0139 |
| — | LightGBM | LGB - 2026-05-21 | 0.9551 | 0.7918 | 0.9661 | 944 | 0.0049 |

### Modelo seleccionado como mejor candidato

**LightGBM** — cumple Recall >= 0.95 y tiene mayor Precision entre los que cumplen.

| Métrica | Valor | Criterio | Estado |
|---------|-------|----------|--------|
| Recall | 0.9551 | >= 0.95 | ✅ |
| Precision | 0.7918 | >= 0.85 | ❌ |
| ROC-AUC | 0.9661 | — | — |
| FP | 944 | — | — |
| Gap precision | 0.0049 | <= 0.05 | ✅ |
| Threshold | 0.2752 | — | — |

---

## Análisis de resultados

### Por qué LightGBM es el mejor

1. **Recall >= 0.95:** Detecta 95.51% de los ataques
2. **Mayor Precision:** 0.7918 vs XGBoost 0.7716
3. **Menor Gap val-test:** 0.0049 — indica estabilidad
4. **Menor FP:** 944 vs 1066 de XGBoost

### Por qué Precision no llega a 0.85

**Causa raíz:** El techo de Precision está en las features, no en el algoritmo.

| Feature | Importancia (LightGBM) | Observación |
|---------|----------------------|-------------|
| url_length | ~1321 | Feature más importante |
| content_length | ~701 | Ataques POST tienen bodies más largos |
| content_pct_density | ~667 | Densidad de encoding en content |
| content_pct_latin1_density | ~540 | No está en v4 (solo en v7) |
| url_pct_latin1_density | ~527 | No está en v4 (solo en v7) |

Las features binarias (`url_has_pct27`, `content_has_dashdash`, etc.) capturan presencia/ausencia de patrones, pero no distinguen entre:
- Un ataque real: `%27` en SQL injection
- Un formulario legítimo: comilla en nombre de producto ("Vino Rioja")

---

## Comparativa con versión anterior (PMT MLSec)

| Modelo | PMT MLSec v7 (25 features) | PMT_MLSecOps v4 (23 features) | Diferencia |
|--------|---------------------------|------------------------------|------------|
| LightGBM | 0.7929 | 0.7918 | -0.001 |
| XGBoost | 0.7731 | 0.7716 | -0.002 |
| RandomForest | 0.7551 | 0.7782 | **+0.023** |
| LogisticRegression | 0.4110 | 0.4739 | **+0.063** |

**Nota:** v4 sin Latin-1 encoding反而 mejora RF y LR, pero LGB y XGB se mantienen similares.

---

## FP Analysis — Resultados (2026-05-21)

**Notebook:** `notebooks/experiments/model_csic_fp_analysis.ipynb`
**Modelo:** LightGBM (threshold=0.2752)
**FP totales:** 942 / 9160 en test set

### Matriz de confusión

| Tipo | Count | Descripción |
|------|-------|-------------|
| True Positives (TP) | 3591 | Ataques detectados ✅ |
| True Negatives (TN) | 4458 | Normales detectados ✅ |
| **False Positives (FP)** | **942** | Normales marcados como ataque ❌ |
| False Negatives (FN) | 169 | Ataques NO detectados |

**Precision:** 0.7922 | **Recall:** 0.9551

---

### Hallazgo 1: Requests largos son la causa principal

| Feature | FP media | TN media | Diferencia |
|---------|----------|----------|------------|
| `content_length` | 95.3 | 5.0 | **+90.4** |
| `url_query_length` | 89.8 | 6.5 | **+83.3** |
| `url_length` | 144.9 | 63.3 | **+81.6** |

Los FP son requests **3-18x más largas** que los TN en todas las features continuas.

---

### Hallazgo 2: POST tiene 2.5x más tasa de FP que GET

| Método | FP count | Tasa FP |
|--------|----------|---------|
| GET | 459 | **7.1%** |
| POST | 483 | **17.7%** |

El modelo confunde POST requests largos (legítimos) con ataques.

---

### Hallazgo 3: Las features binarias NO son el problema

| Feature | FP (%) | TN (%) |
|---------|--------|--------|
| `url_has_pct27` | 0.5% | 0.0% |
| `content_has_pct27` | 0.8% | 0.0% |
| `url_has_script` | 0.0% | 0.0% |

Los indicadores de ataque (`%27`, `dashdash`, etc.) aparecen en <1% de FP.

---

### Hallazgo 4: Hipótesis confirmadas

| Hipótesis | FP count | % de FP | Confirmada |
|-----------|----------|---------|------------|
| `content_length > 50` | 481 | 51.1% | ✅ Sí |
| GET con `url_length > 100` | 456 | 48.4% | ✅ Sí |

---

### Causa raíz

El modelo usa **features individuales** (`url_length`, `content_length`) pero **no distingue** entre:
- Un ataque real con payload largo
- Un request legítimo con muchos parámetros (formulario, búsqueda, etc.)

**Solución:** Agregar features de **ratio/contexto** que capturen si el request es "proporcionalmente largo para su tipo".

---

### Features candidatas para v5

| Feature | Fórmula | Justificación |
|---------|---------|---------------|
| `url_query_ratio` | `url_query_length / url_length` | Detecta query strings anormalmente largas |
| `content_url_ratio` | `content_length / url_query_length` | Compara body vs query |
| `is_long_post` | `method_is_post AND content_length > 100` | Flag para POST con body largo |
| `url_length_method` | `url_length * method_is_get` | Interacción largo × método |

---

## Feature Engineering v5 — Resultados

**Script:** `src/mlsec/data/preprocess_csic_v2.py`
**Features:** `features_v5.parquet` (27 features = 23 originales + 4 ratio)
**Fecha:** 2026-05-21

### Runs en MLflow (v5)

| Modelo | Run ID | Recall | Precision | ROC-AUC | FP | Gap |
|--------|--------|--------|-----------|---------|-----|-----|
| LogisticRegression | `b0c1fcc8` | 0.9649 | 0.4808 | 0.8209 | 3917 | 0.0017 |
| RandomForest | `150f894f` | 0.9492 | 0.7776 | 0.9609 | 1021 | 0.0123 |
| **XGBoost** | `d234a90a` | **0.9535** | **0.7944** | **0.9655** | **928** | 0.0054 |
| LightGBM | `e1b30307` | 0.9553 | 0.7917 | 0.9662 | 945 | 0.0043 |

### Comparativa v4 → v5

| Modelo | v4 Precision | v5 Precision | Delta |
|--------|-------------|-------------|-------|
| LightGBM | 0.7918 | 0.7917 | -0.0001 |
| **XGBoost** | 0.7716 | **0.7944** | **+0.0228** |
| RandomForest | 0.7782 | 0.7776 | -0.0006 |
| LogisticRegression | 0.4739 | 0.4808 | +0.0069 |

**Observación:** Las ratio features mejoran **XGBoost +0.023** pero LightGBM no capitaliza. El problema de fondo persiste.

---

## Conclusión: El techo de Precision (~0.79)

### Hallazgos de PMT MLSec (proyecto hermano)

El análisis exhaustivo de PMT MLSec en **v6 y v7** ya había identificado la causa raíz:

**v6 — Root cause:** Los FP son formularios de una tienda española con encoding Latin-1 (`%F1`=ñ, `%ED`=í, `%FA`=ú). El modelo confunde `%F1` con `%27` porque `content_pct_density` cuenta **todos** los `%XX` sin distinguir si son:
- Latin-1 inofensivo: `%F1`=ñ, `%ED`=í (vocales acentuadas en nombres/contraseñas)
- Ataque: `%27`=', `%3C`=< (caracteres SQLi/XSS)

**v7 — Latin-1 features:** Intentaron `content_pct_latin1_density` pero **no funcionó**. ¿Por qué? Porque el generador de ataques de CSIC 2010 incluye field names con caracteres acentuados:
```
# Ataque real con Latin-1 (el campo "apellidos" tiene %ED)
apellidos=Garc%EDa&pass=%27+OR+1%3D1--
```
Los ataques **también tienen Latin-1** — no hay separación.

### Tabla comparativa final

| Proyecto | Version | Features | Mejor Precision | Mejor Recall | ROC-AUC |
|----------|---------|----------|-----------------|--------------|---------|
| PMT MLSec | v7 | 25 | 0.7929 | 0.9529 | 0.9677 |
| PMT_MLSecOps | v5 | 27 | 0.7944 (XGB) | 0.9553 | 0.9662 |
| **Target MVP** | — | — | **0.85** | **0.95** | **0.95** |

**Conclusión:** Ambos proyectos convergen en el mismo techo de Precision (~0.79-0.80) con features de campos HTTP individuales.

---

## Modelo para producción — Aceptación del techo

| Criterio MVP | Target | Alcanzado? | Valor |
|-------------|--------|------------|-------|
| Recall | ≥ 0.95 | ✅ | 0.9535 (XGBoost v5) |
| Precision | ≥ 0.85 | ❌ | 0.7944 (techo práctico) |
| ROC-AUC | ≥ 0.95 | ✅ | 0.9655 |

### Significado operativo

- **De cada 100 ataques reales**, se detectan **~95**
- **De cada 100 alarmas del modelo**, ~20 son falsos positivos (requests legítimos)
- El Blue Team debe revisar las alarmas antes de actuar

### Decisión

Se acepta **Precision 0.79 como techo práctico** del enfoque actual (features de campos HTTP individuales). Para bajar del 20% de FP se requiere:
1. Análisis semántico de valores de parámetros individuales (mayor complejidad)
2. Features a nivel de sesión (patrones de navegación)
3. Otro enfoque — probablemente fuera del scope del MVP actual

---

## Arquitectura implementada — Opción B

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — Train Model A                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────┐    ┌────────────────────────────┐ │
│  │  NOTEBOOK (experimentación) │    │  SCRIPT (producción)       │ │
│  │                              │    │                            │ │
│  │  notebooks/experiments/      │    │  src/mlsec/data/          │ │
│  │  model_csic_experiments.ipynb  │    │  train_model_a.py          │ │
│  │                              │    │                            │ │
│  │  • Importa train_model_a()   │    │  • Misma función           │ │
│  │  • skip_promote=True        │    │  • DAG lo invoca           │ │
│  │  • Análisis interactivo     │    │  • Registro en Registry    │ │
│  └──────────────┬───────────────┘    └──────────────┬───────────┘ │
│                 │                                   │             │
│                 └───────────────┬───────────────────┘             │
│                                 ▼                                 │
│                   ┌─────────────────────────┐                    │
│                   │  MLflow                 │                    │
│                   │  Experiment: model-csic │                    │
│                   │  4 runs (uno por modelo)│                    │
│                   │  Tags + description     │                    │
│                   └─────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Cambios implementados

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Nombre modelo Registry | `mlsec-model-a` | `model-csic` |
| Experiment name | `mlsec-model-a` | `model_name` (default) |
| Descripción del run | Sin descripción | `Model CSIC {name} - {execution_time}` |
| Timestamp | No | `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` |
| Tags | Solo params | `model_name`, `features_version`, `execution_time` |
| Registro modelo | Descripción básica | `{model_name} - {execution_time} - {algorithm}` |

---

## Estado actual del pipeline

| Stage | Status | Output |
|-------|--------|--------|
| Stage 1 (Curation) | ✅ Completado | `curation_report.md` |
| Stage 2 (EDA) | ✅ Completado | `csic2010_eda.ipynb` |
| Stage 2 (Preprocess) | ✅ Completado | `features_v5.parquet` (27 features) |
| Stage 3 (Train) | ✅ Completado | XGBoost v5 mejor candidato — Precision 0.7944 |

**XGBoost v5 pasa Recall (0.9535 ≥ 0.95) pero NO Precision (0.7944 < 0.85).**
Se acepta Precision 0.79 como techo práctico — disponible para staging.

---

## Próximos pasos

| Prioridad | Acción | Notebook/Script | Estado | Descripción |
|-----------|--------|----------|--------|-------------|
| 1 | FP Analysis | `model_csic_fp_analysis.ipynb` | ✅ Completado | 942 FP — requests largos + POST > GET |
| 2 | Feature engineering v5 | `preprocess_csic_v2.py` | ✅ Completado | 4 ratio features → XGBoost +0.023 |
| 3 | Aceptar techo Precision | — | ✅ Decision | Precision ~0.79 es el techo con features HTTP |
| 4 | Promover a staging | `dag_promote_model.py` | 🔜 Pendiente | Selección automática + SNS a Blue Team |
| 5 | Blue Team review | `blue_team.md` | 🔜 Pendiente | Revisar candidato antes de producción |

---

## Stage 6 — Promoción a Staging + SNS

**DAG:** `dags/dag_promote_model.py`
**Script:** `src/mlsec/data/promote_model_to_staging.py`
**Fecha:** 2026-05-21

### Pipeline automático

```
┌─────────────────────────────────────────────────────────────────────┐
│  dag_promote_model                                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  find_best_candidate ──→ promote_to_staging ──→ notify_blue_team  │
│  (PythonOperator)          (PythonOperator)        (PythonOperator) │
│                                                                     │
│  1. Query MLflow runs con features_version=v5                       │
│  2. Filtrar: Recall >= 0.95                                          │
│  3. Seleccionar: Mayor Precision                                    │
│  4. Registrar en MLflow con alias=staging                            │
│  5. Enviar SNS al Blue Team                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Selección automática

El DAG selecciona el mejor candidato automáticamente:

```python
# Criterios de selección
features_version = "v5"
MIN_RECALL = 0.95
# Ordenado por Precision descendente → elige el mejor
```

**Resultado esperado:** XGBoost v5 (run `d234a90a`)

### Variables de entorno

```bash
MLFLOW_TRACKING_URI=http://localhost:5081
MLFLOW_MODEL_NAME=model-csic
MLFLOW_FEATURES_VERSION=v5
MIN_RECALL=0.95
AIRFLOW_VAR_SNS_BLUE_TEAM_TOPIC_ARN=arn:aws:sns:us-east-1:...:mlsecops-blue-team
```

### Script manual (alternativa al DAG)

```bash
python -m src.mlsec.data.promote_model_to_staging \
    --run-id d234a90a3a32490183467fb8214ffd46 \
    --model-name model-csic
```

---

## Estado actual del pipeline

| Stage | Status | Output |
|-------|--------|--------|
| Stage 1 (Curation) | ✅ Completado | `curation_report.md` |
| Stage 2 (EDA) | ✅ Completado | `csic2010_eda.ipynb` |
| Stage 2 (Preprocess) | ✅ Completado | `features_v5.parquet` (27 features) |
| Stage 3 (Train) | ✅ Completado | XGBoost v5 en MLflow — Precision 0.7944 |
| Stage 4 (Registry) | ✅ Completado | Runs en MLflow experiment `model-csic` |
| Stage 6 (Promote) | 🔜 Listo para ejecutar | `dag_promote_model` listo |

**XGBoost v5 es el candidato seleccionado** — listo para promoción a staging.

---

## Archivos del stage

```
notebooks/experiments/
├── model_csic_experiments.ipynb    ← notebook de experimentación (training)
└── model_csic_fp_analysis.ipynb   ← notebook de análisis de FP

src/mlsec/data/
├── preprocess_csic_v1.py           ← baseline (23 features) → features_v4.parquet
├── preprocess_csic_v2.py             ← + 4 ratio features (27 features) → features_v5.parquet
├── preprocess_csic.py                ← alias de v2 (para DAG)
├── train_model_a.py                 ← función train_model_a() (DRY)
└── promote_model_to_staging.py      ← script manual de promoción

dags/
├── dag_preprocess.py                ← Stage 2
├── dag_promote_model.py             ← Stage 6 (selección + promoción + SNS)
└── dag_curate_dataset.py           ← Stage 1
```

---

## Notas sobre MLflow

### Experiment deleted issue

Si al ejecutar aparece el error:
```
MlflowException: Cannot set a deleted experiment 'model-csic' as the active experiment
```

Solución:
```python
client = mlflow.MlflowClient()
exp = client.get_experiment_by_name('model-csic')
client.restore_experiment(exp.experiment_id)
```

### Verificar runs en MLflow

```bash
# Desde terminal con PYTHONPATH configurado
python3 << 'EOF'
import mlflow
mlflow.set_tracking_uri('http://localhost:5081')
client = mlflow.MlflowClient()
exp = client.get_experiment_by_name('model-csic')
for run in client.search_runs(exp.experiment_id):
    print(f"{run.info.run_id[:8]}: {run.data.params.get('model')} | "
          f"recall={run.data.metrics.get('recall', 0):.4f} | "
          f"precision={run.data.metrics.get('precision', 0):.4f}")
EOF
```

---

## Responsable

**MLOps** — entrenamiento y registro de candidatos