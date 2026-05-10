# Blue Team — Guía

---

## Tareas del Blue Team

| # | Tarea | Periodicidad |
|---|-------|---------------|
| 1 | Revisar modelos en Staging | Cuando aparece nuevo candidato |
| 2 | Evaluar factores de decisión | Durante revisión de staging |
| 3 | Aprobar o rechazar modelo | Después de evaluación |
| 4 | Promover a Production | Si se aprueba |
| 5 | Monitorear en producción | Continuo |
| 6 | Investigar falsos positivos | Cuando se detectan alertas |
| 7 | Evaluar gaps del Red Team | Cada FN Report |
| 8 | Solicitar re-training a MLOps | Si se detectan gaps |

---

## Revisión de modelo en Staging

1. Abrir MLflow UI: http://localhost:5081
2. Ir a **Models** → seleccionar `mlsec-model-a`
3. Filtrar por **Stage: Staging**
4. Revisar métricas: test_recall, test_precision, gap_recall, threshold

---

## Factores de decisión

### Métricas de training (criterios mínimos)

| Métrica | Criterio |
|---------|----------|
| test_recall | ≥ 0.95 |
| test_precision | ≥ 0.75 |
| gap_recall | ≤ 0.05 |

### FP rate en producción (estimado)

| Threshold | FP rate (99:1 tráfico) |
|-----------|------------------------|
| 0.3002 | ~17.4% |
| 0.4723 | ~12.7% |

---

## Checklist de decisión

```
☐ test_recall ≥ 0.95
☐ test_precision ≥ 0.75
☐ gap_recall ≤ 0.05
☐ FP rate aceptable para nuestro contexto
☐ Latencia API aceptable (p95 < 500ms)
☐ No hay alertas pendientes
```

---

## Decisiones posibles

| Decisión | Acción |
|----------|--------|
| **Aprobar** | Promover a Production |
| **Rechazar** | Quedarse con Production actual |
| **Aprobar con ajustes** | Solicitar re-training con threshold diferente |