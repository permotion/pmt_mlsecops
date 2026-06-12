# Red Team — Guía

Guía operativa para pruebas de evasión contra el modelo en producción y generación de FN reports.

**Stage:** [10 — Red Team](stage_10_red_team.md)  
**Conceptos:** [Blue Team y Red Team](conceptos_equipos.md)

---

## Misión del Red Team

Encontrar **falsos negativos** (ataques que el modelo clasifica como normales) usando payloads frescos no necesariamente presentes en CSIC 2010, y alimentar el feedback loop hacia Blue Team y MLOps.

---

## Arquitectura: Macro-GAN Semántica (Adversarial ML)

El trabajo del Red Team automatizado funciona bajo una arquitectura **Macro-GAN Semántica**, impulsada por Agentes LLM que simulan una Red Generativa Antagónica:
- **Agente 1 (Payload Hunter / Latent Space):** Inicializa el espacio latente de la GAN buscando y extrayendo Inteligencia de Amenazas (OSINT) real desde repositorios públicos.
- **Agente 2 (Attack Simulator / Generator):** Actúa como el Generador. Dispara los payloads y, si son bloqueados, **muta iterativamente** el ataque (URL encoding, ofuscación) hasta lograr evadir las defensas.
- **Discriminador (WAF / XGBoost):** El modelo en producción que intenta atrapar los ataques (devuelve 403 o 200).
- **Feedback Loop:** Los Falsos Negativos exitosos se documentan para re-entrenar al Discriminador en el siguiente ciclo.

---

## Cuándo ejecutar

| Trigger | Descripción |
|---------|-------------|
| **Post-deploy** | Tras `dag_deploy_prod` (alerta SNS / acuerdo con MLOps) |
| **Programado** | Cadencia acordada con el equipo (ej. semanal) |
| **Ad-hoc** | Tras incidente, nuevo vector de ataque o cambio de features |
| **Pre-auditoría** | Opcional: validar candidato en staging antes de Blue Team |

**Nota:** no hay DAG Airflow cada 6 h en el repo — la ejecución es **manual o externamente schedulada**.

---

## Prerrequisitos

| Requisito | Comando / URL |
|-----------|---------------|
| API en `:5082` con modelo cargado | `curl http://localhost:5082/health` |
| MLflow con `@production` (o `@staging` para prueba) | http://localhost:5081 |
| Token LLM | `export ANTHROPIC_AUTH_TOKEN=...` |
| Dependencias | `pip install -r requirements-ml.txt` |

Opcional:

```bash
export ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
export ANTHROPIC_MODEL=MiniMax-M2.7
```

---

## Red Team automatizado (CrewAI)

### Arquitectura

```text
PayloadHunter                    AttackSimulator
     │                                  │
     │ ScrapeWebsiteTool                │ APISimulatorTool
     ▼                                  ▼
PayloadsAllTheThings            POST /predict/http :5082
(SQLi, XSS, Path Traversal)              │
                                         ▼
                              reports/red_team_report_*.md
```

### Agentes

| Agente | Rol | Output |
|--------|-----|--------|
| **PayloadHunter** | Extrae payloads HTTP de fuentes públicas | JSON estructurado de payloads |
| **AttackSimulator** | Dispara payloads contra la API | Reporte Markdown |

**Fuentes reales en código** (`red_team_crew.py`):

- PayloadsAllTheThings — Classic SQLi
- PayloadsAllTheThings — Directory Traversal
- PayloadsAllTheThings — XSS

### Ejecución

```bash
cd PMT_MLSecOps
export ANTHROPIC_AUTH_TOKEN=<tu-token>
python -m src.mlsec.red_team.red_team_crew
```

Salida en consola + archivo:

```
reports/red_team_report_YYYYMMDD_HHMMSS.md
```

---

## Cómo funciona APISimulatorTool

Para cada payload:

1. Construye request HTTP sintético (GET en URL o POST en body según `target_field`)
2. Envía a `http://localhost:5082/predict/http`
3. Clasifica:
   - `prediction=1` → **BLOQUEADO**
   - `prediction=0` → **EVADIÓ (FN)**

Código: `src/mlsec/red_team/attack_simulator_tool.py`

---

## Métricas del ciclo

| Métrica | Fórmula | Target |
|---------|---------|--------|
| **detection_rate** | bloqueados / total payloads | ≥ **85%** |
| **fn_count** | payloads con prediction=0 | < **3** por ciclo (alerta) |
| **evasion_rate** | 1 - detection_rate | ≤ 15% |

