# Objetivos

---

## Objetivo general

**Diseñar e implementar un pipeline MLOps completo de detección de ataques HTTP que integre equipos de ML, Blue Team y Red Team, con gobernanza de modelos en producción y feedback loop automatizado.**

---

## Objetivos específicos

| # | Objetivo | Entregable | Stage |
|---|----------|------------|-------|
| 1 | Automatizar el ciclo de entrenamiento | DAG `dag_model_a`: `verify_data → preprocess → train → register → evaluate` | 1-4 |
| 2 | Garantizar gobernanza de modelos | MLflow Registry con aliases (staging/production/archived) y tags (candidate/production) | 4-5 |
| 3 | Integrar hombre en el loop (Blue Team) | Evaluación manual antes de producción con checklist de factores de decisión | 6 |
| 4 | Cerrar el flujo con Red Team Agent | CrewAI que busca payloads frescos, testa contra API, genera FN reports | 10 |
| 5 | Monitorear en producción | Métricas: FP rate, recall, latencia, disponibilidad con umbrales de alerta | 9 |
| 6 | Cerrar el ciclo de mejora | Cuando detection_rate < 85%, Blue Team solicita re-training a MLOps | 10 |

---

## Criterios de éxito del MVP

| Métrica | Target | Verificación |
|---------|--------|--------------|
| Recall (test) | ≥ 0.95 | El modelo detecta 95%+ de ataques |
| Precision (test) | ≥ 0.75 | Menos del 25% de falsas alarmas |
| Gap recall (train-test) | ≤ 0.05 | Bajo riesgo de overfitting |
| ROC-AUC | ≥ 0.95 | Excelente capacidad discriminativa |
| FP rate (producción) | < 20% | Con threshold 0.3002 en tráfico 99:1 |
| Latencia API | p95 < 500ms | Respuesta rápida del endpoint /predict |
| Detection rate (Red Team) | ≥ 85% | Payloads frescos detectados |

---

## Stack tecnológico

| Herramienta | Rol | Por qué |
|-------------|-----|---------|
| **Python 3.11** | Lenguaje principal | Compatibilidad con todas las librerías |
| **LightGBM** | Modelo ML | Rápido, eficiente, maneja datos desbalanceados con `scale_pos_weight` |
| **MLflow 3.x** | Experiment tracking + Model Registry | Versionado de modelos, aliases (staging/production) en vez de stages deprecated |
| **Apache Airflow** | Orquestación | DAGs con dependencies, scheduling, retry logic |
| **FastAPI** | API de inferencia | Ligero, rápido, carga modelo de MLflow Registry |
| **PostgreSQL** | Metastore | Compartido entre MLflow y Airflow via docker volume |
| **CrewAI** | Red Team Agent | Tres agents (PayloadHunter, AttackSimulator, Reporter) para testing automatizado |
| **MkDocs + Material** | Documentación | Navegable, mantenida cerca del código |

---

## Resultados esperados del pipeline

```
Input: csic_database.csv (61,065 filas, 41% ataques)
         │
         ▼
Stage 0: Curado → PII removido, deduplicado, validation
         │
         ▼
Stage 1-4: Airflow DAG (automático)
         │
         ▼
Output: mlsec-model-a vN en Production
        - ROC-AUC: 0.9661
        - Recall: 0.9543 (≥ 0.95 ✅)
        - Precision: 0.7929 (≥ 0.75 ✅)
        - Threshold: 0.3002

+ FN Report (Red Team Agent cada 6h)
+ Monitoreo continuo (FP rate, latencia, disponibilidad)
+ Feedback loop (si detection_rate < 85% → re-training)
```