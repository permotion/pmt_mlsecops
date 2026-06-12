# Stage 2 — Preprocess CSIC 2010

---

## Objetivo

Generar **features estructuradas (v5)** desde el CSV crudo del dataset CSIC 2010. El output alimenta Stage 3 (experimentos) y Stage 4 (entrenamiento automatizado).

**Este stage NO entrena modelos** — solo transforma HTTP requests en una matriz numérica.

**EDA previo:** [Stage 1 — Exploración de datos](stage_1_eda.md) (`notebooks/eda/csic2010_eda.ipynb`)

---

## Estructura del stage

```
Stage 2
└── Preprocess (script + DAG)
    ├── Input:  csic_database.csv
    ├── Script: preprocess_csic.py
    └── Output: features_v5.parquet (27 features + label)
```

---

## Parte 1: EDA — Análisis Exploratorio

### Objetivo del EDA

El EDA responde a las siguientes preguntas antes de escribir cualquier código de producción:

1. ¿Cuál es la estructura del dataset?
2. ¿El label está en formato usable?
3. ¿Cuál es la distribución de clases?
4. ¿Dónde viven los ataques (URL, content, headers)?
5. ¿Cuáles son las columnas útiles vs. constantes/redundantes?
6. ¿Qué patterns de ataque se observan?
7. ¿Qué features tienen potencial discriminativo?

### Notebook: csic2010_eda.ipynb

**Ubicación:** `notebooks/eda/csic2010_eda.ipynb`

**Dataset:** `../../data/raw/csic2010/csic_database.csv`

### Secciones del notebook

#### 0. Setup

Importa librerías y define la ruta al dataset.

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 80)

DATA_PATH = '../../data/raw/csic2010/csic_database.csv'
```

#### 1. Carga y estructura básica

Carga el CSV y muestra las primeras filas para entender la estructura.

```python
df = pd.read_csv(DATA_PATH)
print(f'Shape: {df.shape}')
df.head(3)
```

**Hallazgos esperados:**
- Shape: (61065, 17)
- Columnas: Method, User-Agent, URL, content, classification, etc.

#### 2. Descripción de columnas

Documenta cada columna y su utilidad para el modelo.

| Columna | Qué es | Útil para el modelo |
|---------|--------|---------------------|
| `Unnamed: 0` | Índice original Normal/Anomalous | No — redundante |
| `Method` | Método HTTP: GET, POST, PUT | Sí — feature categórica |
| `User-Agent` | Identificador del cliente | Probablemente no — constante |
| `host` | Host destino | No — constante (localhost:8080) |
| `cookie` | JSESSIONID | Posible — presencia/ausencia |
| `content` | Body del request | **Muy importante** — ataques POST |
| `classification` | Label: 0=normal, 1=attack | **Target** |
| `URL` | URL completa | **Muy importante** — ataques GET |

#### 3. El label

Verifica el formato del label.

```python
print('classification — valores únicos:', df['classification'].unique())
print(df['classification'].value_counts())
df = df.rename(columns={'classification': 'label'})
```

**Descubrimiento:** `classification` ya está en 0/1 — sin transformación necesaria.

#### 4. Distribución de clases

```python
counts = df['label'].value_counts().sort_index()
# Normal: 36,000 (59%)
# Attack: 25,065 (41%)
```

**Descubrimiento:** Desbalance leve — usar `class_weight='balanced'`.

#### 5. Nulos por columna

```python
nulls = df.isnull().sum().sort_values(ascending=False)
```

**Descubrimiento:**
- `content`, `lenght`, `content-type`: ~70% nulos en GETs — esperado, no es problema
- `Accept`: <1% nulos — columna constante

#### 6. Columnas constantes o de baja variación

```python
uniqueness = df.nunique().sort_values()
# Columnas con 1 solo valor (descartar):
# language, User-Agent, Pragma, Cache-Control,
# Accept, Accept-encoding, Accept-charset, content-type
```

#### 7. Feature engineering — URL

Explora patrones en la URL.

```python
# Longitud de URL
df['url_length'] = df['URL'].str.len()

# Indicadores de ataque en URL
indicators = {
    'pct27': '%27',    # Quote encoded
    'pct3c': '%3C',   # Less-than encoded
    'dashdash': '--',  # SQL comment
    'script': 'script',
    'select': 'select',
}

for name, ind in indicators.items():
    df[f'url_has_{name}'] = df['URL'].str.contains(ind, case=False, regex=False).astype(int)
