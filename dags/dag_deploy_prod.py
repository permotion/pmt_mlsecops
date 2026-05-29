"""
DAG - Stage 7: Despliegue de staging a producción

Pipeline:
    validate_approval -> promote_to_prod -> notify_deployment

Flujo manual (Blue Team):
    1. Revisa que el alias 'staging' tenga tag deployment_stage='approved'
    2. Pasa el alias 'production' a esa versión de MLflow
    3. Notifica a Infraestructura que se puede deployar en el WAF

Trigger: manual
"""

import os
import json
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5081")
MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "model-csic")
SNS_TOPIC_ARN = os.environ.get("AIRFLOW_VAR_SNS_DEPLOY_TOPIC_ARN", "")


def validate_approval(**kwargs):
    """Verifica que el modelo en staging haya sido aprobado."""
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "staging")
    except Exception as e:
        raise ValueError(f"No se encontró un modelo en staging: {e}")

    stage_tag = mv.tags.get("deployment_stage", "unknown")
    
    if stage_tag != "approved":
        raise ValueError(
            f"El modelo v{mv.version} no está aprobado. "
            f"Tag actual: deployment_stage={stage_tag}. "
            "El Blue Team debe cambiar este tag a 'approved' en MLflow antes de desplegar."
        )

    print(f"✅ Modelo v{mv.version} aprobado para producción.")
    kwargs["ti"].xcom_push(key="approved_version", value=mv.version)
    return mv.version


def promote_to_prod(**kwargs):
    """Asigna el alias production a la versión aprobada."""
    import mlflow
    from mlflow.tracking import MlflowClient

    ti = kwargs["ti"]
    version = ti.xcom_pull(task_ids="validate_approval", key="approved_version")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    # Asignar alias
    client.set_registered_model_alias(MODEL_NAME, "production", str(version))
    
    # Actualizar tag
    client.set_model_version_tag(MODEL_NAME, version, "deployment_stage", "production")
    client.set_model_version_tag(MODEL_NAME, version, "deployed_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print(f"🚀 Modelo v{version} promovido a PRODUCCIÓN exitosamente.")
    return version


def notify_red_team(**kwargs):
    """Notifica al Red Team que hay un nuevo modelo en prod para que intenten evadirlo."""
    ti = kwargs["ti"]
    version = ti.xcom_pull(task_ids="promote_to_prod")

    message = {
        "subject": f"[MLSecOps] RED TEAM ALERT — Nuevo Modelo en Producción v{version}",
        "model_name": MODEL_NAME,
        "model_version": version,
        "action_required": "Iniciar pruebas de evasión y DAST contra el WAF de producción.",
        "timestamp": datetime.now().isoformat(),
    }

    print("=" * 60)
    print("MENSAJE SNS AL RED TEAM:")
    print("=" * 60)
    print(json.dumps(message, indent=2))
    print("=" * 60)


with DAG(
    dag_id="dag_deploy_prod",
    description="Stage 7 - Promoción de staging a producción (Requiere Aprobación)",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["stage-7", "deploy", "mlflow", "production", "red-team"],
) as dag:

    validate_approval_task = PythonOperator(
        task_id="validate_approval",
        python_callable=validate_approval,
    )

    promote_to_prod_task = PythonOperator(
        task_id="promote_to_prod",
        python_callable=promote_to_prod,
    )

    notify_red_team_task = PythonOperator(
        task_id="notify_red_team",
        python_callable=notify_red_team,
    )

    validate_approval_task >> promote_to_prod_task >> notify_red_team_task
