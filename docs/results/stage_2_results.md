# Resultados — Stage 2: EDA + Preprocess

---

Esta sección documenta los outputs y hallazgos del Stage 2 del pipeline. Los resultados se documentan a nivel estructural — mostrando qué información genera cada stage y qué análisis es posible extraer — sin exponer datos sensibles del dataset.

---

## EDA vs Preprocessing vs Experimento

Antes de detailar los resultados, es importante entender la diferencia entre estas tres fases:

| | EDA | Preprocessing | Experimento |
|---|---|---|---|
| **Pregunta** | ¿Qué hay en los datos? | ¿Cómo transformo los datos? | ¿Por qué falla el modelo? |
| **Punto de partida** | Sin modelo | Decisiones del EDA | Modelo entrenado con resultados |
| **Output** | Conocimiento + decisiones | Features listas para training | Decisión de mejora |
| **Vive en** | `notebooks/eda/` | `src/mlsec/data/` | `notebooks/experiments/` |
| **Cambia con el tiempo** | No — es documentación estable | Solo si cambian las decisiones | Sí — itera con cada experimento |

---

## Stage 2 — EDA: `notebooks/eda/csic2010_eda.ipynb`

### Estructura del dataset

- **Shape:** 61,065 filas × 17 columnas
- **Columnas originales:** `Unnamed: 0`, `Method`, `User-Agent`, `Pragma`, `Cache-Control`, `Accept`, `Accept-encoding`, `Accept-charset`, `language`, `host`, `cookie`, `content-type`, `connection`, `lenght`, `content`, `classification`, `URL`

---

### El label

`classification` ya está en `int64` con valores `[0, 1]`. No necesita transformación. Columna renombrada a `label` para claridad.

- `Unnamed: 0` tiene el texto "Normal"/"Anomalous" — es redundante con el label, se descarta
- `0` = Normal, `1` = Attack

---

### Distribución de clases

| Clase | Registros | % |
|---|---|---|
| Normal (0) | 36,000 | 59% |
| Attack (1) | 25,065 | 41% |

**Desbalance leve** — no requiere SMOTE. Estrategia: `class_weight='balanced'`.

---

### Distribución de métodos HTTP

| Method | Normal | Attack | % Attack |
|---|---|---|---|
| GET | 28,000 | 15,088 | 35% |
| POST | 8,000 | 9,580 | 54% |
| PUT | 0 | **397** | **100%** |

**Hallazgo crítico — PUT = 100% ataques:**

Toda request PUT en el dataset es maliciosa. `method_is_put` es la feature con mayor poder discriminativo — clasifica 397 ataques con precisión perfecta con un solo bit.

**Dónde viven los ataques según el método:**

| Método | Ubicación del ataque |
|--------|---------------------|
| GET | En la `URL` (query string — SQLi, XSS) |
| POST | En `content` (body del request) |
| PUT | El método en sí es el indicador de ataque |

---

### Nulos

| Columna | Nulos | % | Causa | Estrategia |
|---|---|---|---|---|
| `content` | 43,088 | 70.56% | Requests GET no tienen body | No imputar — rellenar con `""` o `0` |
| `lenght` | 43,088 | 70.56% | Requests GET no tienen body | `content_length = 0` para GETs |
| `content-type` | 43,088 | 70.56% | Requests GET no tienen body | Descartar — constante entre no-nulos |
| `Accept` | 397 | 0.65% | Desconocida | Descartar — columna constante |

Los 43,088 nulos corresponden exactamente a los requests GET. **No es un error de calidad de datos** — es el diseño del protocolo HTTP (los GETs no tienen body).

---

### Columnas descartadas

| Columna | Razón |
|---|---|
| `Unnamed: 0` | Redundante con label |
| `User-Agent` | Constante — 1 único valor en todo el dataset |
| `Pragma` | Constante — 1 único valor |
| `Cache-Control` | Constante — 1 único valor |
| `Accept` | Constante — 1 único valor |
| `Accept-encoding` | Constante — 1 único valor |
| `Accept-charset` | Constante — 1 único valor |
| `language` | Constante — 1 único valor |
| `content-type` | Constante entre no-nulos |
| `host` | 2 valores, sin señal útil |
| `connection` | 2 valores, sin señal útil |

