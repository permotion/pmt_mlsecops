# PMT MLSecOps

## Descripción del proyecto

**PMT MLSecOps** es un sistema de detección de ataques web basado en Machine Learning con un pipeline MLOps automatizado. Clasifica peticiones HTTP como normales o maliciosas (SQL Injection, XSS, Path Traversal, etc.) usando el dataset académico **CSIC 2010** (~61.000 requests, ~41% ataques).

No es solo un modelo entrenado: implementa un ciclo de vida completo con **gobernanza de modelos**, **roles de seguridad** (Blue Team y Red Team) y **feedback loop** para re-entrenamiento. El objetivo es demostrar (a modo de ejercicio teórico/práctico) cómo operar ML en ciberseguridad con procesos, no solo con notebooks aislados.

---

## Resumen del proyecto

| Aspecto | Detalle |
|---------|---------|
| **Problema** | Detectar ataques HTTP a escala, con modelos que no se degraden en silencio. |
| **Solución** | Pipeline MLOps (Airflow + MLflow) + API FastAPI + agentes Red Team (CrewAI). |
| **Dataset** | CSIC 2010 — 27 features extraídas de requests HTTP. |
| **Modelo** | XGBoost (run v5 canónico: recall 0.9535, precision 0.7944). Se entrenan 4 algoritmos; gana el de mayor precision con recall ≥ 0.95. |
| **Gobernanza** | Aliases MLflow `@staging` → aprobación Blue Team → `@production`. |
| **Innovación** | Red Team automatizado que busca payloads frescos y prueba evasión contra la API. |
| **Documentación** | MkDocs publicada en GitHub Pages. |

---

## Objetivos

### Objetivo general
Diseñar e implementar un pipeline MLOps completo de detección de ataques HTTP que integre equipos de ML, Blue Team y Red Team, con gobernanza de modelos en producción y feedback loop automatizado.

### Objetivos específicos

| # | Objetivo | Entregable |
|---|----------|------------|
| 1 | Automatizar el ciclo de entrenamiento | Notebook + DAGs `dag_preprocess`, `dag_train` |
| 2 | Garantizar gobernanza de modelos | MLflow Registry con tags y aliases |
| 3 | Integrar humano en el loop (Blue Team) | Evaluación manual + `POST /model/approve` |
| 4 | Cerrar el flujo con Red Team Agent | CrewAI: PayloadHunter + AttackSimulator |
| 5 | Monitorear en producción | FP rate, recall, latencia, disponibilidad |
| 6 | Cerrar el ciclo de mejora | Re-training si detection rate < 85% |

---

## Criterios de éxito del MVP

| Métrica | Target | Verificación |
|---------|--------|--------------|
| Recall (test) | ≥ 0.95 | El modelo detecta 95%+ de ataques |
| Precision (test) | ≥ 0.75 | Menos del 25% de falsas alarmas |
| Gap recall (train-test) | ≤ 0.05 | Bajo riesgo de overfitting |
| ROC-AUC | ≥ 0.95 | Excelente capacidad discriminativa |
| FP rate (producción) | < 20% | Con threshold 0.2502 en tráfico 99:1 |
| Latencia API (p95) | < 500 ms | Respuesta rápida del endpoint /predict |
| Detection rate (Red Team) | ≥ 85% | Payloads frescos detectados |

---

## Diagrama de arquitectura (flujo completo)

```text
================================================================================
                         PMT MLSecOps — Pipeline Completo
================================================================================
                              [ CSIC 2010 Dataset ]
                              data/raw/csic2010/
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 0 — CURADO                                                            │
│  dag_curate_dataset (Airflow)                                                │
│  → Limpieza, deduplicación, validación                                       │
│  Output: datos limpios + curation_report.md                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — EXPLORACIÓN (Data Science / Blue Team)                            │
│  notebooks/csic2010_eda.ipynb                                                │
│  → EDA: distribuciones, morfología HTTP, diseño de features                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — PREPROCESS (MLOps)                                                │
│  dag_preprocess (Airflow)                                                    │
│  → Extracción de 27 features numéricas                                       │
│  Output: features_v5.parquet                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — PROTOTIPADO (Data Science)                                        │
│  notebooks/experiments/model_csic_experiments.ipynb                          │
│  → Compara LR, RF, XGBoost, LightGBM (skip_promote=True)                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4 — TRAIN (MLOps)                                                     │
│  dag_train (Airflow) → train_model_a.py                                      │
│  → Entrena 4 modelos, calibra threshold, registra en MLflow                  │
│  Tag: deployment_stage = candidate                                           │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5 — PROMOTE TO STAGING (MLOps)                                        │
│  dag_promote_model (Airflow)                                                 │
│  → Mejor modelo con Recall >= 0.95 → alias @staging                          │
│  → Alerta SNS/Email al Blue Team                                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 6 — BLUE TEAM AUDIT                                                   │
│  FastAPI model_serving (puerto 5082) — carga modelo @staging                 │
│  → Pruebas DAST contra /predict y /predict/http                              │
│  → POST /model/approve → tag deployment_stage = approved                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 7 — DEPLOY TO PRODUCTION (MLOps)                                      │
│  dag_deploy_prod (Airflow)                                                   │
│  → Valida tag approved → alias @production                                   │
│  → Alerta SNS al Red Team                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  STAGE 8 — API SERVING (Producción)                                          │
│  FastAPI → carga modelo @production                                          │
│  Endpoints: /health | /model/info | /predict | /predict/http                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                      ▼
┌───────────────────────────────┐      ┌───────────────────────────────────────┐
│  STAGE 9 — MONITOREO          │      │  STAGE 10 — RED TEAM (Macro-GAN)      │
│  Blue Team + Evidently AI     │      │  PayloadHunter → Latent Space OSINT   │
│  → Data Drift, FP rate        │      │  AttackSimulator → Muta y prueba API  │
│  → Alerta si Drift > 50%      │      │  → Reportes .md en reports/           │
└───────────────────────────────┘      │  → Alerta si hay Bypasses (FN)        │
                    │                  └───────────────────────────────────────┘
                    └──────────────────┬──────────────────┘
                                       ▼
                         ┌─────────────────────────┐
                         │  FEEDBACK LOOP          │
                         │  MLOps → re-training    │
                         └─────────────────────────┘
```

