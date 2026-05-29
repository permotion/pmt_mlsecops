# Ciclo de Vida MLOps y Separación de Responsabilidades

En este proyecto, existe una división clara entre el entorno de **investigación** (donde los Data Scientists inventan la lógica), el entorno de **producción** (donde MLOps automatiza), y el perímetro de **seguridad** (donde el Blue Team y Red Team auditan y atacan).

A continuación se detalla cómo fluyen los datos a través de los Notebooks y los DAGs de Airflow, respetando el principio fundamental de que "los modelos en producción no se entrenan a mano".

## Diagrama de Flujo de Datos y Promoción

```text
[Datos Externos / Logs HTTP]
      │
      ▼
+------------------------------------+
| ⚙️ Step 1: dag_curate_dataset      | (MLOps)
+------------------------------------+
      │
      ├─► [Output] data/raw/csic2010.parquet
      │
      ▼
+------------------------------------+
| 📓 Step 2: csic2010_eda.ipynb      | (Data Science / Blue Team)
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Step 3: dag_preprocess          | (MLOps)
+------------------------------------+
      │
      ├─► [Output] data/processed/features_v5.parquet
      │
      ▼
+------------------------------------+
| 📓 Step 4: experiments.ipynb       | (Data Science)
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Step 5: dag_train               | (MLOps)
+------------------------------------+
      │
      ├─► [Output] MLflow Model Registry [Tag: candidate]
      │
      ▼
+------------------------------------+
| ⚙️ Step 6: dag_promote_model       | (MLOps)
+------------------------------------+
      │
      ├─► [Output] MLflow [Alias: @staging] + Alerta SNS
      │
      ▼
+------------------------------------+
| 🛡️ Step 7: Auditoría de Seguridad   | (Blue Team)
|   Ataca API en puerto 5082         |
+------------------------------------+
      │
      ├─► [Output] curl -X POST /model/approve -> [Tag: approved]
      │
      ▼
+------------------------------------+
| ⚙️ Step 8: dag_deploy_prod         | (MLOps)
+------------------------------------+
      │
      └─► [Output] MLflow [Alias: @production] + Alerta Red Team
```

---

## Detalle Paso a Paso (Entradas y Salidas)

### Step 1: Curado de Datos (`dag_curate_dataset.py`)
Es el punto de entrada al sistema. Se encarga de aislar la infraestructura interna de las fuentes de datos externas.
- **Input:** Bases de datos externas o texto plano de logs.
- **Output:** Archivo inmutable `data/raw/csic2010.parquet`.

### Step 2: Exploración de Datos (`csic2010_eda.ipynb`)
Es la primera fase humana. Los investigadores proponen reglas lógicas basándose en análisis visual.
- **Input:** `data/raw/csic2010.parquet`.
- **Output:** Hallazgos analíticos sobre morfología de ataques.

### Step 3: Procesamiento en Producción (`dag_preprocess.py`)
Traduce los descubrimientos del Step 2 en una tubería robusta.
- **Input:** `data/raw/csic2010.parquet`.
- **Output:** `data/processed/features_v5.parquet` (Matriz numérica de 27 variables).

### Step 4: Prototipado del Modelo (`model_csic_experiments.ipynb`)
Calibración de algoritmos (XGBoost).
- **Input:** `data/processed/features_v5.parquet`.
- **Output:** Parámetros óptimos. Los runs se guardan en MLflow (Tracing) pero sin promoverse.

### Step 5: Automatización del Entrenamiento (`dag_train.py`)
El código final se ejecuta automáticamente. No depende de humanos.
- **Input:** `data/processed/features_v5.parquet`.
- **Output:** Modelo guardado en MLflow bajo la etiqueta `deployment_stage = candidate`.

### Step 6: Búsqueda y Staging (`dag_promote_model.py`)
El DAG escanea los modelos candidatos, selecciona el de mayor precisión que supere el 0.95 de Recall.
- **Input:** Modelos `candidate` en MLflow.
- **Output:** Se le asigna el alias dinámico `@staging` y se envía alerta al Blue Team.

### Step 7: Aprobación del Blue Team (API)
Fase humana de ciberseguridad. El equipo ataca la API que consume el modelo `@staging`.
- **Input:** Endpoint `/predict/http`.
- **Output:** Si es robusto, ejecutan `/model/approve` para inyectar el tag `approved`.

### Step 8: Despliegue a Producción (`dag_deploy_prod.py`)
Última barrera. El DAG verifica que el modelo `@staging` tenga la firma `approved`.
- **Input:** Modelo `@staging` firmado.
- **Output:** Se le asigna el alias `@production`. Se envía alerta SNS al Red Team para iniciar DAST en el WAF real.
