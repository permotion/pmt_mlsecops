# Manual de Aprobación y Deploy

Procedimiento end-to-end para pasar un modelo de **`@staging`** a **`@production`** en PMT MLSecOps.

**Stage:** [7 — Deploy a producción](stage_7_deploy.md)  
**Auditoría previa:** [Blue Team Guide](blue_team.md) · [Stage 6](stage_6_blue_team_audit.md)

---

## Resumen del flujo

```text
dag_promote_model          Blue Team              dag_deploy_prod
      │                         │                        │
      ▼                         ▼                        ▼
  @staging              DAST + approve            @production
  tag=candidate         tag=approved              tag=production
      │                         │                        │
      └─────── gate ────────────┘                        │
                    (sin approved → DAG aborta)          ▼
                                                  Alerta Red Team
                                                  API :5082 reload
```

El deploy **no es 100% automático** por diseño: requiere firma del Blue Team antes de que MLOps ejecute el DAG.

---

## Prerrequisitos

| Requisito | Verificación |
|-----------|--------------|
| Docker Compose arriba | `docker compose ps` en `docker/` |
| MLflow accesible | http://localhost:5081 |
| Airflow accesible | http://localhost:5080 (admin/admin) |
| Modelo en `@staging` | MLflow → `model-csic` → alias staging |
| Blue Team completó Stage 6 | DAST OK |
| Tag `deployment_stage=approved` | MLflow o vía `/model/approve` |

---

## Fase 1 — Blue Team: auditoría en staging

Ver guía completa: [Blue Team Guide](blue_team.md)

Checklist mínimo:

- [ ] Métricas MLflow: recall ≥ 0.95, precision ≥ 0.75
- [ ] API `:5082` con modelo staging responde `/health`
- [ ] DAST con `/predict/http` (normales + ataques)
- [ ] Latencia aceptable (p95 < 500 ms)

---

## Fase 2 — Blue Team: aprobar el modelo

### Método 1 — Endpoint API (recomendado)

Con API cargando `@staging`:

```bash
curl -X POST http://localhost:5082/model/approve
```

Respuesta:

```json
{
  "status": "success",
  "message": "Modelo model-csic vN firmado y aprobado...",
  "version": "N"
}
```

### Método 2 — MLflow UI manual

1. http://localhost:5081 → **Models** → `model-csic`
2. Versión con alias **staging**
3. **Tags** → `deployment_stage` = `approved`

### Verificar tag

En MLflow UI o:

```bash
# Desde el contenedor / entorno con mlflow CLI
mlflow models get-model-version-tag -n model-csic -v <VERSION> -k deployment_stage
```

Debe retornar `approved`.

---

## Fase 3 — MLOps: deploy a producción

### Ejecutar DAG

1. Abrir http://localhost:5080
2. DAG **`dag_deploy_prod`**
3. **Trigger DAG** (ejecución manual)

### Tasks del DAG

| Task | Función |
|------|---------|
| `validate_approval` | Falla si `deployment_stage ≠ approved` |
| `promote_to_prod` | Alias `@production` + tags `production`, `deployed_at` |
| `notify_red_team` | Alerta SNS (simulada en logs si no hay ARN) |

Código: `dags/dag_deploy_prod.py`

### Resultado esperado en logs

```
✅ Modelo vN aprobado para producción.
🚀 Modelo vN promovido a PRODUCCIÓN exitosamente.
MENSAJE SNS AL RED TEAM: ...
```

### Verificar en MLflow

- Alias **`production`** apunta a la misma versión aprobada
- Tag `deployment_stage=production`
- Tag `deployed_at` con timestamp

---

## Fase 4 — Operar API en producción

### Reiniciar / recargar API

La API carga el modelo al **inicio**. Tras cambiar `@production`:

```bash
export MLFLOW_TRACKING_URI=http://localhost:5081
# Ajustar STAGE si el código usa variable de entorno para production
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

Verificar:

```bash
curl -s http://localhost:5082/model/info | jq '{version, metrics, params}'
curl -s http://localhost:5082/health | jq .
```

Detalle API: [Stage 8 — API Serving](stage_8_api_serving.md)

---

## Fase 5 — Red Team post-deploy

Tras deploy, el DAG notifica al Red Team. Ejecutar pruebas de evasión:

```bash
export ANTHROPIC_AUTH_TOKEN=<token>
python -m src.mlsec.red_team.red_team_crew
```

Reportes en `reports/red_team_report_*.md`. Guía: [Red Team Guide](red_team.md)

---

## Rollback

No hay alias `archived` automatizado en el MVP. Rollback manual:

1. Identificar versión production anterior en MLflow (historial de versiones)
2. Re-asignar alias `@production` a la versión estable
3. Tag `deployment_stage=production` en esa versión
4. Reiniciar API
5. Documentar incidente y motivo

---

## Troubleshooting

| Error | Causa | Solución |
|-------|-------|----------|
| `validate_approval` falla | Tag ≠ `approved` | Blue Team ejecuta `/model/approve` |
| No hay modelo en staging | `dag_promote_model` no ejecutado | Ejecutar Stage 5 primero |
| API 503 modelo no cargado | MLflow down o sin alias | Verificar `:5081` y alias staging/production |
| SNS no llega | ARN no configurado | Normal en dev — revisar logs Airflow |
| Métricas distintas en API vs MLflow | Modelo distinto al esperado | Verificar alias y versión en `/model/info` |

---

## Variables de entorno (deploy)

```bash
MLFLOW_TRACKING_URI=http://localhost:5081   # host
# En Docker Airflow: http://mlflow:5000
MLFLOW_MODEL_NAME=model-csic
```

---

## Roles en el deploy

| Paso | Responsable |
|------|-------------|
| Auditoría staging | Blue Team |
| Tag `approved` | Blue Team |
| Trigger `dag_deploy_prod` | MLOps |
| Verificar `@production` | MLOps |
| Reload API | MLOps |
| Red Team post-deploy | Red Team |

RACI: [Matriz RACI](raci.md)

---

## Diagrama de estados MLflow

```text
candidate ──(Blue Team)──► approved ──(dag_deploy_prod)──► production
   ▲                              │
   │                              │
   └── dag_promote_model          └── @staging alias
       @staging alias
```

---

## Páginas relacionadas

- [Stage 5 — Promote to staging](stage_5_promote.md)
- [Stage 6 — Auditoría Blue Team](stage_6_blue_team_audit.md)
- [Stage 7 — Deploy](stage_7_deploy.md)
- [Conceptos MLOps](conceptos_mlops.md)
