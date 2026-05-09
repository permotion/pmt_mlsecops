# PMT MLSecOps

**Sistema de detección de ataques web basado en Machine Learning con pipeline MLOps automatizado, gobernanza de modelos en producción, e integración de equipos Blue Team y Red Team.**

---

## Resumen del proyecto

Este proyecto implementa un pipeline MLOps completo para detección de ataques HTTP, integrando:

| Componente | Descripción |
|------------|-------------|
| **Airflow** | Orquestación del pipeline de entrenamiento |
| **MLflow** | Gobernanza de modelos (Registry con aliases) |
| **FastAPI** | API de inferencia en producción |
| **CrewAI** | Red Team Agent autónomo para testing adversarial |
| **Blue Team** | Hombre en el loop para validación de candidatos |

---

## Arquitectura general

```
MLOps ──▶ Airflow DAG ──▶ Preprocess ──▶ Train ──▶ Register
                                                      │
                                                  Staging
                                                      │
                                                  Blue Team
                                                      │
                              ┌───────────────────────┼───────────────────────┐
                              ▼                       ▼                       ▼
                    Promover a Prod           Quedarse Prod           Aprobar c/ajustes
                              │                         │                         │
                         alias=prod               (sin cambio)           Solicitar re-train
                              │                                               │
                         API ◀────────────────────────┴──────────────────────┘
                          │
                    Monitoreo ◀──────┐
                          │          │
                    Blue Team      Red Team
                          │          │
                    Alert si      FN Report
                    FP>20%        detection<85%
                          │          │
                          └────┬─────┘
                               ▼
                          MLOps (re-training)
```

---

## Stages del pipeline

| Stage | Nombre | Responsable |
|-------|--------|-------------|
| 0 | Curado del dataset | MLOps |
| 1 | Trigger training | Airflow |
| 2 | Preprocess | Airflow |
| 3 | Train | Airflow |
| 4 | Register | Airflow |
| 5 | MLflow Registry (Staging) | — |
| 6 | Blue Team evaluación | Blue Team |
| 7 | Promoción a Production | Blue Team |
| 8 | API serving | — |
| 9 | Monitoreo | Blue Team + AIOps |
| 10 | Feedback loop | Red Team + Blue Team + MLOps |

---

## Tech stack

- **Python 3.11** — Lenguaje principal
- **LightGBM** — Gradient boosting para clasificación
- **MLflow 3.x** — Experiment tracking y Model Registry
- **Apache Airflow** — Orquestación de pipelines
- **FastAPI** — API de inferencia
- **PostgreSQL** — Metastore compartido
- **CrewAI** — Agentes para Red Team
- **MkDocs + Material** — Documentación

---

## Empezar

### Levantar el entorno de documentación

```bash
cd PMT_MLSecOps
pip install -r requirements-docs.txt
mkdocs serve
# → http://localhost:8000
```

### Levantar servicios (Docker)

```bash
cd docker
docker compose up -d
```

Servicios disponibles:
- MLflow UI: http://localhost:5081
- Airflow: http://localhost:5080
- FastAPI: http://localhost:5082
- nginx: http://localhost:5083