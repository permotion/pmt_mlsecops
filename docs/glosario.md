# Glosario

---

## Términos generales

| Término | Definición |
|---------|------------|
| **MLOps** | Disciplina que integra desarrollo de ML con operaciones de software |
| **Model Registry** | Sistema de versionado y gobernanza de modelos en MLflow |
| **Alias** | Etiqueta para identificar el estado de un modelo (staging/production/archived) |
| **Threshold** | Valor de probabilidad para clasificación binaria |
| **Recall** | % de ataques reales detectados |
| **Precision** | % de predictions positivas que son correctas |
| **FP rate** | Tasa de falsos positivos |
| **False Negative (FN)** | Ataque no detectado por el modelo |

---

## Pipeline stages

| Stage | Descripción |
|-------|-------------|
| 0 | Curado del dataset (PII removal, deduplicación) |
| 1 | Trigger del entrenamiento vía Airflow |
| 2 | Preprocessing (feature engineering) |
| 3 | Training (LightGBM + threshold calibration) |
| 4 | Registro en MLflow Registry |
| 5 | Modelo disponible en Staging |
| 6 | Blue Team evalúa candidato |
| 7 | Promoción a Production |
| 8 | API sirve predictions |
| 9 | Monitoreo continuo |
| 10 | Feedback loop (Red Team → Blue Team → MLOps) |

---

## Equipos y roles

| Rol | Responsabilidad |
|-----|-----------------|
| **MLOps** | Entrenamiento y mantenimiento del pipeline |
| **Blue Team** | Validación y promoción de modelos |
| **Red Team** | Testing adversarial y detección de gaps |
| **AIOps** | Análisis de logs y detección de anomalías |

---

## Herramientas

| Herramienta | Rol |
|-------------|-----|
| **Airflow** | Orquestación de pipelines |
| **MLflow** | Experiment tracking y Model Registry |
| **FastAPI** | API de inferencia |
| **CrewAI** | Agentes autonomous para Red Team |
| **LightGBM** | Gradient boosting para clasificación |