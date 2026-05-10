# Flujo Completo del Pipeline

---

## Stage 0 — Curado del Dataset

| Campo | Detalle |
|-------|---------|
| Objetivo | Dataset seguro y de calidad |
| Responsable | MLOps |
| Input | `data/raw/csic2010/csic_database.csv` |
| Output | `data/curated/csic2010/csic_database_curated.csv` |

---

## Stage 1 — Trigger Training

| Campo | Detalle |
|-------|---------|
| Objetivo | Iniciar el pipeline |
| Responsable | MLOps + Airflow |
| Input | Dataset curado |
| Output | DAG ejecutado |

---

## Stage 2 — Preprocess

| Campo | Detalle |
|-------|---------|
| Objetivo | Generar features estructuradas |
| Script | `preprocess_csic_v4.py` |
| Output | `features_v4.parquet` (24 features) |

---

## Stage 3 — Train

| Campo | Detalle |
|-------|---------|
| Objetivo | Entrenar LightGBM con threshold calibrado |
| Script | `train_model_a_pipeline.py` |
| Split | 70/15/15 |
| Threshold | 0.3002 |
| Métricas | Recall≥0.95, Precision≥0.75, Gap≤0.05 |

---

## Stage 4 — Register

| Campo | Detalle |
|-------|---------|
| Objetivo | Registrar en MLflow como candidato |
| Condición | Solo si pasa criterios |
| Output | alias=staging, tag=candidate |

---

## Stage 5 — MLflow Registry

Modelo disponible para revisión del Blue Team.

---

## Stage 6 — Blue Team: Evaluación

| Campo | Detalle |
|-------|---------|
| Objetivo | Validar si el candidato es apropiado para producción |
| Responsable | **Blue Team** |
| Factores | Métricas training, FP rate, threshold, costo operativo |

---

## Stage 7 — Promoción

- **Aprobado**: `promote_model_to_production.py` → alias=production
- **Rechazado**: se mantiene Production actual

---

## Stage 8 — API Serving

| Campo | Detalle |
|-------|---------|
| Endpoint | `POST /predict` |
| Threshold | 0.3002 |
| Latencia target | p95 < 500ms |

---

## Stage 9 — Monitoreo

| Métrica | Target | Alerta si |
|---------|--------|-----------|
| FP rate | < 20% | > 20% |
| Recall | ≥ 0.93 | < 0.93 |
| Latencia | < 500ms | > 750ms |

---

## Stage 10 — Feedback Loop

| Campo | Detalle |
|-------|---------|
| Responsable | Red Team + Blue Team + MLOps |
| DAG | `dag_red_team_agent` (cada 6h) |
| Alert | Si detection_rate < 85% |