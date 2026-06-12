# Arquitectura — Visión General del Pipeline

---

## Ciclo de vida MLOps (Stages 0-10)

El pipeline de PMT MLSecOps está estructurado en 11 fases discretas (Stages 0 al 10). Esta convención unificada rige todo el proyecto, desde la orquestación en Airflow hasta las pruebas del Red Team.

Ver detalle de entradas/salidas en [Fases y Pipeline MLOps](arquitectura_fases.md).  
Índice por stage: [Flujo completo 0–10](flujo_completo.md)

---

## Diagrama de flujo completo

```text
================================================================================
                            MLSecOps Pipeline
================================================================================

[Dataset CSIC 2010 — data/raw/csic2010/csic_database.csv]
      │
      ▼
+------------------------------------+
| ⚙️ Stage 0: dag_curate_dataset     | (MLOps) — escaneo PII, sin modificar datos
+------------------------------------+
      │
      ▼
+------------------------------------+
| 📓 Stage 1: csic2010_eda.ipynb     | (Data Science / Blue Team)
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Stage 2: dag_preprocess         | (MLOps) → features_v5.parquet
+------------------------------------+
      │
      ▼
+------------------------------------+
| 📓 Stage 3: model_experiments      | (Data Science) — skip_promote=True
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Stage 4: dag_train              | (MLOps) → 4 runs en MLflow
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Stage 5: dag_promote_model      | (MLOps) → @staging + tag candidate
|                                    |         → Alerta Blue Team
+------------------------------------+
      │
      ▼
+------------------------------------+
| 🛡️ Stage 6: Validación de Staging  | (Blue Team)
|   FastAPI :5082 — /predict/http    | → POST /model/approve → tag approved
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Stage 7: dag_deploy_prod        | (MLOps) → valida approved
|                                    |         → @production + Alerta Red Team
+------------------------------------+
      │
      ▼
+------------------------------------+
| 🚀 Stage 8: model_serving API      | FastAPI :5082 (modelo @production)
+------------------------------------+
      │
          ┌──────────────────────────┴──────────────────────────┐
          ▼                                                      ▼
+---------------------------+              +-----------------------------------+
| Stage 9 — MONITOREO       |              | Stage 10 — RED TEAM (Macro-GAN)   |
| Blue Team: Evidently AI   |              | PayloadHunter → Latent Space      |
| Data Drift Report         |              | AttackSimulator → Bypass testing  |
+---------------------------+              +-----------------------------------+
          │                                                  │
          └────────────────────────┬─────────────────────────┘
                                   ▼
                         ┌─────────────────────┐
                         │  FEEDBACK LOOP      │
                         │  MLOps → re-training│
                         └─────────────────────┘
```

---

## Ciclo de vida (Stages 0–10)

| Stage | Componente | Página |
|-------|------------|--------|
| 0 | `dag_curate_dataset` | [Stage 0](stage_0_curation.md) |
| 1 | `csic2010_eda.ipynb` | [Stage 1](stage_1_eda.md) |
| 2 | `dag_preprocess` | [Stage 2](stage_2_preprocess.md) |
| 3 | `model_csic_experiments.ipynb` | [Stage 3](stage_3_experiments.md) |
| 4 | `dag_train` | [Stage 4](stage_4_train.md) |
| 5 | `dag_promote_model` | [Stage 5](stage_5_promote.md) |
| 6 | FastAPI + Blue Team | [Stage 6](stage_6_blue_team_audit.md) |
| 7 | `dag_deploy_prod` | [Stage 7](stage_7_deploy.md) |
| 8 | `model_serving.py` | [Stage 8](stage_8_api_serving.md) |
| 9 | `dag_stage9_monitoring.py` | [Stage 9](stage_9_monitoreo.md) |
| 10 | `red_team_crew.py` | [Stage 10](stage_10_red_team.md) |

Índice: [Flujo completo](flujo_completo.md) · Guías: [Blue Team](blue_team.md) · [Red Team](red_team.md)

---

## Gobernanza MLflow

```text
dag_train           → 4 runs (LR, RF, XGBoost, LightGBM)
dag_promote_model   → alias @staging + tag candidate
Blue Team           → POST /model/approve → tag approved
dag_deploy_prod     → alias @production
```

Criterio de selección en Step 6: recall ≥ 0.95 → mayor precision (run canónico v5: **XGBoost**).

---

## Arquitectura de servicios

```text
┌─────────────────────────────────────────────────────────┐
│  Docker Compose (docker/)                               │
│  PostgreSQL :5432  ←  MLflow :5081  ←  Airflow :5080   │
└─────────────────────────────────────────────────────────┘
                              │
                    MLflow Model Registry
                              │
                    ┌─────────▼─────────┐
                    │  FastAPI :5082    │  ← fuera de Docker (host local)
                    │  model_serving    │
                    └───────────────────┘
```

| Servicio | Puerto | Dónde corre | Rol |
|----------|--------|-------------|-----|
| PostgreSQL | 5432 | Docker | Metastore Airflow + MLflow |
| MLflow | 5081 | Docker | Tracking + Registry + artefactos |
| Airflow | 5080 | Docker | Orquestación de DAGs |
| FastAPI | 5082 | **Host local** | Inferencia + aprobación Blue Team |

Detalle en [Stack Tecnológico](stack.md) y [Docker README](../docker/README.md).

---

## Roles y responsabilidades

| Equipo | Misión principal | Actividad en el pipeline |
|--------|------------------|--------------------------|
| **Data Science** | Diseñar features y evaluar algoritmos | Stages 1 y 3 (notebooks). Calibrar threshold. |
| **MLOps** | Automatizar la tubería e infra | Stages 0, 2, 4, 5 y 7 (DAGs). Docker Compose. |
| **Blue Team** | Defensa y auditoría | Stage 6: DAST contra API en staging. Stage 9: monitoreo. |
| **Red Team** | Simulación de adversarios | Stage 10: payloads frescos contra API. Reportes FN. |