```

**Correlaciones esperadas con label:**
- `url_has_pct27`: ~0.183
- `url_has_dashdash`: ~0.148
- `url_has_script`: ~0.137
- `url_has_pct3c`: ~0.124

#### 8. Feature engineering — content (body POST)

```python
# Solo requests POST tienen content
df_post = df[df['Method'] == 'POST'].copy()
df['content_length'] = df['content'].str.len().fillna(0)
```

**Descubrimiento:**
- Ataques POST tienen body 35% más largo en promedio (media 123 vs 92 chars)

#### 9. Hallazgos clave

Documenta los descubrimientos del EDA:

- **Label:** `classification` ya está en 0/1
- **Desbalance:** 59% normal / 41% ataque — leve, usar `class_weight='balanced'`
- **PUT = 100% ataques** — feature más poderosa del dataset
- **Ataques viven en URL (GET) y content (POST)**
- **URL encoding:** atacantes usan `%27` (quote), `%3C` (<) — nunca caracteres literales
- **11 columnas constantes** sin información

---

## Parte 2: Preprocess — Generación de Features

### Objetivo

Generar features estructuradas (v5) desde el CSV crudo. El output es un archivo Parquet con 27 features numéricas + label, listo para Stages 3 y 4.

### Script: preprocess_csic.py

**Ubicación:** `src/mlsec/data/preprocess_csic.py`

**Input:** `data/raw/csic2010/csic_database.csv`
**Output:** `data/processed/csic2010/features_v5.parquet`

### Features generadas (v5)

Total: **27 features** + label (23 base + 4 ratio features de análisis FP)

#### Método HTTP (3 features)

| Feature | Descripción | Tipo |
|---------|-------------|------|
| `method_is_get` | 1 si GET, 0 si no | int8 |
| `method_is_post` | 1 si POST, 0 si no | int8 |
| `method_is_put` | 1 si PUT, 0 si no | int8 |

#### URL features (11 features)

| Feature | Descripción | Tipo |
|---------|-------------|------|
| `url_length` | Longitud total de la URL | int32 |
| `url_param_count` | Cantidad de parámetros (`=` separators) | int16 |
| `url_pct_density` | Proporción de `%XX` encoding en URL | float32 |
| `url_path_depth` | Profundidad del path (`/` separadores) | int16 |
| `url_query_length` | Longitud del query string | int32 |
| `url_has_query` | 1 si la URL tiene `?` | int8 |
| `url_has_pct27` | 1 si contiene `%27` (quote) | int8 |
| `url_has_pct3c` | 1 si contiene `%3C` (less-than) | int8 |
| `url_has_dashdash` | 1 si contiene `--` (SQL comment) | int8 |
| `url_has_script` | 1 si contiene `<script` | int8 |
| `url_has_select` | 1 si contiene `select` (case-insensitive) | int8 |

#### Content features (9 features)

| Feature | Descripción | Tipo |
|---------|-------------|------|
| `content_length` | Longitud del body | int32 |
| `content_pct_density` | Proporción de `%XX` encoding en body | float32 |
| `content_param_count` | Cantidad de parámetros en POST body | int16 |
| `content_param_density` | `content_param_count / content_length` | float32 |
| `content_has_pct27` | 1 si body contiene `%27` | int8 |
| `content_has_pct3c` | 1 si body contiene `%3C` | int8 |
| `content_has_dashdash` | 1 si body contiene `--` | int8 |
| `content_has_script` | 1 si body contiene `<script` | int8 |
| `content_has_select` | 1 si body contiene `select` | int8 |

#### Label

| Feature | Descripción | Tipo |
|---------|-------------|------|
| `label` | 0=normal, 1=attack | int8 |

### Regex patterns utilizados

```python
# URL encoding
PCT27_RE = re.compile(r'%27')          # Quote (')
PCT3C_RE = re.compile(r'%3[cC]')        # Less-than (<)
DASHDASH_RE = re.compile(r'--')         # SQL comment
SCRIPT_RE = re.compile(r'<script', re.IGNORECASE)
SELECT_RE = re.compile(r'\bselect\b', re.IGNORECASE)
```

### Algoritmo de las features principales

```python
def url_param_count(url: str) -> int:
    """Cantidad de parámetros en la URL (count '=')."""
    return url.str.count("=").astype("int16")

def url_path_depth(url: str) -> int:
    """Profundidad del path (/ separadores)."""
    url_path = url.str.split("?").str[0]
    return url_path.str.count("/").astype("int16")

def url_query_length(url: str) -> int:
    """Longitud del query string."""
    url_query = url.str.split("?").str[1].fillna("")
    return url_query.str.len().astype("int32")
```

### Pipeline del DAG

```
verify_input → generate_features → verify_output
```

| Task | Descripción |
|------|-------------|
| `verify_input` | Verifica que existe `data/raw/csic2010/csic_database.csv` |
| `generate_features` | Ejecuta `preprocess_csic.py` |
| `verify_output` | Verifica que se generó `features_v4.parquet` |

### Ejecución del DAG

```bash
http://localhost:5080 → dag_preprocess → Play
```

### Ejecución manual del script

```bash
python -m src.mlsec.data.preprocess_csic \
    --input data/raw/csic2010/csic_database.csv \
    --output data/processed/csic2010/features_v4.parquet
```

---

## Output del stage

| Campo | Detalle |
|-------|---------|
| Notebook EDA | `notebooks/eda/csic2010_eda.ipynb` |
| Features | `data/processed/csic2010/features_v4.parquet` |
| Shape | (61,065 filas, 24 columnas = 23 features + label) |
| Label balance | Normal: 36,000 (59%) / Attack: 25,065 (41%) |

---

## Deuda técnica pendiente

### 1. Sin validación de duplicados

El script no detecta registros duplicados en el dataset. Esto puede afectar la división train/val/test si hay data leakage.

**Pendiente:** Agregar paso de deduplicación antes del feature engineering.

### 2. Sin feature selection

Se usan las 23 features sin evaluar si todas aportan señal o si hay redundancia.

**Pendiente:** Implementar análisis de correlación y feature importance post-training en notebook de experiments.

---

## Archivos del stage

| Archivo | Descripción |
|---------|-------------|
| `notebooks/eda/csic2010_eda.ipynb` | Notebook de análisis exploratorio |
| `src/mlsec/data/preprocess_csic.py` | Script de generación de features |
| `dags/dag_preprocess.py` | DAG de Airflow |
| `docs/stage_2_preprocess.md` | Esta documentación |
| `data/processed/csic2010/features_v5.parquet` | Output del preprocess |

---

## Responsable

**MLOps** — preprocess automatizado · **Data Science** — EDA en [Stage 1](stage_1_eda.md)

---

## Navegación

← [Stage 1 — EDA](stage_1_eda.md) · [Stage 3 — Prototipado](stage_3_experiments.md) →