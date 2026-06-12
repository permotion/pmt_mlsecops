# Stage 8 — API Serving en Producción

---

## Objetivo

Exponer el modelo con alias `@production` para inferencia en tiempo real sobre requests HTTP.

**Responsable:** MLOps / Infra (API en host local en el MVP)  
**Componente:** `src/mlsec/api/model_serving.py` (FastAPI)

---

## Arquitectura

```text
MLflow Registry (@production)
        │
        ▼
model_serving.py (FastAPI :5082)
        │
        ├── GET  /health
        ├── GET  /model/info
        ├── POST /predict
        ├── POST /predict/http    ← principal
        └── POST /model/approve   ← solo staging
```

**Nota:** FastAPI **no está en Docker Compose** — corre en el host apuntando a MLflow en `:5081`.

---

## Ejecución

```bash
pip install -r src/mlsec/api/requirements.txt
export MLFLOW_TRACKING_URI=http://localhost:5081
# Opcional: MLFLOW_MODEL_NAME=model-csic, STAGE=production
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

Por defecto carga alias `@staging`. Para producción, configurar `STAGE=production` en el entorno o ajustar el código.

---

## Endpoint principal: `/predict/http`

Acepta un request HTTP estructurado; extrae internamente las **27 features** de v5:

```bash
curl -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "url": "http://localhost/tienda?id=1'\'' OR 1=1--",
    "content_length": 0,
    "body": ""
  }'
```

Respuesta: `prediction` (0/1), `probability`, `threshold`, `latency_ms`.

---

## Documentación de API

Referencia completa de endpoints: **[src/mlsec/api/README.md](../src/mlsec/api/README.md)**.

---

## Integración futura

En el MVP la API es localhost. Integración con WAF o reverse proxy queda fuera de scope — el modelo se consume vía HTTP JSON.

---

## Navegación

← [Stage 7 — Deploy](stage_7_deploy.md) · [Stage 9 — Monitoreo](stage_9_monitoreo.md) →
