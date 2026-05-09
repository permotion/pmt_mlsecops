# Contexto y Motivación

---

## ¿Por qué es relevante detectar ataques web automáticamente?

Los servidores web reciben miles de requests por minuto. Revisar manualmente cada uno es imposible. Las técnicas de ataque evolucionan constantemente — SQL injection bypass, XSS polyglots, HTTP desync — y un sistema de reglas manuales se vuelve obsoleto rápido.

### Impacto de un ataque exitoso

| Tipo de ataque | Consecuencia |
|----------------|-------------|
| SQL Injection | Exfiltración de datos, compromiso de base de datos |
| XSS | Robo de sesiones, defacement, malware injection |
| Path Traversal | Lectura de archivos sensibles del servidor |
| Command Injection | Compromiso total del servidor |

La detección automática permite:
- **Escalar** a volúmenes de tráfico industrial
- **Reaccionar rápido** a nuevas técnicas de ataque
- **Reducer falsos negativos** — en seguridad, no detectar un ataque es más costoso que investigar un falso positivo

---

## El problema: modelos sin gobernanza

Un modelo puesto en producción sin proceso de ciclo de vida va a:

1. **Degradar silenciosamente** — los ataques evolucionan, el modelo no
2. **Generar más FP** — condiciones de producción (tráfico 99:1 normal:ataque) son distintas al training (41:59)
3. **No generar feedback** — nadie sabe si el modelo está fallando hasta que hay un incidente

```
Training once → Production → Model becomes stale → Attacks evolve → Incident happens
```

El problema no es entrenar un modelo. El problema es **operarlo** sin proceso.

---

## ¿Por qué CSIC 2010?

El dataset CSIC 2010 (HTTP dataset) fue publicado por la Universidad de Granada y es ampliamente utilizado en investigación académica de detección de ataques web.

| Característica | Detalle |
|----------------|---------|
| **Origen** | Universidad de Granada — Datacenter CSIC |
| **Contenido** | Requests HTTP reales capturados de una aplicación web |
| **Etiquetas** | Cada request marcado como normal o ataque (SQLi, XSS, etc.) |
| **Tamaño** | 61,065 requests |
| **Attack rate** | ~41% (facilita el entrenamiento inicial) |
| **Ventaja** | Benchmark académico reconocido — permite comparar con otros trabajos |
| **Limitación** | Dataset de 2010 — técnicas más nuevas (HTTP desync, API-specific) no están representadas |

---

## ¿Por qué detectar ataques web con ML?

| Enfoque | Ventaja | Limitación |
|---------|---------|------------|
| **Reglas manuales (WAF)** | Rápido de implementar | Se vuelve obsoleto rápido,容易被 bypass |
| **ML (nuestro enfoque)** | Se adapta a patrones, detecta variantes | Requiere proceso MLOps, necesita datos de training |
| **Firma estática** | Muy preciso para ataques conocidos | No detecta ataques nuevos (0-day) |

Nuestro enfoque combina **ML para detección** con **MLOps para gobernanza** — el modelo se actualiza cuando el Red Team detecta gaps.

---

## Dataset: desbalance inherente

| Entorno | Ratio normal:ataque | Implicancia |
|---------|---------------------|-------------|
| **Dataset CSIC 2010** | ~59:41 | Training con ejemplos suficientes de ambas clases |
| **Producción típica** | ~99:1 | FP rate sube significativamente vs. test |

Este desbalance es la razón por la cual el **threshold calibration** es crítico — un threshold de 0.50 (default) genera muchos FP en producción.