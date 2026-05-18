# Dataset: CSIC 2010

---

## Descripción

El dataset CSIC 2010 fue desarrollado en el **Instituto de Seguridad de la Información** del CSIC (Consejo Superior de Investigaciones Científicas de España). Contiene miles de peticiones web generadas automáticamente dirigidas a una aplicación web de e-commerce.

| Característica | Valor |
|----------------|-------|
| **Origen** | Instituto de Seguridad de la Información — CSIC, España |
| **Año** | 2010 |
| **Peticiones normales** | ~36,000 |
| **Peticiones anómalas** | ~25,000 |
| **Total** | ~61,065 requests |
| **Attack rate** | ~41% |

### ¿Por qué un dataset balanceado?

Elegimos este dataset porque tiene ~41% de ataques, a diferencia de producción real que tiene ~1%. Ventajas de esta característica:

| Ventaja | Descripción |
|---------|-------------|
| **Training estable** | El modelo recibe suficientes ejemplos de ambas clases, evitando bias hacia la clase mayoritaria |
| **Métricas de training significativas** | Recall y Precision son representativos durante el entrenamiento |
| **Convergencia más rápida** | LightGBM converge más rápido con datos balanceados |
| **Baseline confiable** | Permite establecer métricas base antes de ajustar para producción desbalanceada |

**Nota:** En producción el ratio es ~99:1 (normal:ataque), por eso recalibramos el threshold y monitoreamos FP rate con el Red Team Agent.

### División del dataset

El dataset está dividido en tres bloques:
- **Conjunto de entrenamiento normal** — peticiones legítimas para training
- **Conjunto de prueba normal** — peticiones legítimas para evaluación
- **Conjunto de prueba anómalo** — peticiones de ataque para evaluación

---

## Tipos de ataques cubiertos

El dataset incluye los siguientes tipos de ataque:

| Categoría | Descripción |
|-----------|-------------|
| **SQL Injection** | Inyección de código SQL en parámetros |
| **XSS** | Cross-Site Scripting |
| **Buffer Overflow** | Desbordamiento de buffer |
| **CRLF Injection** | Inyección de caracteres CRLF en headers |
| **Parameter Tampering** | Manipulación de parámetros de request |
| **Path Traversal** | Acceso a archivos del sistema |
| **Command Injection** | Ejecución de comandos |

---

## Estructura del dataset

```
data/raw/csic2010/
├── csic_database.csv
├── README.md
└── SHA256.txt
```

### Columnas del CSV

| Columna | Descripción |
|---------|-------------|
| `request` | HTTP request completo como string |
| `method` | GET o POST |
| `url` | URL del request |
| `label` | 0=normal, 1=ataque |

---

## Limitaciones conocidas

El dataset CSIC 2010 es ampliamente usado pero también tiene limitaciones:

| Limitación | Impacto |
|------------|---------|
| **Falta de variedad** | Es criticado por su falta de variedad, lo que lleva a muchos investigadores a crear o combinar datasets para mayor confiabilidad |
| **No representa ataques modernos** | No representa adecuadamente los vectores de ataque más nuevos orientados a tecnologías web actuales (API-specific attacks, HTTP desync) |
| **Dataset de 2010** | Las técnicas de ataque han evolucionado desde entonces |

**Mitigación:** El Red Team Agent busca payloads frescos de fuentes públicas (Exploit-DB, CVE feeds) para detectar gaps del modelo frente a ataques actuales.
