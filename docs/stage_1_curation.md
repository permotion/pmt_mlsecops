# Stage 1 — Curado del Dataset

---

## Objetivo

Escanear el dataset CSIC 2010 en busca de **PII (Personally Identifiable Information)** y **referencias a empresas/organizaciones** específicas antes de usarlo en training de ML. Generar un reporte de hallazgos para revisión humana.

**Este DAG solo escanea y reporta — no modifica los datos.**

---

## ¿Por qué es necesario?

Antes de usar un dataset para training de ML en contexto de seguridad, es fundamental verificar que no contenga:

- **PII**: Datos personales que podrían identificar personas reales (session tokens, emails, teléfonos, IPs)
- **Datos de empresas**: Información confidencial de organizaciones externas
- **Sesgos no deseados**: Datos que podrían generar discriminación o fuite de información privada

Este paso protege la privacidad, evita leakage de información sensible, y documenta el estado del dataset antes de cualquier procesamiento.

---

## ¿Qué busca este DAG?

### PII

| Tipo | Descripción | Columnas escaneadas |
|------|-------------|---------------------|
| Session tokens | `JSESSIONID=...` | cookie |
| Teléfonos | Números de teléfono en formato internacional | content, URL |
| Emails | Direcciones de email | content, URL, User-Agent |
| IPs | Direcciones IPv4 | host, URL |

### Empresas y Organizaciones

| Empresa/Organización | Por qué se busca |
|---------------------|------------------|
| Hackademy | Empresa de training de seguridad |
| Ekoparty | Conferencia de seguridad |
| CSIC | Consejo Superior de Investigaciones Científicas |
| Universidad de Granada | Institución académica del dataset |

---

## Pipeline del DAG

```
verify_input → scan_pii → generate_report
```

### Task 1: verify_input

Verifica que el CSV crudo existe en la ruta esperada.

```python
def check_input_exists():
    if not DATA_INPUT.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {DATA_INPUT}")
    size_mb = DATA_INPUT.stat().st_size / 1024 / 1024
    print(f"Input encontrado: {DATA_INPUT} ({size_mb:.1f} MB)")
```

**Input:** `data/raw/csic2010/csic_database.csv`

### Task 2: scan_pii

Ejecuta el script `curate_dataset.py` que:

1. Carga el CSV en pandas
2. Para cada tipo de PII, busca el pattern regex en las columnas especificadas
3. Para cada empresa, busca el texto (case-insensitive) en todas las columnas
4. Cuenta ocurrencias y guarda hasta 3 ejemplos
5. Genera el `curation_report.md`

```python
PII_PATTERNS = {
    "session_token": {
        "columns": ["cookie"],
        "pattern": r"JSESSIONID=[A-Za-z0-9\-_]+",
        "description": "Session tokens JSESSIONID",
    },
    "phone": {
        "columns": ["content", "URL"],
        "pattern": r"\+?\d{1,4}[-\s]?\(?\d{1,4}\)?[-\s]?\d{1,4}[-\s]?\d{1,9}",
        "description": "Números de teléfono",
    },
    "email": {
        "columns": ["content", "URL", "User-Agent"],
        "pattern": r"[\w\.-]+@[\w\.-]+\.\w+",
        "description": "Direcciones de email",
    },
    "ip_address": {
        "columns": ["host", "URL"],
        "pattern": r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
        "description": "Direcciones IP",
    },
}
```

```python
COMPANY_PATTERNS = [
    "hackademy",
    "ekoparty",
    "csic",
    "consejo superior de investigaciones científicas",
    "universidad de granada",
]
```

**Input:** CSV crudo
**Output:** `curation_report.md`

### Task 3: generate_report

Lee el reporte generado y lo imprime en los logs de Airflow para revisión.

```python
def show_report():
    content = REPORT_OUTPUT.read_text()
    print(f"\n{'='*60}")
    print("CURATION REPORT")
    print('='*60)
    print(content)
```

---

## Output del DAG

| Campo | Detalle |
|-------|---------|
| Report | `data/curated/csic2010/curation_report.md` |

### Estructura del curation_report.md

El reporte generado tiene la siguiente estructura:

