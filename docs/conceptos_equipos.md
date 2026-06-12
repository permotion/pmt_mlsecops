# Conceptos Clave — Blue Team y Red Team

---

## Por qué equipos de seguridad en un pipeline ML

Un modelo de detección de ataques HTTP no vive aislado: en producción enfrenta tráfico distinto al training (99:1 normal:ataque vs. 59:41 en CSIC 2010), payloads evasivos no vistos en 2010, y riesgo de falsos positivos que bloquean tráfico legítimo.

**Blue Team** y **Red Team** cierran ese gap entre "modelo entrenado" y "modelo operado con seguridad".

---

## Blue Team

### En seguridad clásica

Detecta, responde y defiende sistemas en producción.

### En PMT MLSecOps

| Fase | Stage | Qué hace |
|------|-------|----------|
| **Pre-producción** | 6 | Evalúa candidato en `@staging`: DAST, FP, latencia |
| **Aprobación** | 6 | `POST /model/approve` → tag `approved` |
| **Operación** | 9 | Monitorea FP rate, recall, disponibilidad API |
| **Respuesta a gaps** | 10 | Recibe FN reports del Red Team; solicita re-train |

### Human in the loop

El Blue Team es el **humano en el loop** obligatorio: ningún modelo llega a `@production` sin tag `approved`. El DAG `dag_deploy_prod` lo enforcea en código.

```text
dag_promote_model → @staging
        │
        ▼
Blue Team prueba API :5082
        │
        ├── Rechazar → quedarse en @production actual
        ├── Aprobar con ajustes → solicitar nuevo threshold / re-train
        └── Aprobar → POST /model/approve
                │
                ▼
        dag_deploy_prod → @production
```

### Criterios de decisión (MVP)

| Métrica | Target |
|---------|--------|
| test_recall | ≥ 0.95 |
| test_precision | ≥ 0.75 |
| gap_recall | ≤ 0.05 |
| FP rate prod (99:1) | < 20% |
| Latencia p95 | < 500 ms |

Guía operativa: [Blue Team Guide](blue_team.md) · Stage: [Stage 6 — Auditoría](stage_6_blue_team_audit.md)

---

## Red Team

### En seguridad clásica

Simula ataques para encontrar debilidades antes que un adversario real.

### En PMT MLSecOps

| Actividad | Descripción |
|-----------|-------------|
| Recolectar payloads frescos | Fuentes públicas (PayloadsAllTheThings) |
| Probar evasión | `POST /predict/http` contra API en producción |
| Reportar FN | Markdown en `reports/red_team_report_*.md` |
| Alertar | Si detection rate < 85% → Blue Team → MLOps |

### Red Team automatizado (CrewAI)

Dos agentes orquestados secuencialmente:

| Agente | Rol | Herramienta |
|--------|-----|-------------|
| **PayloadHunter** | Extrae payloads SQLi, XSS, Path Traversal desde fuentes públicas (ej. GitHub PayloadsAllTheThings) | `ScrapeWebsiteTool` |
| **AttackSimulator** | Dispara payloads contra la API en producción y genera reportes en Markdown consolidados | `APISimulatorTool` |

```bash
export ANTHROPIC_AUTH_TOKEN=<token>
python -m src.mlsec.red_team.red_team_crew
```

**Nota:** la ejecución es **bajo demanda** (no hay DAG cada 6 h en el repo actual). Se dispara tras deploy o manualmente.

Guía operativa: [Red Team Guide](red_team.md) · Stage: [Stage 10 — Red Team](stage_10_red_team.md)

---

## Integración Blue Team ↔ Red Team ↔ MLOps

```text
                    ┌─────────────┐
                    │   MLOps     │
                    │ Stages 0–5  │
                    └──────┬──────┘
                           │ @staging
                           ▼
                    ┌─────────────┐
                    │ Blue Team   │ Stage 6: approve
                    └──────┬──────┘
                           │ @production
                           ▼
                    ┌─────────────┐
         ┌─────────│  API :5082  │─────────┐
         │         └─────────────┘         │
         ▼                                 ▼
  ┌─────────────┐                  ┌─────────────┐
  │ Blue Team   │ Stage 9          │ Red Team    │ Stage 10
  │ Monitoreo   │ FP, latencia     │ CrewAI      │ FN reports
  └──────┬──────┘                  └──────┬──────┘
         │                                │
         │    detection_rate < 85%        │
         └────────────┬───────────────────┘
                      ▼
              Solicitar re-training
                      │
                      ▼
                 MLOps (Stage 2–5)
```

---

## Thresholds de alerta operativos

| Métrica | Threshold | Origen | Acción |
|---------|-----------|--------|--------|
| detection_rate | < 85% | Red Team | Alert → Blue Team → re-train |
| FP rate | > 20% | Blue Team (Stage 9) | Revisar threshold / features |
| fn_count | ≥ 3 por ciclo | Red Team | Escalar revisión |
| Latencia p95 | > 500 ms | Blue Team | Escalar infra |

---

## Matriz RACI (resumen)

| Actividad | MLOps | Data Science | Blue Team | Red Team |
|-----------|-------|--------------|-----------|----------|
| Feature engineering | ✅ | colabora | — | — |
| Entrenamiento (DAG) | ✅ | — | — | — |
| Promote staging | ✅ | — | — | — |
| Aprobar modelo | — | — | ✅ | — |
| Deploy production | ✅ | — | valida | — |
| Monitoreo prod | apoya | — | ✅ | — |
| Pruebas evasión | — | — | recibe | ✅ |
| Re-training | ✅ | colabora | solicita | informa |

Detalle: [Matriz RACI](raci.md)

---

## Páginas relacionadas

- [Conceptos MLOps y gobernanza](conceptos_mlops.md)
- [Threshold calibration](conceptos_threshold.md)
- [Arquitectura — Roles](arquitectura.md#roles-y-responsabilidades)
