# Blue Team — Guía

Guía operativa para validación de modelos en staging, aprobación para producción y monitoreo post-deploy.

**Stages:** [6 — Auditoría](stage_6_blue_team_audit.md) · [9 — Monitoreo](stage_9_monitoreo.md)  
**Conceptos:** [Blue Team y Red Team](conceptos_equipos.md) · [Threshold calibration](conceptos_threshold.md)

---

## Misión del Blue Team

Garantizar que ningún modelo llegue a producción sin revisión humana y que el modelo activo siga siendo aceptable operativamente (FP rate, latencia, gaps reportados por Red Team).

---

## Tareas y periodicidad

| # | Tarea | Cuándo | Stage |
|---|-------|--------|-------|
| 1 | Revisar alerta de nuevo candidato en `@staging` | Tras `dag_promote_model` | 5 → 6 |
| 2 | Inspeccionar métricas en MLflow | Durante auditoría | 6 |
| 3 | Levantar API y ejecutar pruebas DAST | Durante auditoría | 6 |
| 4 | Aprobar, rechazar o pedir re-train | Fin de auditoría | 6 |
| 5 | Firmar modelo (`approved`) | Si aprueba | 6 |
| 6 | Validar deploy (opcional) | Tras `dag_deploy_prod` | 7 |
| 7 | Monitorear FP rate y latencia | Continuo | 9 |
| 8 | Revisar FN reports del Red Team | Cada reporte en `reports/` | 10 → 9 |
| 9 | Solicitar re-training a MLOps | Gaps críticos | 10 |

---

## Flujo de auditoría (Stage 6)

```text
1. Recibir alerta (SNS / log Airflow) de nuevo @staging
2. MLflow → model-csic → versión con alias staging
3. Revisar: recall, precision, threshold, gap, algoritmo
4. Levantar API apuntando a @staging
5. DAST: tráfico normal + ataques conocidos + edge cases
6. Decisión → approve / reject / re-train
7. Si approve → POST /model/approve o tag en MLflow
8. Notificar MLOps para ejecutar dag_deploy_prod
```

---

## Paso 1 — Revisión en MLflow

1. Abrir http://localhost:5081
2. **Models** → `model-csic`
3. Buscar versión con alias **`staging`** (MLflow 3.x usa aliases, no stages deprecated)
4. Revisar:

| Campo | Qué validar |
|-------|-------------|
| `recall` | ≥ 0.95 |
| `precision` | ≥ 0.75 (MVP) |
| `gap_precision` | ≤ 0.05 |
| `threshold` | Coherente (~0.25 para XGBoost v5) |
| `features_version` | `v5` |
| `model` (param) | Algoritmo (run canónico: XGBoost) |

Run de referencia: recall 0.9535, precision 0.7944, threshold **0.2502**.

---

## Paso 2 — Levantar API en staging

```bash
cd PMT_MLSecOps
pip install -r src/mlsec/api/requirements.txt
export MLFLOW_TRACKING_URI=http://localhost:5081
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

Verificar carga:

```bash
curl -s http://localhost:5082/health | jq .
curl -s http://localhost:5082/model/info | jq .
```

---

## Paso 3 — Pruebas DAST

Usar **`POST /predict/http`** (extrae 27 features automáticamente).

### Tráfico normal (esperar `prediction: 0`)

```bash
curl -s -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "url": "http://localhost:8080/tienda1/index.jsp",
    "content_length": 0,
    "body": ""
  }'
```

### SQL Injection (esperar `prediction: 1`)

```bash
curl -s -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "POST",
    "url": "http://localhost:8080/tienda/login.jsp",
    "content_length": 45,
    "content_type": "application/x-www-form-urlencoded",
    "body": "username=admin'\'' OR 1=1--&password=123"
  }'
```

### XSS en URL (esperar `prediction: 1`)

```bash
curl -s -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "url": "http://localhost/search?q=<script>alert(1)</script>",
    "content_length": 0,
    "body": ""
  }'
