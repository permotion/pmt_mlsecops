# Flujo Completo del Pipeline (MLSecOps)

Este documento detalla el ciclo de vida definitivo de 8 pasos para la ingesta, entrenamiento, validación y pase a producción de modelos de detección de ataques HTTP.

---

## Step 1 — Ingesta y Curado (`dag_curate_dataset`)

**Función:** Descargar, verificar integridad y limpiar el dataset raw inicial.
**Equipo Responsable:** MLOps / Data Engineering
**Inputs:** Fuentes de datos externas (CSIC 2010).
**Outputs/Entregables:** `curation_report.md` y datos limpios en `data/raw/`.

---

## Step 2 — Exploración (`csic2010_eda.ipynb`)

**Función:** Análisis exploratorio de los datos (EDA) para entender la morfología de las peticiones HTTP (longitudes, distribuciones, caracteres extraños).
**Equipo Responsable:** Data Science / Blue Team
**Inputs:** Dataset raw curado.
**Outputs/Entregables:** Notebook documentado con hallazgos para diseñar las features del siguiente paso.

---

## Step 3 — Preprocesamiento (`dag_preprocess`)

**Función:** Transformación de texto libre (HTTP requests) a un espacio vectorial numérico. Extracción estructurada de características.
**Equipo Responsable:** MLOps
**Inputs:** Dataset limpio.
**Outputs/Entregables:** `features_v5.parquet` (matriz de 27 features de alta densidad).

---

## Step 4 — Prototipado (`experiments.ipynb`)

**Función:** Entrenamiento manual y búsqueda de hiperparámetros de distintos algoritmos (Logistic Regression, Random Forest, LightGBM, XGBoost) para determinar cuál resuelve mejor el problema.
**Equipo Responsable:** Data Science
**Inputs:** `features_v5.parquet`
**Outputs/Entregables:** Experimentos guardados en MLflow con `skip_promote=True` (sin afectar entornos superiores).

---

## Step 5 — Entrenamiento Automatizado (`dag_train`)

**Función:** Entrenamiento oficial y recurrente del modelo ganador (XGBoost) utilizando los parámetros descubiertos en el Step 4. Registro en la base de datos de MLflow.
**Equipo Responsable:** MLOps
**Inputs:** `features_v5.parquet` y código de entrenamiento (`train_model_a.py`).
**Outputs/Entregables:** 
- Binario del modelo registrado en MLflow Model Registry.
- Tag en MLflow: `deployment_stage = candidate`.

---

## Step 6 — Promoción a Staging (`dag_promote_model`)

**Función:** Búsqueda automática del mejor modelo "candidate" que cumpla los requisitos mínimos (ej. Recall >= 0.95). Asignación del alias `@staging` y notificación.
**Equipo Responsable:** MLOps (Totalmente Automatizado)
**Inputs:** Modelos registrados en MLflow.
**Outputs/Entregables:** 
- Alias en MLflow: `@staging` apuntando al mejor candidato.
- Alerta enviada al Blue Team vía SNS/Email.

---

## Step 7 — Auditoría y Aprobación (Blue Team)

**Función:** El Blue Team evalúa la API expuesta con el modelo `@staging`. Realizan pruebas DAST y evalúan Falsos Positivos. Si es seguro, aprueban la versión.
**Equipo Responsable:** Blue Team
**Inputs:** API de Inferencia (consumiendo `@staging`).
**Outputs/Entregables:** 
- Llamada a `POST /model/approve`
- Tag en MLflow actualizado a `deployment_stage = approved`.

---

## Step 8 — Despliegue a Producción (`dag_deploy_prod`)

**Función:** Verificación estricta de la firma digital del Blue Team (`approved`). Si está presente, transfiere el modelo al WAF real y alerta a los atacantes éticos.
**Equipo Responsable:** MLOps
**Inputs:** Modelo en `@staging` con tag `approved`.
**Outputs/Entregables:** 
- Alias en MLflow: `@production`.
- Alerta (SNS) enviada al **Red Team** indicando que pueden comenzar las pruebas de evasión en producción.

---

## Diagrama de la Arquitectura de Transiciones

```text
  [Step 5]         [Step 6]          [Step 7]           [Step 8]
 dag_train  --->  dag_promote  ---> Blue Team API ---> dag_deploy_prod
(candidate)       (@staging)       (/approve tag)      (@production)
```