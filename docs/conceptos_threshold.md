# Conceptos Clave — Threshold Calibration

---

## ¿Qué es el threshold?

En un clasificador binario, el modelo produce una **probabilidad** de que un request sea ataque. El **threshold** es el corte a partir del cual se clasifica como ataque (`1`):

```text
probability ≥ threshold  →  prediction = 1 (ataque)
probability < threshold  →  prediction = 0 (normal)
```

En la API (`model_serving.py`), la regla es:

```python
pred = 1 if proba >= threshold else 0
```

El threshold se lee de las métricas del run en MLflow (o default `0.2502` si viene en 0).

---

## ¿Por qué no usar 0.50?

| Threshold | Comportamiento típico en CSIC 2010 |
|-----------|-------------------------------------|
| **0.50** (default sklearn) | Recall ~90% — pierde ~10% de ataques |
| **Calibrado** (~0.25) | Recall ≥ 95% — prioriza no perder ataques |

En seguridad, **un falso negativo (ataque no detectado) suele costar más que un falso positivo (alarma a revisar)**. Por eso bajamos el threshold hasta cumplir recall mínimo.

---

## Cómo calibramos en PMT MLSecOps

Implementado en `find_best_threshold()` (`src/mlsec/data/train_model_a.py`):

### Split de datos

```text
70% train  │  15% validation  │  15% test
           │  (calibración)   │  (métricas finales)
```

Estratificado, `random_state=42`.

### Algoritmo

1. Entrenar modelo en **train**
2. Predecir probabilidades en **validation**
3. Recorrer la curva precision-recall
4. Filtrar puntos con `recall >= 0.955` (validación)
5. Entre esos, elegir el threshold que **maximiza precision**
6. Aplicar ese threshold al **test set** para reportar métricas finales

```python
def find_best_threshold(y_true, y_proba, min_recall=0.955):
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    mask = recalls[:-1] >= min_recall
    # → threshold que maximiza precision bajo recall mínimo
```

### Constantes del proyecto

| Constante | Valor | Uso |
|-----------|-------|-----|
| `MIN_RECALL_VAL` | 0.955 | Calibración en validation |
| `MIN_RECALL` | 0.95 | Criterio de aceptación en test |
| `MIN_PRECISION` | 0.75 | Target entrenamiento (alineado con MVP) |
| MVP precision | 0.75 | Criterio Blue Team |

---

## Run canónico: XGBoost v5

Modelo seleccionado con `features_v5.parquet`:

| Métrica | Valor (test) | Criterio |
|---------|--------------|----------|
| Recall | 0.9535 | ≥ 0.95 ✅ |
| Precision | 0.7944 | ≥ 0.75 ✅ |
| Threshold | **0.2502** | Calibrado en val |
| FP (test) | 928 | — |
| ROC-AUC | 0.9655 | ≥ 0.95 ✅ |

El threshold **0.2502** queda loggeado en MLflow como métrica/parámetro del run y lo consume la API al cargar el modelo.

---

## Desbalance train vs. producción

| Entorno | Ratio normal:ataque | Efecto en métricas |
|---------|---------------------|-------------------|
| **CSIC 2010 (training/test)** | ~59:41 | Recall y precision del test son representativos del benchmark |
| **Producción típica** | ~99:1 | FP rate sube mucho con el mismo threshold |

Un threshold óptimo en CSIC **no es automáticamente óptimo en prod**. Por eso:

- Blue Team estima FP rate con tráfico desbalanceado (Stage 6)
- Stage 9 monitorea FP rate operativo (< 20% target)
- Puede requerirse **re-calibración** post-deploy

Ver también: [Contexto — desbalance](contexto.md#dataset-desbalance-inherente)

---

## Trade-off: recall vs. precision vs. FP rate

Con el modelo XGBoost v5 en test balanceado (CSIC):

| Threshold (ejemplo) | Recall test | Precision test | Notas |
|---------------------|-------------|----------------|-------|
| 0.50 | ~0.90 | mayor | Pierde ataques |
| **0.2502** (canónico) | **0.9535** | **0.7944** | Elegido por calibración |
| 0.30 | ~0.95 | ~0.79 | Alternativa cercana |
| 0.47 | ~0.96 | ~0.77 | Más conservador en FP |

En tráfico **99:1** (producción), la precision operativa cae respecto al test — de ahí el target de FP rate < 20% en lugar de confiar solo en precision de training.

---

## ¿Dónde vive el threshold?

| Ubicación | Descripción |
|-----------|-------------|
| MLflow run | Parámetro `threshold` + métrica en el run |
| API `/model/info` | Expone threshold del modelo cargado |
| API `/predict` | Usa threshold del run para decidir clase |
| Blue Team | Puede solicitar re-train con criterios distintos |

La API **no hardcodea** el algoritmo ni el threshold permanentemente — los descarga del alias activo (`@staging` o `@production`).

---

## Techo de precision (~0.79)

El análisis del proyecto (Stages 2–4) concluye que con **features de campos HTTP individuales** (27 features v5), la precision en test converge en ~0.79–0.80 independientemente del algoritmo (XGBoost vs LightGBM).

Causa principal: features binarias (`url_has_pct27`, etc.) no distinguen bien entre:
- Ataque real: `%27` en SQLi
- Formulario legítimo: caracteres acentuados codificados (`%F1` = ñ) en nombres de producto

**Implicancia para threshold:** subir precision vía threshold alto baja recall por debajo de 0.95 — no es viable sin nuevas features o enfoque distinto.

Detalle: [Resultados Stage 3 — techo de precision](results/stage_3_results.md)

---

## Flujo threshold en el pipeline

```text
dag_train
    └── find_best_threshold(val) → log threshold a MLflow

dag_promote_model
    └── selecciona run (recall/precision en test)

model_serving.py
    └── carga threshold del run → /predict, /predict/http

Blue Team (Stage 6)
    └── valida si FP rate aceptable con ese threshold

Red Team (Stage 10)
    └── detecta FN → puede forzar re-calibración
```

---

## Páginas relacionadas

- [Conceptos MLOps](conceptos_mlops.md) — gobernanza y ciclo de vida
- [Blue Team Guide](blue_team.md) — criterios FP rate
- [Stage 4 — Train](stage_4_train.md) — entrenamiento y calibración
- [Stage 3 — Resultados](results/stage_3_results.md) — métricas por modelo
