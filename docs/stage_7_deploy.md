# Stage 7 — Despliegue a Producción

---

## Objetivo

Promover el modelo **aprobado** en staging al alias `@production`, tras verificar el tag `deployment_stage=approved`.

**Responsable:** MLOps  
**Componente:** `dag_deploy_prod` (Airflow, ejecución manual)

---

## DAG

| | |
|---|---|
| **Archivo** | `dags/dag_deploy_prod.py` |
| **Tag Airflow** | `stage-7` |
| **Trigger** | Manual (`schedule=None`) |

### Pipeline de tasks

```
validate_approval → promote_to_prod → notify_red_team
```

---

## Gate de seguridad

El DAG **aborta** si el modelo en `@staging` no tiene `deployment_stage=approved`:

```python
if stage_tag != "approved":
    raise ValueError("Blue Team debe aprobar antes de desplegar.")
```

Esto garantiza que ningún modelo llegue a producción sin firma del Blue Team.

---

## Outputs

| Output | Descripción |
|--------|-------------|
| Alias `@production` | Modelo activo para inferencia |
| Tag `deployment_stage=production` | Estado en Registry |
| Tag `deployed_at` | Timestamp del deploy |
| Alerta Red Team | SNS simulada en logs |

---

## Ejecución

1. Confirmar tag `approved` en MLflow (Stage 6)
2. Airflow UI → `dag_deploy_prod` → Trigger DAG
3. Verificar alias `@production` en http://localhost:5081
4. Reiniciar/recargar API si apunta a `@production`

---

## Manual paso a paso

Guía operativa con capturas de flujo MLflow: **[Manual de Aprobación y Deploy](README_deploy.md)**.

---

## Siguiente paso

API sirviendo `@production` → [Stage 8 — API Serving](stage_8_api_serving.md)

---

## Navegación

← [Stage 6 — Blue Team](stage_6_blue_team_audit.md) · [Stage 8 — API Serving](stage_8_api_serving.md) →