### Acciones si no cumple

| Condición | Acción |
|-----------|--------|
| detection_rate < 85% | Reporte a Blue Team → evaluar re-train |
| fn_count ≥ 3 | Escalar revisión manual de payloads FN |
| FN en categoría crítica (RCE, SQLi) | Prioridad alta para MLOps |

---

## Formato FN Report

Ejemplo de estructura generada por AttackSimulator:

```markdown
# Informe Red Team — MLSecOps

## Resumen
- Total payloads testeados: N
- Bloqueados (TP): N
- Evadidos (FN): N
- Detection rate: X%

## Falsos negativos (detalle)
| attack_type | payload | source | prediction | probability |
|-------------|---------|--------|------------|-------------|
| SQL Injection | ' OR '1'='1 | PayloadsAllTheThings | 0 | 0.12 |
...

## Recomendaciones
- ...
```

Ejemplo real: `reports/red_team_report_20260529_144649.md`

---

## Integración con Blue Team y MLOps

```text
dag_deploy_prod
      │
      ▼ notify_red_team (log/SNS)
Red Team ejecuta red_team_crew.py
      │
      ▼
reports/*.md
      │
      ▼
Blue Team evalúa (Stage 9)
      │
      ├── detection_rate ≥ 85% → OK
      └── detection_rate < 85% → solicitar re-train
              │
              ▼
      MLOps: dag_preprocess → dag_train → dag_promote_model
              │
              ▼
      Blue Team re-audita (Stage 6)
```

---

## Hands-on: pruebas manuales (sin CrewAI)

Útil para debug rápido sin LLM.

### SQL Injection

```bash
curl -s -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "url": "http://localhost/app?id=1'\'' OR '\''1'\''='\''1",
    "content_length": 0,
    "body": ""
  }'
```

### XSS

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

### Path Traversal

```bash
curl -s -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "url": "http://localhost/file?path=../../../../etc/passwd",
    "content_length": 0,
    "body": ""
  }'
```

Interpretar respuesta:

```json
{
  "prediction": 1,
  "probability": 0.87,
  "threshold": 0.2502,
  "model_version": "5",
  "latency_ms": 2.1
}
```

- `prediction: 0` con payload claramente malicioso → **FN** (documentar)
- `prediction: 1` → detectado correctamente

---

## Fuentes de payloads (referencia)

| Fuente | Uso en proyecto | Categorías |
|--------|-----------------|------------|
| **PayloadsAllTheThings** (GitHub) | ✅ Usado por PayloadHunter | SQLi, XSS, Path Traversal |
| Exploit-DB | Referencia futura | RCE, LFI |
| NVD / CVE feeds | Referencia futura | Vulnerabilidades recientes |
| OWASP Cheat Sheets | Referencia futura | Patrones de ataque |

El MVP automatizado scrapea **solo PayloadsAllTheThings** (3 archivos `.txt` en raw GitHub).

---

## Limitaciones del MVP

| Limitación | Impacto |
|------------|---------|
| Payloads de 2010-era en training | Modelo puede fallar en técnicas modernas |
| API localhost, no WAF real | Integración prod requiere proxy/gateway |
| LLM externo requerido | CrewAI necesita `ANTHROPIC_AUTH_TOKEN` |
| Sin scheduler integrado | Ejecución manual o cron externo |
| Requests sintéticos | `target_field` simplifica URL vs body |

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `Connection refused :5082` | Levantar `model_serving` |
| `ANTHROPIC_AUTH_TOKEN no configurada` | Exportar token |
| Reporte vacío / alucinado | Verificar que AttackSimulator invoque APISimulatorTool |
| Todos FN o todos TP | Verificar threshold y alias del modelo en `/model/info` |
| Timeout en API | Aumentar timeout en `attack_simulator_tool.py` (default 5s) |

---

## RACI resumido

| Actividad | Red Team |
|-----------|----------|
| Ejecutar pruebas evasión | **Responsible** |
| Generar FN report | **Responsible** |
| Alertar si detection < 85% | **Responsible** |
| Decidir re-train | Blue Team (Accountable) |
| Re-entrenar modelo | MLOps (Responsible) |

Detalle: [Matriz RACI](raci.md)

---

## Páginas relacionadas

- [Blue Team Guide](blue_team.md)
- [Manual de Aprobación y Deploy](README_deploy.md)
- [Stage 10 — Red Team](stage_10_red_team.md)
- [API README](../src/mlsec/api/README.md)
