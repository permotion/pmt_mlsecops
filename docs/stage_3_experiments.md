# Stage 3 — Prototipado y Experimentación

---

## Objetivo

Entrenar y comparar **4 algoritmos** en un entorno controlado **sin promover modelos a staging**. Validar hipótesis del EDA y calibrar expectativas de métricas antes del pipeline automatizado.

**Responsable:** Data Science  
**Componente:** Notebook manual

---

## Notebook

| | |
|---|---|
| **Archivo** | `notebooks/experiments/model_csic_experiments.ipynb` |
| **Input** | `data/processed/csic2010/features_v5.parquet` |
| **Output** | Runs en MLflow experiment `model-csic` |
| **Flag clave** | `skip_promote=True` — no toca Model Registry |

---

## Algoritmos evaluados

| Algoritmo | Estrategia desbalance |
|-----------|----------------------|
| LogisticRegression | `class_weight='balanced'` |
| RandomForest | `class_weight='balanced'` |
| XGBoost | `scale_pos_weight` |
| LightGBM | `scale_pos_weight` |

**Criterio de selección:** recall ≥ 0.95 → mayor precision.

---

## Run canónico (features v5)

| Modelo | Recall | Precision | ROC-AUC | FP |
|--------|--------|-----------|---------|-----|
| LogisticRegression | 0.9649 | 0.4808 | 0.8209 | 3917 |
| RandomForest | 0.9492 | 0.7776 | 0.9609 | 1021 |
| **XGBoost** ✅ | **0.9535** | **0.7944** | **0.9655** | **928** |
| LightGBM | 0.9553 | 0.7917 | 0.9662 | 945 |

Las **4 ratio features** de v5 mejoran XGBoost +0.023 precision vs v4.

---

## Relación con Stage 4

El notebook importa la misma función que el DAG de producción:

```python
from src.mlsec.data.train_model_a import train_model_a

results = train_model_a(
    features_path=FEATURES_PATH,
    model_name='model-csic',
    skip_promote=True,  # ← diferencia clave vs DAG
)
```

Stage 4 (`dag_train`) ejecuta la **misma lógica** de forma automatizada y recurrente.

---

## Notebook complementario

`notebooks/experiments/model_csic_fp_analysis.ipynb` — análisis de falsos positivos que motivó las ratio features de v5.

---

## Resultados

Detalle en [Resultados Stage 3 — Train](results/stage_3_results.md).

---

## Navegación

← [Stage 2 — Preprocess](stage_2_preprocess.md) · [Stage 4 — Train](stage_4_train.md) →
