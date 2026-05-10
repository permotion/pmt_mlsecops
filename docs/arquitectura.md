# Arquitectura — Visión General del Pipeline

---

## Diagrama de flujo completo

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
                              │                         │
                         alias=prod               Solicitar re-train
                              │
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
| 1-4 | Airflow DAG | Airflow |
| 5 | MLflow Registry (Staging) | — |
| 6 | Blue Team evaluación | Blue Team |
| 7 | Promoción a Production | Blue Team |
| 8 | API serving | — |
| 9 | Monitoreo | Blue Team + AIOps |
| 10 | Feedback loop | Red Team |

---

## Arquitectura de servicios

```
MLflow :5081   ← Experiment tracking + Model Registry
Airflow :5080  ← Orquestación + scheduling
FastAPI :5082  ← API de inferencia
Postgres :5432 ← Metastore compartido
```

---

## Roles y responsabilidades

| Rol | Responsabilidad |
|-----|-----------------|
| **MLOps** | Entrenar y registrar modelos candidatos |
| **Blue Team** | Validar, promote y monitorear modelos |
| **AIOps** | Detectar patrones anómalos en logs |
| **Red Team** | Generar inputs frescos, detectar gaps |