### Arquitectura de Servicios

```text
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │  PostgreSQL │◀───▶│   MLflow    │     │   Airflow   │
    │   :5432     │     │   :5081     │     │   :5080     │
    │  (metastore)│     │  (tracking  │     │ (scheduler  │
    │             │     │  + registry)│     │ + webserver)│
    └─────────────┘     └─────────────┘     └─────────────┘
           ▲                   ▲                   ▲
           │                   │                   │
           └───────────────────┴───────────────────┘
                               │
                    docker compose (docker/)
                               │
                         ┌─────▼─────┐
                         │  FastAPI  │
                         │  :5082    │
                         │  (local)  │
                         └───────────┘
```

---

## Stages del proceso

| Stage | Nombre | Componente | Responsable | Output |
|-------|--------|------------|-------------|--------|
| 0 | Curado del dataset | `dag_curate_dataset` | MLOps | Datos limpios |
| 1 | Exploración (EDA) | `csic2010_eda.ipynb` | Data Science | Notebook con hallazgos |
| 2 | Preprocess | `dag_preprocess` | MLOps | `features_v5.parquet` |
| 3 | Prototipado | `model_csic_experiments.ipynb` | Data Science | Experimentos MLflow |
| 4 | Train | `dag_train` | MLOps | Modelo + tag candidate |
| 5 | Promote to Staging | `dag_promote_model` | MLOps | Alias `@staging` |
| 6 | Blue Team Audit | FastAPI + `/model/approve` | Blue Team | Tag `approved` |
| 7 | Deploy to Production | `dag_deploy_prod` | MLOps | Alias `@production` |
| 8 | API Serving | `model_serving.py` | — | Inferencia en prod |
| 9 | Monitoreo (Data Drift) | `Evidently AI` | Blue Team | Reporte HTML de Drift |
| 10 | Red Team (Macro-GAN) | `red_team_crew.py` | Red Team | FN reports → re-train |

---

## Stack tecnológico

| Capa | Herramienta | Rol |
|------|-------------|-----|
| Lenguaje | Python 3.11 | Base del pipeline |
| ML | LightGBM, XGBoost, RF, LogisticRegression | Clasificación binaria |
| Orquestación | Apache Airflow | DAGs del pipeline |
| Experiment tracking | MLflow 3.x | Runs, Model Registry, aliases |
| Base de datos | PostgreSQL 15 | Metastore compartido |
| API | FastAPI + uvicorn | Inferencia y aprobación |
| Red Team | CrewAI + LiteLLM | Agentes PayloadHunter y AttackSimulator |
| Contenedores | Docker Compose | Infra local |
| Documentación | MkDocs + Material | GitHub Pages |
| CI/CD | GitHub Actions | Deploy docs en push a main |

---

## Cómo levantar los servicios disponibles

### 1. Infraestructura Docker (MLflow, Airflow, PostgreSQL)
```bash
cd PMT_MLSecOps/docker
cp .env.example .env
docker compose up -d

# Esperar ~30 segundos y verificar
docker compose ps
docker compose logs -f mlflow
```

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| MLflow UI | `http://localhost:5081` | — |
| Airflow UI | `http://localhost:5080` | `admin` / `admin` |
| PostgreSQL | `localhost:5432` | `airflow` / `airflow` |

### 2. API de inferencia (FastAPI — fuera de Docker)
*Requiere MLflow corriendo y un modelo con alias `@staging` o `@production`:*

```bash
cd PMT_MLSecOps
pip install -r requirements-ml.txt
export MLFLOW_TRACKING_URI=http://localhost:5081
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check + info del modelo |
| `/model/info` | GET | Métricas, threshold, versión |
| `/predict` | POST | Predicción con features JSON |
| `/predict/http` | POST | Predicción desde request HTTP crudo |
| `/model/approve` | POST | Aprobación Blue Team |

API disponible en: `http://localhost:5082`

### 3. Documentación local (MkDocs)
```bash
cd PMT_MLSecOps
pip install -r requirements-docs.txt
mkdocs serve
# → http://localhost:8000
```
Docs publicadas: [https://permotion.github.io/PMT_MLSecOps](https://permotion.github.io/PMT_MLSecOps)

### 4. Red Team (CrewAI)
Requiere API key y la API en producción:

```bash
export ANTHROPIC_AUTH_TOKEN=<tu-token>
export ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic  # opcional
python -m src.mlsec.red_team.red_team_crew
```
Genera reportes en `reports/red_team_report_*.md`.

### 5. Ejecutar DAGs en Airflow
1. Abrir `http://localhost:5080`
2. Activar y ejecutar en orden: `dag_curate_dataset` → `dag_preprocess` → `dag_train` → `dag_promote_model`
3. Tras aprobación Blue Team: `dag_deploy_prod`

### Comandos útiles Docker
```bash
docker compose logs -f airflow-webserver   # logs Airflow
docker compose restart mlflow              # reiniciar MLflow
docker compose down                        # bajar servicios
docker compose down -v                     # bajar y limpiar volúmenes
```