**Total: 11 columnas eliminadas** de 17 originales. Quedan 6 con información útil: `Method`, `cookie`, `lenght`, `content`, `URL`, `label`.

---

### Análisis de URL length

| Métrica | Normal (0) | Attack (1) |
|---------|-----------|------------|
| Media | 79.0 chars | 106.6 chars |
| Std | 59.4 chars | 91.6 chars |
| Min | 48.0 chars | 31.0 chars |
| P50 (mediana) | 58.5 chars | 64.0 chars |
| P75 | 67.0 chars | 122.0 chars |
| Máximo | 367 chars | **895 chars** |

Las distribuciones de longitud de URL se solapan entre normal y ataque — ambas concentradas en 50-100 chars. Los ataques tienen cola más larga (max 895 vs 367). La media de ataques es 35% mayor (106.6 vs 79.0).

**Conclusión:** `url_length` sola no discrimina bien, pero aporta como feature **combinada** con los indicadores de texto.

---

### Correlación de indicadores en URL con label

**Hallazgo crítico — URL encoding:**

Los caracteres especiales `'`, `"`, `<`, `>`, `;` **nunca aparecen crudos** en las URLs. Los atacantes siempre los codifican (`%27`, `%3C`, etc.) para evadir filtros. El feature engineering debe buscar las versiones **percent-encoded**, no los literales.

| Indicador | Significado | Correlación con label |
|---|---|---|
| `url_has_pct27` | `%27` = `'` URL-encoded | **0.183** |
| `url_has_dashdash` | `--` = comentario SQL | **0.148** |
| `url_has_script` | keyword XSS | **0.137** |
| `url_has_pct3c` | `%3C` = `<` URL-encoded | **0.124** |
| `url_has_select` | keyword SQL SELECT | 0.050 |
| `url_has_union` | keyword SQL UNION | ~0.000 — descartar |
| `'`, `"`, `<`, `>`, `;` crudos | Caracteres literales | NaN — nunca aparecen |

---

### Correlación de indicadores en content con label

| Indicador | Significado | Correlación con label |
|---|---|---|
| `content_has_pct27` | `%27` = `'` URL-encoded | **0.183** |
| `content_has_dashdash` | `--` = comentario SQL | **0.148** |
| `content_has_script` | keyword XSS | **0.126** |
| `content_has_pct3c` | `%3C` = `<` URL-encoded | **0.124** |
| `content_has_select` | keyword SQL SELECT | 0.048 |

**Análisis:** Los indicadores en content tienen correlaciones similares a los de URL. `%27` y `--` son los más correlacionados, confirmando que los ataques usan las mismas técnicas tanto en GET (URL) como en POST (content).

### Análisis del content (body POST)

| Métrica | Normal | Attack |
|---|---|---|
| Requests POST totales | 8,000 | 9,580 |
| Content length — media (todos los registros) | 20.3 chars | 48.6 chars |
| Content length — máximo (todos los registros) | 307 chars | **836 chars** |

**Nota:** `content_length` se calculó con `fillna(0)` para todos los registros (incluyendo GETs que no tienen body). Por eso la media global es baja — la mayoría de los registros son GETs con `content_length=0`.

Los ataques tienen body más largo y cola más pesada (max 836 vs 307). `content_length` es una feature discriminativa para requests POST.

---

### Decisiones de preprocessing

| Decisión | Detalle |
|---|---|
| Desbalance | `class_weight='balanced'` — no SMOTE |
| Nulos en content/lenght | `content_length = 0` para GETs — no NaN |
| Encoding de Method | One-hot: `method_is_get`, `method_is_post`, `method_is_put` |
| Indicadores de texto | Percent-encoded (`%27`, `%3C`) — no chars literales |
| Normalización | Solo features continuas: `url_length`, `content_length` |
| Features binarias | Sin normalizar — ya están en 0/1 |

---

### Features finales — Modelo A

