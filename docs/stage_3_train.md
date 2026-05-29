# Stage 3 — Train Model A

---

## Objetivo

Entrenar 4 modelos de clasificación binaria (LogisticRegression, RandomForest, XGBoost, LightGBM) usando `features_v5.parquet` de Stage 2. El mejor modelo que pase los criterios de aceptación es registrado en MLflow Model Registry con alias `staging` para revisión del Blue Team.

Este stage responde a la pregunta: **¿qué algoritmo funciona mejor para detectar ataques web con las features que tenemos?**

---

## Criterios de aceptación

| Métrica | Target | Descripción |
|---------|--------|-------------|
| **Recall** | >= 0.95 | El modelo debe detectar al menos 95% de los ataques |
| **Precision** | >= 0.85 | De las predicciones positivas, 85% deben ser ataques reales |
| **Gap val-test** | <= 0.05 | La diferencia de precision entre validación y test debe ser <= 5% |

Si el mejor modelo no pasa los criterios, no se promueve a staging y se debe revisar el feature engineering o los datos.

---

## Arquitectura del stage — Opción B

Este stage sigue el patrón **notebook para experimentación + script para producción**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — Train Model A                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────┐    ┌────────────────────────────┐ │
│  │  NOTEBOOK (experimentación) │    │  SCRIPT (producción)       │ │
│  │                              │    │                            │ │
│  │  notebooks/experiments/      │    │  src/mlsec/data/           │ │
│  │  model_csic_experiments.ipynb │    │  train_model_a.py          │ │
│  │                              │    │                            │ │
│  │  • Carga train_model_a()    │    │  • train_model_a()         │ │
│  │  • Entrena 4 modelos       │    │  • Misma función            │ │
│  │  • Visualiza resultados    │    │  • Invocado por DAG        │ │
│  │  • Análisis interactivo    │    │  • Logging a MLflow         │ │
│  │                              │    │  • Registro en Registry   │ │
│  └──────────────┬───────────────┘    └──────────────┬───────────┘ │
│                 │                                   │             │
│                 │  Misma función                   │             │
│                 │  train_model_a()                  │             │
│                 └───────────────┬───────────────────┘             │
│                                 │                                 │
│                                 ▼                                 │
│                   ┌─────────────────────────┐                    │
│                   │  MLflow (tracking)     │                    │
│                   │  4 runs (uno por modelo)│                    │
│                   │  Métricas + parámetros │                    │
│                   └─────────────────────────┘                    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  DAG — Orquestación                                         │  │
│  │  verify_input → train_models (invoca script)                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Por qué este patrón

| Aspecto | Notebook | Script |
|---------|----------|--------|
| **Velocidad de iteración** | Alta — código células por célula | Baja — todo el script |
| **Debugging** | Fácil — print o visualizaciones | Medio — logs |
| **Reproducibilidad** | Baja — depende del kernel state | Alta — idempotente |
| **MLflow logging** | Sí — `mlflow.start_run()` | Sí — mismo código |
| **Ejecución automática** | No — manual | Sí — DAG |

