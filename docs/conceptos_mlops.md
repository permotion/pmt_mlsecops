# Conceptos Clave — MLOps y Gobernanza

---

## ¿Qué es MLOps?

**MLOps = Machine Learning + Operations**

Es la disciplina de integrar el desarrollo de modelos ML con las operaciones de software: deployment, monitoreo, gobernanza, y retriggering.

---

## Sin MLOps vs. Con MLOps

| Sin MLOps | Con MLOps |
|-----------|-----------|
| Jupyter notebook → producción manual | Pipeline automatizado (Airflow) |
| Modelo puesto en prod y olvidado | Modelo versionado, monitoreado, reemplazable |
| Nadie sabe si el modelo degrada | Monitoreo continuo con alertas |
| Training solo una vez | Ciclo continuo |

---

## Gobernanza de modelos

MLflow Registry permite:

- **Versionado**: cada training crea una nueva versión
- **Aliases**: `staging` (candidato), `production` (en uso), `archived`
- **Tags**: metadatos como `deployment_stage=candidate`

---

## Ciclo de vida del modelo

```
Training → Staging → Evaluation → Production → Monitoring
                ↑                                   │
                └────────── Feedback loop ←────────┘
```

El modelo no se entrena una sola vez. El Red Team detecta gaps, el Blue Team solicita re-training, y el ciclo se repite.