| Feature | Fuente | Tipo | Importancia |
|---|---|---|---|
| `method_is_put` | `Method` | Binaria | ⭐⭐⭐ — 100% ataques |
| `method_is_post` | `Method` | Binaria | ⭐⭐ — tasa 54% ataque |
| `method_is_get` | `Method` | Binaria | ⭐ — referencia |
| `url_has_pct27` | `URL` | Binaria | ⭐⭐ — corr 0.183 |
| `url_has_dashdash` | `URL` | Binaria | ⭐⭐ — corr 0.148 |
| `url_has_script` | `URL` | Binaria | ⭐⭐ — corr 0.137 |
| `url_has_pct3c` | `URL` | Binaria | ⭐⭐ — corr 0.124 |
| `url_has_select` | `URL` | Binaria | ⭐ — corr 0.050 |
| `url_length` | `URL` | Numérica | ⭐ — útil combinada |
| `content_length` | `content` | Numérica | ⭐⭐ — ataques POST más largos |
| `content_has_*` | `content` | Binaria | Mismos indicadores que URL |

---

## Stage 2 — Preprocess: `src/mlsec/data/preprocess_csic.py`

### Output: `features_v4.parquet`

El script genera 23 features estructuradas desde el CSV crudo.

### Features generadas

**Método HTTP (3 features):**

| Feature | Descripción |
|---------|-------------|
| `method_is_get` | 1 si GET, 0 si no |
| `method_is_post` | 1 si POST, 0 si no |
| `method_is_put` | 1 si PUT, 0 si no |

**URL features (11 features):**

| Feature | Descripción |
|---------|-------------|
| `url_length` | Longitud total de la URL |
| `url_param_count` | Cantidad de parámetros (`=` separators) |
| `url_pct_density` | Proporción de `%XX` encoding |
| `url_path_depth` | Profundidad del path |
| `url_query_length` | Longitud del query string |
| `url_has_query` | 1 si la URL tiene `?` |
| `url_has_pct27` | 1 si contiene `%27` (quote) |
| `url_has_pct3c` | 1 si contiene `%3C` (less-than) |
| `url_has_dashdash` | 1 si contiene `--` (SQL comment) |
| `url_has_script` | 1 si contiene `<script` |
| `url_has_select` | 1 si contiene `select` |

**Content features (9 features):**

| Feature | Descripción |
|---------|-------------|
| `content_length` | Longitud del body |
| `content_pct_density` | Proporción de `%XX` encoding |
| `content_param_count` | Cantidad de parámetros en POST |
| `content_param_density` | `content_param_count / content_length` |
| `content_has_pct27` | 1 si body contiene `%27` |
| `content_has_pct3c` | 1 si body contiene `%3C` |
| `content_has_dashdash` | 1 si body contiene `--` |
| `content_has_script` | 1 si body contiene `<script` |
| `content_has_select` | 1 si body contiene `select` |

**Label:**

| Feature | Descripción |
|---------|-------------|
| `label` | 0=normal, 1=attack |

---

## Archivos generados por el stage

```
notebooks/eda/
└── csic2010_eda.ipynb   ← análisis exploratorio (sin archivos de output)

data/processed/csic2010/
└── features_v4.parquet   ← output del preprocess (61,065 filas × 24 columnas = 23 features + label)

data/curated/csic2010/
└── curation_report.md   ← output del stage 1
```

---

## Próximos pasos

| Stage | Status | Output |
|-------|--------|--------|
| Stage 1 (Curation) | ✅ Completado | `curation_report.md` |
| Stage 2 (EDA) | ✅ Completado | Hallazgos en notebook |
| Stage 2 (Preprocess) | ✅ Completado | `features_v5.parquet` (27 features) |
| Stage 3 (Train) | Pendiente | Modelo en MLflow |

---

## Notas sobre privacidad

Los resultados documentados en esta página son **schematics y análisis** — no contienen datos reales del dataset. Los números mostrados (61,065 filas, 59/41, etc.) son metadatos públicos del dataset CSIC 2010 disponibles en la documentación de la institución.

---

## Responsable

**MLOps** — análisis exploratorio y generación de features para training