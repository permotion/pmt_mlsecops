# Stage 10 — Red Team y Feedback Loop (Macro-GAN Semántica)

---

## Objetivo

Probar el modelo en producción con **payloads mutados** dinámicamente, detectar evasiones (falsos negativos) y cerrar el ciclo de mejora con MLOps para lograr una defensa robusta en continua evolución.

**Responsable:** Red Team  
**Componente:** CrewAI (`src/mlsec/red_team/red_team_crew.py`)  
**Custom Tool:** `APISimulatorTool`

---

## Arquitectura: Macro-GAN Semántica

Hemos evolucionado desde la generación manual o las inestables redes GAN tradicionales hacia un enfoque de **Macro-GAN Semántica basada en LLMs**. El sistema orquesta dos agentes autónomos que simulan un ataque completo.

### 1. El Espacio Latente (Agent 1: Payload Hunter)
En una GAN clásica, el Generador arranca con "ruido aleatorio". En nuestra arquitectura, inicializamos el Generador con *Inteligencia de Amenazas real (OSINT)*.
* **Misión:** Navega repositorios públicos (ej. `PayloadsAllTheThings`).
* **Prueba:** Parsea heurísticamente el texto crudo y extrae las cadenas de inyección (SQLi, XSS) puras.
* **Output:** JSON estructurado con payloads base.

### 2. El Generador y Mutador (Agent 2: Attack Simulator)
Recibe el JSON base y lanza peticiones reales contra el **Discriminador** (la API del WAF en el Stage 8).
* **Feedback Loop:** Si el WAF bloquea el ataque (HTTP 403), el agente *no se rinde*. Razona por qué falló y **muta iterativamente el payload** (ej. URL encoding, ofuscación) hasta lograr un Bypass (HTTP 200).

---

## Orquestación Autónoma (CrewAI)

```text
Payload Hunter (OSINT) 
      │   Inyecta JSON (Process.sequential)
      ▼
Attack Simulator (Generator) ────► API WAF (Discriminator)
      │      (Mutación y Retry si es bloqueado)
      ▼
Reporte Markdown (reports/red_team_report_*.md)
      │
      ▼
Si hay Bypasses → Inyectar al Data Lake → Re-entrenar modelo (Stage 1)
```

**Nota:** Utilizamos `Process.sequential`. El paso de contexto (JSON) entre el Agente 1 y el Agente 2 es 100% automático, sin intervención de scripts intermediarios.

---

## Ejecución

```bash
# Requisitos: API en :5082 corriendo, token LLM configurado (ej. MiniMax/Anthropic)
export ANTHROPIC_AUTH_TOKEN=<token>
.venv/bin/python src/mlsec/red_team/red_team_crew.py
```

Output: `reports/red_team_report_YYYYMMDD_HHMMSS.md`

---

## Criterios de Feedback Loop

Si el Agente 2 logra generar ataques que producen **Falsos Negativos (Bypasses)**, el reporte alertará a MLOps. Los nuevos payloads mutados que tuvieron éxito se deben extraer e incorporar al `features_v5.parquet` original.
El pipeline de Airflow se dispara de nuevo, el XGBoost se re-entrena aprendiendo de sus propios errores, y la defensa evoluciona. Es una **carrera armamentística autónoma**.

---

## Navegación

← [Stage 9 — Monitoreo](stage_9_monitoreo.md) · [Visión general](arquitectura.md)

