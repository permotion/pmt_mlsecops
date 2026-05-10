# Stage 0 — Curado del Dataset

---

## Objetivo

Asegurar que el dataset de training es **seguro, legal, y de calidad** antes de usarlo en el pipeline.

---

## Procesos de curado

### 1. Remoción de PII

| Tipo | Ejemplo | Acción |
|------|---------|--------|
| IPs | `172.16.0.45` | Hash |
| Emails | `user@example.com` | Mask |
| Sessions | `JSESSIONID=...` | Remover |
| Teléfonos | `+5491123456789` | Remover |

### 2. Validación de estructura

Verificar columnas esperadas, labels válidos, filas duplicadas.

### 3. Deduplicación

Remover requests exactos duplicados.

### 4. Análisis de class balance

Reportar distribución normal/ataque.

### 5. Label leakage check

Verificar que requests normales no tengan patrones de ataque.

---

## Responsable

**MLOps** (curación)

---

## Input / Output

| Campo | Detalle |
|-------|---------|
| Input | `data/raw/csic2010/csic_database.csv` |
| Output | `data/curated/csic2010/csic_database_curated.csv` + `curation_report.md` |