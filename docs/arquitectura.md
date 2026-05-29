# Arquitectura — Visión General del Pipeline

---

## Diagrama de flujo completo

```text
================================================================================
                            MLSecOps Pipeline
================================================================================

[Data Ingestion]
      │
      ▼
+------------------------------------+
| ⚙️ Step 1: dag_curate_dataset      | (MLOps)
+------------------------------------+
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
      ▼
+------------------------------------+
| 📓 Step 4: experiments.ipynb       | (Data Science)
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Step 5: dag_train               | (MLOps) -> [Tag: candidate]
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Step 6: dag_promote_model       | (MLOps) -> [Alias: @staging] -> [Alerta BT]
+------------------------------------+
      │
      ▼
+------------------------------------+
| 🛡️ Step 7: Validación de Staging   | (Blue Team) -> Ataca API y aprueba 
|            /model/approve          |                [Tag: approved]
+------------------------------------+
      │
      ▼
+------------------------------------+
| ⚙️ Step 8: dag_deploy_prod         | (MLOps) -> Verifica firma Blue Team
|                                    |         -> [Alias: @production]
|                                    |         -> [Alerta Red Team]
+------------------------------------+
      │
      ▼
+------------------------------------+
| 🚀 Producción: model_serving API   | (WAF / Tráfico Real)
+------------------------------------+
```

---

## Ciclo de Vida (8 Steps)

| Step | Componente | Responsabilidad |
|------|------------|-----------------|
| 1 | `dag_curate_dataset` | Ingeniería de Datos (Ingesta) |
| 2 | `csic2010_eda.ipynb` | Data Science (Exploración) |
| 3 | `dag_preprocess` | MLOps (Vectorización) |
| 4 | `experiments.ipynb` | Data Science (Prototipado) |
| 5 | `dag_train` | MLOps (Entrenamiento Automatizado) |
| 6 | `dag_promote_model` | MLOps (Asignación de @staging) |
| 7 | Pruebas DAST a la API | Blue Team (Aprobación y Firma) |
| 8 | `dag_deploy_prod` | MLOps (Pase a @production) |

---

## Arquitectura de servicios

```
MLflow :5081   ← Experiment tracking + Model Registry
Airflow :5080  ← Orquestación + scheduling
FastAPI :5082  ← API de inferencia
Postgres :5432 ← Metastore compartido
```

---

## Roles y Responsabilidades

| Equipo | Misión Principal | Actividad en el Pipeline |
|--------|------------------|--------------------------|
| **Data Science** | Crear la matemática. | Steps 2 y 4 (Notebooks). Calibrar el modelo. |
| **MLOps** | Automatizar la tubería. | Steps 1, 3, 5, 6 y 8 (DAGs). Mantener Infra. |
| **Blue Team** | Defensa y Auditoría. | Step 7. Atacar la API en Staging y aprobar (`/model/approve`). |
| **Red Team** | Ataque en vivo. | Atacar el modelo en Producción para buscar Falsos Negativos (Evasión). |