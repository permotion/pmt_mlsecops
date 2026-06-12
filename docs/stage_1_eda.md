# Stage 1 — Exploración de Datos (EDA)

---

## Objetivo

Analizar el dataset CSIC 2010 **antes de escribir código de producción**: entender estructura, calidad, distribución de clases y dónde viven los patrones de ataque.

**Responsable:** Data Science / Blue Team  
**Componente:** Notebook manual (no hay DAG)

---

## Notebook

| | |
|---|---|
| **Archivo** | `notebooks/eda/csic2010_eda.ipynb` |
| **Input** | `data/raw/csic2010/csic_database.csv` |
| **Output** | Decisiones documentadas en el notebook (no genera parquet) |

---

## Preguntas que responde el EDA

1. ¿Cuál es la estructura del dataset? (61.065 filas × 17 columnas)
2. ¿El label (`classification`) está usable? → renombrar a `label` en preprocess
3. ¿Distribución de clases? → 59% normal / 41% ataque
4. ¿Dónde viven los ataques? → GET en URL, POST en body, PUT = 100% ataques
5. ¿Columnas útiles vs. constantes? → 11 columnas descartadas
6. ¿Patrones discriminativos? → indicadores `%27`, `script`, `SELECT`, longitudes

---

## Hallazgos clave

### Distribución de métodos HTTP

| Method | Normal | Attack | % Attack |
|--------|--------|--------|----------|
| GET | 28.000 | 15.088 | 35% |
| POST | 8.000 | 9.580 | 54% |
| PUT | 0 | 397 | **100%** |

`method_is_put` es un indicador casi perfecto para los 397 ataques PUT.

### Nulos en `content`

~70% de filas sin body (requests GET). Estrategia: `content_length = 0`, no imputar con media.

### Decisiones que alimentan Stage 2

- Descartar headers constantes (`User-Agent`, `Accept`, etc.)
- One-hot de `Method` → `method_is_get/post/put`
- Indicadores de texto en URL y content (`url_has_pct27`, `content_has_script`, …)
- Ratio features (v5) tras análisis de FP — ver [Stage 2 — Preprocess](stage_2_preprocess.md)

---

## Resultados documentados

Detalle completo en [Resultados Stage 2 — EDA](results/stage_2_results.md#stage-2--eda-notbookscsic2010_edaipynb).

---

## Navegación

← [Stage 0 — Curado](stage_0_curation.md) · [Stage 2 — Preprocess](stage_2_preprocess.md) →
