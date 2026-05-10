# Conceptos Clave — Blue Team y Red Team

---

## Blue Team

### Función en seguridad clásica

Detecta y responde a ataques en producción.

### Función en este pipeline ML

- Evalúa si un modelo candidato está listo para producción
- Monitorea FP rate en producción
- Decide promoción/rechazo
- Solicita re-training cuando detecta gaps

### Man in the loop

El Blue Team es el "man in the loop" — antes de que un modelo llegue a producción, un humano lo evalúa.

---

## Red Team

### Función en seguridad clásica

Simula ataques para encontrar debilidades.

### Función en este pipeline ML

- Busca payloads frescos en fuentes públicas (Exploit-DB, CVE feeds)
- Testa contra la API
- Reporta falsos negativos (gaps del modelo)

### Canary

El Red Team Agent actúa como **canary** — detecta gaps antes de que se conviertan en incidentes.

---

## Integración Blue Team + Red Team

```
Red Team Agent                    Blue Team
      │                             │
      │─ FN Report ────────────────▶│
      │─ Alert si threshold ───────▶│
      │                             │─ Solicitar re-training ──▶ MLOps
      │                             │
      ◀─── Feedback ─────────────────│
```

---

## Thresholds de alert

| Métrica | Threshold | Acción |
|---------|-----------|--------|
| Detection rate | < 85% | Alert + solicitar re-training |
| FP count | ≥ 3 por ciclo | Alert a Blue Team |