```

Más ejemplos: [API README](../src/mlsec/api/README.md)

---

## Criterios de decisión

### Métricas de training

| Métrica | Criterio MVP | Criterio ideal (train) |
|---------|--------------|------------------------|
| test_recall | ≥ 0.95 | ≥ 0.95 |
| test_precision | ≥ 0.75 | ≥ 0.85 |
| gap_precision | ≤ 0.05 | ≤ 0.05 |
| ROC-AUC | ≥ 0.95 | ≥ 0.95 |

### Operativos (staging / prod estimado)

| Métrica | Target |
|---------|--------|
| FP rate (tráfico 99:1) | < 20% |
| Latencia p95 `/predict/http` | < 500 ms |
| Falsos negativos en batería DAST | 0 en ataques obvios |

### Threshold y FP rate

Con threshold **0.2502** (XGBoost v5), en tráfico desbalanceado 99:1 el FP rate estimado ronda **17–20%**. Ver [Threshold calibration](conceptos_threshold.md).

---

## Checklist de aprobación

```
☐ Alias @staging apunta al run correcto
☐ recall ≥ 0.95 en test
☐ precision ≥ 0.75 (MVP)
☐ gap_precision ≤ 0.05
☐ features_version = v5
☐ API /health OK, modelo cargado
☐ DAST: normales → 0, ataques obvios → 1
☐ Latencia p95 < 500 ms en muestra
☐ FP rate estimado aceptable para el negocio
☐ Sin alertas Red Team pendientes críticas
```

---

## Decisiones posibles

| Decisión | Acción | Siguiente paso |
|----------|--------|----------------|
| **Aprobar** | Firmar `approved` | MLOps ejecuta `dag_deploy_prod` |
| **Rechazar** | No cambiar tags | Mantener `@production` actual |
| **Aprobar con ajustes** | Documentar threshold/features | MLOps re-train (Stages 2–4) |
| **Posponer** | Más pruebas / datos | Re-auditar en 24–48 h |

---

## Aprobación del modelo

### Opción A — API (recomendada)

Con la API cargando el modelo `@staging`:

```bash
curl -X POST http://localhost:5082/model/approve
```

Respuesta esperada: `status: success`, tag `deployment_stage=approved`.

### Opción B — MLflow UI

1. Models → `model-csic` → versión en staging
2. Tags → `deployment_stage` = `approved`

**Importante:** `dag_deploy_prod` falla si el tag no es exactamente `approved`.

---

## Post-aprobación

1. Confirmar tag en MLflow
2. Pedir a **MLOps** ejecutar `dag_deploy_prod` en Airflow (http://localhost:5080)
3. Verificar alias `@production` en MLflow
4. Validar API con modelo production (reiniciar uvicorn si cambió alias)

Manual: [Manual de Aprobación y Deploy](README_deploy.md)

---

## Monitoreo en producción (Stage 9)

El Blue Team monitorea la desviación matemática y operativa del modelo mediante **Evidently AI**, orquestado por `dag_stage9_monitoring`.

| Señal (Evidently AI) | Cómo detectar | Acción |
|----------------------|---------------|--------|
| **Data Drift** | Reporte en `reports/data_drift_report.html` (Alerta si > 50% de features con drift) | Investigar nueva tipología de ataque; evaluar impacto en recall. |
| **FP rate alto** | Métricas operativas en logs `/predict` | Re-calibrar threshold; consultar Data Science. |
| **FN report Red Team**| Bypasses en `reports/red_team_report_*.md` | Solicitar re-train inmediato si el ataque evadió defensas de forma crítica. |
| **Degradación Recall**| Impacto post-drift | Re-train del pipeline (Stage 1). |

---

## Integración con Red Team

```text
Red Team (Stage 10) → reports/*.md
        │
        ▼
Blue Team evalúa detection_rate y payloads FN
        │
        ├── OK (≥ 85%) → documentar
        └── Gap → ticket re-training → MLOps
```

---

## RACI resumido

| Actividad | Blue Team |
|-----------|-----------|
| Aprobar/rechazar candidato | **Accountable** |
| DAST en staging | **Responsible** |
| Monitoreo prod | **Responsible** |
| Deploy a production | Informed (ejecuta MLOps) |
| Re-training | Consulted (solicita) |

Detalle: [Matriz RACI](raci.md)