```
# Dataset Curation Report — CSIC 2010

**Fecha:** YYYY-MM-DD HH:MM:SS
**Dataset:** data/raw/csic2010/csic_database.csv
**Total de filas:** 61,065

---

## PII Encontrado

| Tipo de PII | Occurrencias | Estado |
|-------------|--------------|--------|
| Session tokens JSESSIONID | 61,065 | ✅ ENCONTRADO |
| Teléfonos | X | ⚠️ POSIBLE FALSO POSITIVO |
| Emails | 0 | ❌ NO ENCONTRADO |
| IPs | 0 | ❌ NO ENCONTRADO |

### Detalle de hallazgos
[Ejemplos de cada tipo encontrado]

---

## Empresas y Organizaciones Buscadas

| Empresa/Organización | Estado | Columnas |
|---------------------|--------|----------|
| hackademy | ✅ ENCONTRADO | host |
| ekoparty | ✅ ENCONTRADO | host |

---

## Balance de Clases

| Clase | Cantidad | Porcentaje |
|-------|----------|------------|
| Normal | 36,000 | 59.0% |
| Ataque | 25,065 | 41.0% |

---

## Conclusiones

[Análisis de hallazgos y acciones recomendadas]

---

## Sign-off

- [ ] MLOps (revisión de hallazgos completada)
- [ ] Decisión: ¿El dataset requiere sanitización adicional?
```

### Notas sobre detección de PII

- **Session tokens (JSESSIONID):** Se encontraron en todos los registros. Son parte del dataset original y representan sesiones sintéticas generadas para el dataset. No representan PII real.

- **Teléfonos en content:** Pueden aparecer números de teléfono que son parte de payloads de ataque (datos de prueba en inyecciones SQL). Estos son **falsos positivos** — no son PII real. El script no diferencia automáticamente entre teléfono en payload vs. teléfono real.

- **Búsqueda de empresas:** La búsqueda es **case-insensitive** (`hackademy`, `HACKADEMY`, `Hackademy` son encontrados).

### Estados en el reporte

| Estado | Significado |
|--------|-------------|
| ✅ ENCONTRADO | Se encontró evidencia en el dataset |
| ❌ NO ENCONTRADO | No hay evidencia en el dataset |
| ⚠️ POSIBLE FALSO POSITIVO | Se encontró pero requiere revisión manual |

### Manejo de errores

Si el script falla:

1. **Archivo no encontrado:** El DAG falla en `verify_input` con `FileNotFoundError`
2. **Error en scan_pii:** El DAG falla en `scan_pii` — revisar logs de Airflow
3. **Reporte no generado:** `generate_report` falla si no existe el archivo

Para re-ejecutar después de una falla: ir a Airflow UI → dag_curate_dataset → Clear → Play

---

## Ejecución desde Airflow UI

```bash
http://localhost:5080 → dag_curate_dataset → Play
```

**Trigger:** Manual (schedule=None)

El DAG no tiene dependencias de otros DAGs. Puede ejecutarse en cualquier momento para re-escanear el dataset.

---

## Ejecución manual

```bash
# Desde el directorio raíz del proyecto
cd /path/al/proyecto
PYTHONPATH=. python3 -m src.mlsec.data.curate_dataset \
    --input data/raw/csic2010/csic_database.csv \
    --report data/curated/csic2010/curation_report.md
```

---

## Deuda técnica pendiente

### 1. Hostname sintético no documentado

El hostname `plataformahackademy.ekoparty.org` que aparece en el dataset es un placeholder sintético creado para generar el dataset. No representa datos reales de Hackademy ni Ekoparty.

**Pendiente:** El script debería detectar este tipo de hostname sintético y aclararlo en el reporte.

### 2. Números de teléfono en payloads

Los números de teléfono encontrados en el campo `content` son parte de payloads de ataque (SQL injection con datos de prueba). El script actualmente los cuenta como "PII encontrado", lo cual es un falso positivo.

**Pendiente:** Diferenciar entre teléfonos reales (PII) y teléfonos dentro de payloads de ataque (no son PII).

### 3. Búsqueda case-insensitive para empresas

La búsqueda de empresas ya es case-insensitive en el script, pero el reporte no lo detalla claramente.

**Pendiente:** Actualizar el formato del reporte para indicar que la búsqueda fue case-insensitive.

---

## Archivos del stage

| Archivo | Descripción |
|---------|-------------|
| `dags/dag_curate_dataset.py` | DAG de Airflow |
| `src/mlsec/data/curate_dataset.py` | Script de escaneo |
| `docs/stage_1_curation.md` | Esta documentación |

---

## Responsable

**MLOps** — curación de datos y revisión de hallazgos del reporte