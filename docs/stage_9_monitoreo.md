# Stage 9 — Monitoreo en Producción (Data Drift)

---

## Objetivo

Vigilar la salud matemática del modelo en producción, detectando **Data Drift** (desviaciones en la distribución de los datos de entrada) que puedan causar una degradación del modelo, como el aumento de Falsos Positivos o una caída del Recall.

**Responsable:** Blue Team
**Componente:** `src/mlsec/blue_team/stage9_monitoring.py` y `Evidently AI`
**Orquestación:** `dags/dag_stage9_monitoring.py` (Apache Airflow)

---

## Implementación: Evidently AI

En lugar de basarnos únicamente en alertas manuales, hemos implementado **Evidently AI**, una herramienta Open Source de clase mundial para ML Observability.

El pipeline de monitoreo ejecuta un análisis riguroso:
1. **Dataset de Referencia:** Carga el `features_v5.parquet` original (lo que el modelo "conoce").
2. **Dataset de Producción:** Lee los logs productivos de Nginx/FastAPI (`production_logs.csv`) recolectados en el Stage 8.
3. **Statistical Test:** Compara ambas distribuciones feature por feature usando pruebas no paramétricas (como *Kolmogorov-Smirnov* o *Wasserstein distance*).
4. **Reporte:** Genera un dashboard interactivo en HTML (`reports/data_drift_report.html`) que alerta visualmente si los atacantes han mutado sus tácticas (Data Drift).

---

## Arquitectura y DAG

La ejecución no es manual, está orquestada por **Apache Airflow**:

```text
Apache Airflow (dag_stage9_monitoring.py) [@daily]
      │
      ├── 1. check_production_logs (Sensor: Verifica que haya datos nuevos)
      │
      └── 2. run_evidently_drift (PythonOperator: Ejecuta stage9_monitoring.py)
                   │
                   ▼
         reports/data_drift_report.html
```

---

## Ejecución Manual (Modo Simulación)

Para propósitos de demostración, el script incluye un generador de tráfico sintético que inyecta drift intencionalmente (ej. mutando `url_length` y `param_count`).

```bash
# Ejecutar la evaluación de Data Drift
.venv/bin/python src/mlsec/blue_team/stage9_monitoring.py

# Ver el reporte generado
open reports/data_drift_report.html
```

---

## Criterios de Alerta (Feedback Loop)

| Métrica | Acción si se detecta Drift |
|---------|----------------------------|
| **Data Drift (Features)** | Si > 50% de las features muestran drift, el Blue Team debe investigar la nueva tipología de ataque. |
| **Degradación del Modelo** | Si el drift impacta el Recall o dispara los Falsos Positivos, se escala a MLOps para forzar un **Re-entrenamiento (Stage 1)**. |

---

## Navegación

← [Stage 8 — API Serving](stage_8_api_serving.md) · [Stage 10 — Red Team](stage_10_red_team.md) →