**DRY (Don't Repeat Yourself):** El código de training está en `train_model_a.py`. Tanto el notebook como el script importan la misma función.

### Flujo de trabajo

1. **Experimentación** → Se abre el notebook, se ejecuta `train_model_a()`, se analizan resultados
2. **Producción** → El DAG invoca `train_model_a.py`, que usa la misma función
3. **Resultado** → Ambos van a parar al mismo experimento `model-csic` en MLflow

---

## Algoritmos evaluados y por qué

### 1. Logistic Regression (Baseline)

**¿Por qué un baseline lineal?**

Logistic Regression es el punto de partida estándar en cualquier pipeline de ML. Es simple, interpretable, y establece un piso de rendimiento. Si un modelo lineal funciona bien, no necesitamos complejidad extra.

**Configuración:**
```python
LogisticRegression(
    class_weight='balanced',   # Maneja desbalance 59/41
    max_iter=1000,             # Convergencia asegurada
    random_state=42
)
```

**Ventajas:**
- Interpretable (coef. indica dirección de feature)
- Rápido de entrenar
- No requiere feature scaling estricto para árbol-based

**Limitaciones:**
- Supone relación lineal entre features y log-odds
- No captura interacciones entre features
- En problemas con correlación no lineal (como SQL injection patterns), típicamente underfits

**Resultado esperado en CSIC 2010:** Recall alto (~1.0) pero Precision baja (~0.41) — el modelo tiende a predecir todo como ataque cuando no tiene suficiente capacidad discriminativa.

---

### 2. Random Forest

**¿Por qué Random Forest?**

Es un ensemble de decision trees que promedia múltiples modelos, reduciendo variance y overfitting. Random Forest es robusto, no requiere feature scaling, y maneja bien features mixtas (binarias + continuas).

**Configuración:**
```python
RandomForestClassifier(
    n_estimators=200,          # 200 árboles — buen balance speed/performance
    class_weight='balanced',   # Maneja desbalance 59/41
    random_state=42,
    n_jobs=-1                  # Paraleliza en todos los cores
)
```

**Ventajas:**
- No necesita feature scaling
- Maneja features no-lineales e interacciones automáticamente
- Robusto a outliers
- Feature importance integrada

**Limitaciones:**
- Puede overfittear con árboles muy profundos (mitigado con `max_depth` por defecto)
- Memoria pesada con muchos árboles

**Por qué funciona bien en HTTP attack detection:**
- Las features binarias de indicadores (`url_has_pct27`, `content_has_dashdash`) son como splits en árboles
- Interacciones como "PUT + long URL" se capturan sin feature engineering explícito
- `method_is_put` (100% ataques) es un split perfecto que domina el árbol

---

### 3. XGBoost

**¿Por qué XGBoost?**

Gradient Boosting genera árboles secuenciales donde cada nuevo árbol corrige los errores del anterior. XGBoost es conocidos por ganar competencias de ML por su capacidad de capturar patrones complejos.

**Configuración:**
```python
XGBClassifier(
    n_estimators=200,
    scale_pos_weight=neg/pos,  # Ratio de desbalance (calculado dinámicamente)
    eval_metric='logloss',
    random_state=42,
    n_jobs=-1,
    verbosity=0
)
```

**Ventajas:**
- Mejor que Random Forest en muchos casos porque corrige errores secuencialmente
- Regularización L1/L2 integrada (previene overfitting)
- Maneja missing values nativamente

**Limitaciones:**
- Más sensible a hiperparámetros que Random Forest
- Puede overfittear si `n_estimators` es muy alto sin early stopping
- Feature scaling no necesario pero sí recomendado para convergencia más rápida

**Comportamiento esperado:** XGBoost típicamente achieve mayor Recall que Random Forest pero puede generar más False Positives (menor Precision).

---

### 4. LightGBM

**¿Por qué LightGBM?**

LightGBM es una implementación de gradient boosting optimizada para velocidad y memoria. Developed por Microsoft, es más rápido que XGBoost en training mientras mantiene accuracy comparable.

**Configuración:**
```python
LGBMClassifier(
    n_estimators=200,
    scale_pos_weight=neg/pos,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)
```

**Ventajas:**
- Training 10-20x más rápido que XGBoost en datasets grandes
- Usa histogram-based splitting (más eficiente)
- Mejor manejo de features categóricas

**Limitaciones:**
- Puede converger muy rápido causing underfitting si `learning_rate` es muy alto
- Menos maduro que XGBoost (menos documentación, menos battle-tested)

**Comportamiento esperado:** Similar a XGBoost pero más rápido. En CSIC 2010, típicamente obtiene el mejor ROC-AUC entre los 4 modelos.

---

## Comparativa de algoritmos

| Algoritmo | Tipo | Ventajas principales | Limitaciones principales |
|-----------|------|---------------------|--------------------------|
| Logistic Regression | Lineal | Interpretable, rápido | No captura no-linealidades |
| Random Forest | Ensemble (bagging) | Robusto, no necesita scaling | Puede overfittear con depth alta |
| XGBoost | Ensemble (boosting) | Alta accuracy, regularización | Sensitive a hiperparámetros |
| LightGBM | Ensemble (boosting) | Rápido, eficiente | Puede converger muy rápido |

---

## Split del dataset

```
Train: 70%  (~42,745 filas)
Val:   15%  (~9,160 filas)
Test:  15%  (~9,160 filas)
```

El split es **estratificado** para mantener la proporción de ataques en cada conjunto:

```python
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y,
    test_size=0.30,
    stratify=y,           # Mantiene ratio de clases
    random_state=42       # Reprodcibilidad
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp,
    test_size=0.50,
    stratify=y_temp,
    random_state=42
)
```

**¿Por qué 70/15/15?**
- 70% para training da suficiente datos para que los modelos aprendan
- 15% para validación permite calibrar el threshold sin tocar test
- 15% para test simula datos nunca vistos (representa el mundo real)

---

## Feature scaling

Solo las features continuas se escalan (las binarias 0/1 no lo necesitan):

```python
CONTINUOUS_FEATURES = ['url_length', 'url_query_length', 'content_length']

scaler = StandardScaler()
X_train[:, continuous_idx] = scaler.fit_transform(X_train[:, continuous_idx])
X_val[:, continuous_idx] = scaler.transform(X_val[:, continuous_idx])
X_test[:, continuous_idx] = scaler.transform(X_test[:, continuous_idx])
```

**¿Por qué StandardScaler?**
- Centra cada feature en media=0, std=1
- Logistic Regression y XGBoost convergen más rápido con features escaladas
- Random Forest y LightGBM no lo necesitan pero no les afecta

---

## Threshold calibration

El threshold **no es 0.5**. Se busca el threshold óptimo que maximiza Precision manteniendo Recall >= 0.955 en validación.

### ¿Por qué no threshold = 0.5?

En un dataset desbalanceado (59% normal, 41% ataque), el default 0.5 asume que ambos clases son igualmente probables. Esto no es cierto. Además, nuestro criterio de éxito prioriza Recall (detectar ataques), no F1.

### Algoritmo

```python
def find_best_threshold(y_true, y_proba, min_recall=0.955):
    """
    Encuentra el threshold que maximiza Precision
    manteniendo Recall >= min_recall en el set de validación.
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)

    # Máscara: solo thresholds que mantienen Recall >= min_recall
    mask = recalls[:-1] >= min_recall

    if not mask.any():
        # Si ningún threshold cumple, usar el de máximo recall
        return float(thresholds[np.argmax(recalls[:-1])])

    # De los que cumplen, elegir el de máxima precision
    best_idx = np.where(mask, precisions[:-1], 0).argmax()
    return float(thresholds[best_idx])
```

### Resultado esperado

| Modelo | Threshold óptimo |
|--------|-----------------|
| Logistic Regression | ~0.12 (muy bajo — compensa baja capacidad) |
| Random Forest | ~0.15-0.17 |
| XGBoost | ~0.12-0.15 |
| LightGBM | ~0.15-0.17 |

Un threshold bajo significa que el modelo necesita menos "confianza" para clasificar como ataque. Esto es típico cuando la clase positiva (ataque) es la más importante.

---

## Desbalance de clases

El dataset tiene 59% normal / 41% ataque — desbalance leve que se maneja con `class_weight='balanced'`.

```python
neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
scale_pos_weight = neg / pos  # ~1.44 para CSIC 2010
```

Para modelos que usan `scale_pos_weight` (XGBoost, LightGBM), este valor hace que el modelo preste más atención a la clase minoritaria (ataque).

**¿Por qué no SMOTE?**

SMOTE (Synthetic Minority Over-sampling) genera datos sintéticos para balancear. Con 59/41, el desbalance es suficientemente leve para que `class_weight='balanced'` sea suficiente. SMOTE adds complejidad y puede generar ruido.

---

## Registro en MLflow

### Modelo y Experimento

- **Model Registry:** `model-csic`
- **Experiment name:** `model-csic` (usa el mismo nombre por defecto)
- **Tracking URI:** `http://mlflow:5000` (docker) o `http://localhost:5081` (local)

### Metadata de cada run

Cada run en MLflow tiene:

| Campo | Valor ejemplo |
|-------|--------------|
| Run name | `model-csic-lightgbm-features-v5` |
| Description | `Model A LightGBM - 2026-05-21 15:32:00` |
| Tags | `model_name=LightGBM`, `features_version=v5`, `execution_time=2026-05-21 15:32:00` |

### Métricas loggeadas por modelo

| Métrica | Descripción |
|---------|-------------|
| `roc_auc_val` | ROC-AUC en validación |
| `recall_val` | Recall en validación |
| `precision_val` | Precision en validación |
| `roc_auc` | ROC-AUC en test |
| `recall` | TP / (TP + FN) |
| `precision` | TP / (TP + FP) |
| `fp` | False positives |
| `gap_precision` | \|precision_val - precision\| |

### Parámetros loggeados

| Parámetro | Descripción |
|-----------|-------------|
| `model` | Nombre del algoritmo |
| `features_version` | "v5" |
| `n_features` | Cantidad de features (23) |
| `threshold` | Threshold calibrado |
| `min_recall_val` | Target de recall en validación (0.955) |
| `execution_time` | Timestamp de ejecución |
| `feature_i` | Nombre de cada feature |

### Criterios de promoción a staging

Un modelo se registra en MLflow Model Registry con alias `staging` si:

| Criterio | Valor |
|----------|-------|
| test_recall | >= 0.95 |
| test_precision | >= 0.85 |
| gap_precision | <= 0.05 |

### Registro del modelo

```
Modelo registrado: model-csic
Versión: N (auto-incrementado por MLflow)
Alias: staging
Description: model-csic - 2026-05-21 15:32:00 - LightGBM
Tags:
  - deployment_stage: candidate
  - algorithm: LightGBM
  - trained_at: 2026-05-21 15:32:00
```

---

## DAG de Airflow

Este stage no tiene su propio DAG. El entrenamiento se ejecuta desde el notebook `model_csic_experiments.ipynb` (experimentación) o desde el script `train_model_a.py` (producción).

El DAG `dag_promote_model.py` (Stage 6) es el que consulta MLflow, selecciona el mejor candidato y lo promueve a alias=staging.

```bash
# Ejecutar notebook
jupyter notebook notebooks/experiments/model_csic_experiments.ipynb

# O ejecutar script manualmente
python -m src.mlsec.data.train_model_a \
    --input data/processed/csic2010/features_v5.parquet \
    --model-name model-csic

# Trigger DAG de promoción (Stage 6)
airflow dags trigger dag_promote_model
```

---

## Salida del stage

| Campo | Detalle |
|-------|---------|
|Modelo | MLflow `model-csic` con alias `staging` (si pasa criterios) |
| Métricas | ROC-AUC, Recall, Precision, FP, Gap |
| Threshold | Calibrado automáticamente |
| Artefactos | Modelo serializado en MLflow |

### Ejemplo de output

```
============================
RESUMEN DE MODELOS
Modelo                  ROC-AUC   Recall  Precision     FP
------------------------------------------------------------
LogisticRegression       0.7610    1.0000     0.4110   5400
RandomForest             0.9392    0.9510     0.6550   1886
XGBoost                  0.9330    0.9640     0.5940   2476
LightGBM                 0.9410    0.9530     0.6540   1894

Criterios: Recall >= 0.95 | Precision >= 0.85

BEST MODEL: RandomForest
  Recall: 0.9510 >= 0.95 ✅
  Precision: 0.6550 >= 0.85 ❌
  Threshold: 0.1534

❌ Best model (RandomForest) no pasa criterios — no se promueve
  Recall: 0.9510 ✅
  Precision: 0.6550 ❌

Entrenamiento completado!
```

---

## Deuda técnica pendiente

### 1. Sin early stopping

Los modelos se entrenan con un número fijo de estimators (200). No hay early stopping basado en validación.

**Impacto:** Posible overfitting si 200 trees es demasiado.
**Pendiente:** Implementar early stopping con conjunto de validación.

### 2. Sin hyperparameter tuning

Los hiperparámetros son fijos (hardcoded). No se explora el espacio de hiperparámetros.

**Impacto:** El modelo puede no estar en su óptimo.
**Pendiente:** Implementar Optuna o similar para tuning.

### 3. Registro es secuencial

Los 4 modelos se entrenan secuencialmente. Se podrían paralelizar.

**Impacto:** Tiempo de training innecesariamente largo.
**Pendiente:** Paralelizar entrenamiento de modelos.

### 4. Dependencia de MLflow centralizado

Si MLflow no está disponible, el DAG falla. No hay fallback.

**Impacto:** El pipeline no es resiliente a fallos en servicios externos.
**Pendiente:** Agregar retry logic o fallback a archivo local.

### 5. Sin feature importance analysis post-training

No se documenta qué features contribuyen más al modelo.

**Impacto:** Dificulta debugging y explicabilidad.
**Pendiente:** Extraer y documentar feature importance.

---

## Archivos del stage

| Archivo | Descripción |
|---------|-------------|
| `notebooks/experiments/model_csic_experiments.ipynb` | Notebook de experimentación — entrena 4 modelos y registra el mejor en Registry con alias=staging |
| `src/mlsec/data/train_model_a.py` | Script de entrenamiento (función `train_model_a()`) — usado por el notebook |
| `src/mlsec/data/promote_model_to_staging.py` | Script de promoción manual a alias=staging |
| `dags/dag_promote_model.py` | DAG de Airflow — Stage 6: selección automática + alerta SNS |
| `docs/stage_3_train.md` | Esta documentación |

---

## Ejecución manual

### Opción 1 — Notebook (experimentación)

```bash
# Abrir notebook en VS Code o Jupyter
code notebooks/experiments/model_csic_experiments.ipynb
# o
jupyter notebook notebooks/experiments/model_csic_experiments.ipynb
```

El notebook ejecuta `train_model_a()` con `skip_promote=True` — entrena los 4 modelos y los loggea a MLflow, pero no promueve ningún modelo a staging.

### Opción 2 — Script (producción)

```bash
# Con promoción a staging (default)
python -m src.mlsec.data.train_model_a \
    --input data/processed/csic2010/features_v5.parquet \
    --model-name model-csic

# Sin promoción (para testing)
python -m src.mlsec.data.train_model_a \
    --input data/processed/csic2010/features_v5.parquet \
    --model-name model-csic \
    --skip-promote
```

### Opción 3 — DAG (Airflow)

```bash
airflow dags trigger dag_promote_model
```

---

## Referencias

- [PMT MLSec — Models](https://github.com/permotion/PMT-MLSec/blob/main/docs/models.md) — Decisiones de arquitectura y resultados de experimentos
- [PMT MLSec — train_model_a_pipeline.py](https://github.com/permotion/PMT-MLSec/blob/main/src/mlsec/models/train_model_a_pipeline.py) — Pipeline completo de entrenamiento

---

## Responsable

**MLOps** — entrenamiento y registro de candidatos