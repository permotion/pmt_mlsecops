# Objetivos

---

## Objetivo general

**Diseñar e implementar un pipeline MLOps completo de detección de ataques HTTP que integre equipos de ML, Blue Team y Red Team, con gobernanza de modelos en producción y feedback loop automatizado.**

---

## Objetivos específicos

| # | Objetivo | Entregable | Stage |
|---|----------|------------|-------|
| 1 | Automatizar el ciclo de entrenamiento | Notebook `model_csic_experiments.ipynb` + DAGs `dag_preprocess`, `dag_train` | 2-4 |
| 2 | Garantizar gobernanza de modelos | MLflow Registry con tags (candidate/approved) y aliases (@staging/@production) | 4-7 |
| 3 | Integrar humano en el loop (Blue Team) | Evaluación manual y endpoint POST `/model/approve` | 6 |
| 4 | Cerrar el flujo con Red Team Agent | CrewAI (2 agents: PayloadHunter, AttackSimulator) generando FN reports en Markdown | 10 |
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
| FP rate (producción) | < 20% | Con threshold 0.2502 en tráfico 99:1 |
| Latencia API | p95 < 500ms | Respuesta rápida del endpoint /predict |
| Detection rate (Red Team) | ≥ 85% | Payloads frescos detectados |

---

## Stack tecnológico

*(Ver detalles completos en [Stack Tecnológico](stack.md))*

---

## Resultados objetivo del MVP

```
Input: csic_database.csv (61,065 filas, 41% ataques)
         │
         ▼
Stage 0: Curado → PII removido, deduplicado, validation
         │
         ▼
Stage 1-4: Ejecución DAGs (preprocess → train) + Notebooks manuales
         │
         ▼
Output: model-csic vN en Production (Métricas Logradas vs Target)
        - ROC-AUC: 0.9655 (Target: ≥ 0.95 ✅)
        - Recall: 0.9535 (Target: ≥ 0.95 ✅)
        - Precision: 0.7944 (Target: ≥ 0.75 ✅)
        - Threshold: 0.2502

+ FN Report (Red Team Agent ejecutado bajo demanda)
+ Monitoreo continuo (FP rate, latencia, disponibilidad)
+ Feedback loop (si detection_rate < 85% → re-training)
```