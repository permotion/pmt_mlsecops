# Stage 6 — Auditoría Blue Team

---

## Objetivo

Validar manualmente el modelo en **staging** antes de producción: pruebas DAST contra la API, evaluación de falsos positivos y firma de aprobación.

**Responsable:** Blue Team (humano en el loop)  
**Componente:** FastAPI + revisión MLflow

---

## Flujo

```
dag_promote_model (@staging)
        │
        ▼
Levantar API con modelo @staging
        │
        ▼
Pruebas DAST (/predict, /predict/http)
        │
        ▼
¿Cumple checklist? ──No──► Rechazar / solicitar re-train
        │
       Sí
        ▼
POST /model/approve  →  tag deployment_stage=approved
        │
        ▼
dag_deploy_prod (Stage 7)
```

---

## Levantar la API en staging

```bash
export MLFLOW_TRACKING_URI=http://localhost:5081
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

La API carga automáticamente el modelo con alias `@staging`.

---

## Endpoints a probar

| Endpoint | Uso |
|----------|-----|
| `GET /health` | Verificar modelo cargado |
| `GET /model/info` | Métricas, threshold, algoritmo |
| `POST /predict/http` | Request HTTP crudo (principal) |
| `POST /predict` | 27 features en JSON |
| `POST /model/approve` | **Firma de aprobación** |

Ejemplo de aprobación:

```bash
curl -X POST http://localhost:5082/model/approve
```

Alternativa manual: tag `deployment_stage=approved` en MLflow UI.

---

## Checklist mínimo

| Criterio | Target |
|----------|--------|
| test_recall | ≥ 0.95 |
| test_precision | ≥ 0.75 |
| gap_recall | ≤ 0.05 |
| FP rate estimado (prod 99:1) | < 20% |

---

## Guía completa

Operativa detallada, factores de decisión y monitoreo continuo: **[Blue Team Guide](blue_team.md)**.

---

## Navegación

← [Stage 5 — Promote](stage_5_promote.md) · [Stage 7 — Deploy](stage_7_deploy.md) →
