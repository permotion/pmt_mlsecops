# Red Team — Guía

---

## Actividades del Red Team

| # | Actividad | Periodicidad |
|---|-----------|---------------|
| 1 | Buscar payloads frescos | Cada 6h (DAG) |
| 2 | Testar payloads contra API | Cada ciclo |
| 3 | Generar FN Report | Cada ciclo |
| 4 | Evaluar detection rate | Cada ciclo |
| 5 | Alertar si threshold superado | Cuando FN ≥ 3 |
| 6 | Análisis de gaps manuales | A demanda |

---

## Fuentes monitoreadas

| Fuente | Categorías |
|--------|------------|
| Exploit-DB | SQLi, XSS, LFI, RCE |
| PayloadAllTheThings | Polyglots, bypass techniques |
| NVD CVE Feed | Vulnerabilidades recientes |
| OWASP Cheat Sheets | Attack patterns |

---

## Threshold de alert

| Métrica | Threshold | Acción si no cumple |
|---------|-----------|---------------------|
| detection_rate | ≥ 85% | Alert a Blue Team |
| fn_count | < 3 por ciclo | Sin alert |

---

## FN Report

```markdown
# Red Team FN Report
Generado: TIMESTAMP

## Resumen
- Total payloads: N
- Detectados: N
- FN: N
- Detection rate: X%

## Falsos Negativos
(detallar cada FN: payload, source, category, prediction)
```

---

## Integración con Blue Team

```
Red Team Agent → FN Report → Blue Team → Solicitar re-training → MLOps
```

---

## Hands-on: Test manual

```bash
# SQL Injection
curl -X POST http://localhost:5082/predict \
  -H "Content-Type: application/json" \
  -d '{"request": "GET /search?id=1%27+OR+%271%27%3D%271 HTTP/1.1"}'

# XSS
curl -X POST http://localhost:5082/predict \
  -H "Content-Type: application/json" \
  -d '{"request": "GET /comment?text=<script>alert(1)</script> HTTP/1.1"}'
```