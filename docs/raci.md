# Matriz RACI

**R** = Responsible · **A** = Accountable · **C** = Consulted · **I** = Informed · **—** = No involucrado

---

## Roles del proyecto

| Rol | Responsabilidad principal | Stages principales |
|-----|--------------------------|-------------------|
| **MLOps** | Pipeline, infra, DAGs, Registry, deploy automatizado | 0, 2, 4, 5, 7 |
| **Data Science** | EDA, experimentos, diseño de features, análisis FP | 1, 3 |
| **Blue Team** | Auditoría staging, aprobación, monitoreo prod, respuesta a FN | 6, 9 |
| **Red Team** | Payloads frescos, pruebas evasión, FN reports | 10 |

**Herramientas** (no son roles): Airflow (orquestación), MLflow (Registry), FastAPI (inferencia), CrewAI (Red Team).

Conceptos: [Blue Team y Red Team](conceptos_equipos.md) · [MLOps y gobernanza](conceptos_mlops.md)

---

## RACI por Stage (0–10)

| Stage | Actividad | MLOps | Data Science | Blue Team | Red Team |
|:-----:|-----------|:-----:|:------------:|:---------:|:--------:|
| **0** | Curado / escaneo PII (`dag_curate_dataset`) | **R/A** | I | I | — |
| **1** | EDA (`csic2010_eda.ipynb`) | I | **R/A** | C | — |
| **2** | Preprocess (`dag_preprocess`) | **R/A** | C | — | — |
| **3** | Prototipado (`model_csic_experiments.ipynb`) | I | **R/A** | C | — |
| **4** | Train (`dag_train`) | **R/A** | C | I | — |
| **5** | Promote staging (`dag_promote_model`) | **R/A** | I | **I** | — |
| **6** | Auditoría + aprobación (`/model/approve`) | I | — | **R/A** | — |
| **7** | Deploy prod (`dag_deploy_prod`) | **R/A** | — | C | **I** |
| **8** | API serving (`model_serving.py`) | **R** | — | C | C |
| **9** | Monitoreo (FP, latencia, recall) | C | — | **R/A** | I |
| **10** | Red Team CrewAI + FN reports | I | C | **C** | **R/A** |

---

## RACI — Ciclo de vida del modelo (detalle)

| # | Actividad | MLOps | Data Science | Blue Team | Red Team |
|---|-----------|:-----:|:------------:|:---------:|:--------:|
| 1 | Verificar dataset raw (`csic_database.csv`) | **R** | I | — | — |
| 2 | Generar `curation_report.md` | **R** | I | C | — |
| 3 | Exploración y diseño de features | C | **R** | C | — |
| 4 | Generar `features_v5.parquet` | **R** | C | — | — |
| 5 | Experimentar 4 algoritmos (`skip_promote`) | I | **R** | C | — |
| 6 | Entrenar y loggear runs MLflow | **R** | C | I | — |
| 7 | Seleccionar candidato (recall ≥ 0.95, max precision) | **R** | C | I | — |
| 8 | Asignar alias `@staging` + tag `candidate` | **R** | — | **I** | — |
| 9 | Notificar Blue Team (SNS / alerta) | **R** | — | **I** | — |
| 10 | Revisar métricas en MLflow + API staging | I | — | **R** | — |
| 11 | Pruebas DAST (`/predict/http`) | I | — | **R** | — |
| 12 | Decidir aprobar / rechazar / re-train | I | C | **A** | — |
| 13 | Firmar modelo (`approved`) | I | — | **R/A** | — |
| 14 | Ejecutar `dag_deploy_prod` | **R** | — | C | I |
| 15 | Validar tag `approved` (gate automático) | **R** | — | C | — |
| 16 | Asignar alias `@production` | **R** | — | I | **I** |
| 17 | Operar API con modelo production | **R** | — | C | C |
| 18 | Monitorear FP rate y latencia | C | — | **R/A** | — |
| 19 | Ejecutar Red Team (payloads frescos) | I | — | I | **R** |
| 20 | Generar FN report (`reports/`) | I | — | **I** | **R** |
| 21 | Evaluar gaps / detection rate | I | C | **R/A** | C |
| 22 | Solicitar re-training | **R/A** | **C** | **C** | I |

---

## RACI — Decisiones críticas

| Decisión | Accountable | Consulted | Responsible |
|----------|-------------|-----------|-------------|
| ¿Promover run a `@staging`? | MLOps | Data Science | MLOps (DAG) |
| ¿Aprobar para producción? | **Blue Team** | MLOps, Data Science | Blue Team |
| ¿Ejecutar deploy a `@production`? | MLOps | Blue Team | MLOps (DAG) |
| ¿Re-calibrar threshold? | Blue Team | Data Science | MLOps |
| ¿Re-entrenar por gaps Red Team? | MLOps | Data Science, Blue Team | MLOps |

---

## Métricas y responsables

| Métrica | Target | Responsable monitoreo | Acción si falla |
|---------|--------|----------------------|-----------------|
| Recall (test / staging) | ≥ 0.95 | Blue Team | Rechazar candidato o re-train |
| Precision (test) | ≥ 0.75 (MVP) | Blue Team | Evaluar FP rate en staging |
| FP rate (prod 99:1) | < 20% | Blue Team | Re-calibrar threshold / features |
| Latencia API p95 | < 500 ms | Blue Team | Escalar infra (MLOps) |
| Detection rate (Red Team) | ≥ 85% | Red Team | Alert → Blue Team → re-train |
| FN count por ciclo | < 3 | Red Team | Escalar revisión manual |
| Disponibilidad API | > 99% | MLOps / Blue Team | Incident response |

---

## Flujo de escalamiento

```text
Red Team: detection_rate < 85%
        │
        ▼
Blue Team: evalúa FN report + impacto
        │
        ├── Aceptable → documentar, monitorear
        └── Gap crítico → ticket re-training a MLOps
                │
                ▼
        MLOps: Stages 2–5 (features / train / promote)
                │
                ▼
        Blue Team: nueva auditoría Stage 6
```

---

## Páginas relacionadas

- [Blue Team Guide](blue_team.md)
- [Manual de Aprobación y Deploy](README_deploy.md)
- [Red Team Guide](red_team.md)
- [Flujo completo Stages 0–10](flujo_completo.md)
