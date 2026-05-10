# Dataset: CSIC 2010

---

## Descripción

El dataset CSIC 2010 (HTTP Dataset) fue publicado por la Universidad de Granada y contiene requests HTTP capturados de una aplicación web real del datacenter del CSIC.

| Característica | Valor |
|---------------|-------|
| **Origen** | Universidad de Granada — Datacenter CSIC |
| **Año** | 2010 |
| **Total de requests** | 61,065 |
| **Attack rate** | ~41% |
| **Categorías** | SQL Injection, XSS, Path Traversal, Command Injection |

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

## Preprocessing

El script `preprocess_csic_v4.py` extrae 24 features del request HTTP crudo.

Output: `features_v4.parquet` (61,065 filas × 24 features)