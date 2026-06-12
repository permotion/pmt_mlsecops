# PMT MLSecOps

**Pipeline MLOps completo de detección de ataques HTTP con integración Blue Team y Red Team.**

---

## Quick start

### 1. Levantar infraestructura

```bash
cd docker
cp .env.example .env
docker compose up -d
```

### 2. Acceder a las UIs

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| MLflow | http://localhost:5081 | — |
| Airflow | http://localhost:5080 | admin / admin |

### 3. Verificar que está todo arriba

```bash
docker compose ps
```

---

## Documentación

📚 **https://permotion.github.io/pmt_mlsecops/**

---

## Estructura del proyecto

```
PMT_MLSecOps/
├── docker/                    # Docker Compose + Dockerfiles
│   ├── docker-compose.yml
│   ├── Dockerfile.mlflow
│   ├── Dockerfile.airflow
│   └── README.md
├── dags/                      # Airflow DAGs
├── src/                       # Código Python (preprocess, train, etc.)
├── data/                      # Datasets
│   └── raw/csic2010/          # Dataset CSIC 2010
├── docs/                      # Documentación MkDocs
├── requirements-ml.txt       # Dependencias ML
└── requirements-docs.txt      # Dependencias documentación
```

---

## Ciclo de Vida (8 Steps)

| Step | Nombre | Responsable |
|------|--------|-------------|
| 1 | `dag_curate_dataset` | MLOps |
| 2 | Exploración (`eda.ipynb`) | Data Science |
| 3 | `dag_preprocess` | MLOps |
| 4 | Prototipado (`experiments.ipynb`) | Data Science |
| 5 | `dag_train` (Entrenamiento y Registro) | MLOps |
| 6 | `dag_promote_model` (A `staging` + Alerta) | MLOps |
| 7 | Auditoría y Aprobación de API | Blue Team |
| 8 | `dag_deploy_prod` (A `production` + Alerta) | MLOps |

---

## Tech stack

- **Airflow** — orquestación de pipelines automatizados
- **MLflow** — tracking de experimentos y model registry centralizado
- **PostgreSQL** — metastore compartido
- **XGBoost** — modelo seleccionado en el run canónico v5 (4 algoritmos comparados por run)
- **FastAPI** — API de inferencia (con endpoints para aprobación del Blue Team)