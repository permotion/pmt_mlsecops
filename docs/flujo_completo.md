# Flujo Completo del Pipeline (Stages 0–10)

Índice del ciclo de vida MLSecOps. Cada stage tiene su página dedicada bajo **Arquitectura**.

---

## Mapa rápido

| Stage | Nombre | Tipo | Página |
|-------|--------|------|--------|
| 0 | Curado del dataset | DAG | [Stage 0](stage_0_curation.md) |
| 1 | Exploración (EDA) | Notebook | [Stage 1](stage_1_eda.md) |
| 2 | Preprocess | DAG | [Stage 2](stage_2_preprocess.md) |
| 3 | Prototipado | Notebook | [Stage 3](stage_3_experiments.md) |
| 4 | Train | DAG | [Stage 4](stage_4_train.md) |
| 5 | Promote to staging | DAG | [Stage 5](stage_5_promote.md) |
| 6 | Auditoría Blue Team | Humano + API | [Stage 6](stage_6_blue_team_audit.md) |
| 7 | Deploy a producción | DAG | [Stage 7](stage_7_deploy.md) |
| 8 | API serving | FastAPI | [Stage 8](stage_8_api_serving.md) |
| 9 | Monitoreo | Operación | [Stage 9](stage_9_monitoreo.md) |
| 10 | Red Team + feedback | CrewAI | [Stage 10](stage_10_red_team.md) |

Visión general: [Arquitectura](arquitectura.md) · Entradas/salidas: [Fases MLOps](arquitectura_fases.md)

---

## Diagrama de transiciones

```text
Stage 0 ──► Stage 1 ──► Stage 2 ──► Stage 3 ──► Stage 4
(curate)    (EDA)       (preproc)   (experiments) (train)
                                                  │
                                                  ▼
Stage 10 ◄── Stage 9 ◄── Stage 8 ◄── Stage 7 ◄── Stage 5 ──► Stage 6
(feedback)  (monitor)   (API prod)  (deploy)    (promote)   (Blue Team)
```

---

## Resumen por stage

### Stage 0 — Curado (`dag_curate_dataset`)

Escaneo PII sobre `csic_database.csv`. Output: `curation_report.md`. **No modifica datos.**

→ [Detalle](stage_0_curation.md)

### Stage 1 — EDA (`csic2010_eda.ipynb`)

Análisis exploratorio: clases, métodos HTTP, patrones de ataque, diseño de features.

→ [Detalle](stage_1_eda.md)

### Stage 2 — Preprocess (`dag_preprocess`)

CSV → `features_v5.parquet` (27 features).

→ [Detalle](stage_2_preprocess.md)

### Stage 3 — Prototipado (`model_csic_experiments.ipynb`)

4 algoritmos con `skip_promote=True`. Run canónico: XGBoost precision 0.7944.

→ [Detalle](stage_3_experiments.md)

### Stage 4 — Train (`dag_train`)

Misma lógica que Stage 3, automatizada. 4 runs en MLflow.

→ [Detalle](stage_4_train.md)

### Stage 5 — Promote (`dag_promote_model`)

Recall ≥ 0.95 → mayor precision → alias `@staging` + tag `candidate`.

→ [Detalle](stage_5_promote.md)

### Stage 6 — Blue Team

DAST contra API `:5082` → `POST /model/approve` → tag `approved`.

→ [Detalle](stage_6_blue_team_audit.md)

### Stage 7 — Deploy (`dag_deploy_prod`)

Valida `approved` → alias `@production` → alerta Red Team.

→ [Detalle](stage_7_deploy.md)

### Stage 8 — API Serving (WAF Simulado)

FastAPI con modelo `@production` en `:5082`.
Guarda logs estructurados en `production_logs.csv` para monitoreo.

→ [Detalle](stage_8_api_serving.md)

### Stage 9 — Monitoreo (Data Drift)

Evidently AI evalúa la desviación matemática de features. Orquestado por `dag_stage9_monitoring`.
Alerta al Blue Team sobre posibles mutaciones de ataque.

→ [Detalle](stage_9_monitoreo.md)

### Stage 10 — Red Team (Macro-GAN Semántica)

Agentes CrewAI mutan iterativamente ataques contra la API.
Generan reportes Markdown. El éxito de la evasión inicia un ciclo de re-entrenamiento.

→ [Detalle](stage_10_red_team.md)

---

## Equivalencia Steps (8 pasos MLOps)

Algunos documentos usan Steps 1–8 agrupando notebooks con DAGs:

| Steps 1–8 | Stages equivalentes |
|-----------|---------------------|
| Step 1 | Stage 0 |
| Step 2 | Stage 1 |
| Step 3 | Stage 2 |
| Step 4 | Stage 3 |
| Step 5 | Stage 4 |
| Step 6 | Stage 5 |
| Step 7 | Stage 6 |
| Step 8 | Stage 7 |

Stages 8–10 = operación post-deploy (API, monitoreo, Red Team).
