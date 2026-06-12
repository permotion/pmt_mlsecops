"""
DAG - Stage 6: Selección automática de candidato y promoción a staging

Pipeline:
    find_best_candidate -> promote_to_staging -> notify_blue_team

Flujo automático:
    1. Query MLflow por runs de features_version=v5
    2. Filtrar: Recall >= 0.95
    3. Seleccionar: Mayor Precision
    4. Promover: alias=staging en MLflow
    5. Enviar SNS al Blue Team

Trigger: manual (schedule=None)

Uso:
    - Ejecutar DAG desde Airflow UI
    - O manualmente: airflow dags trigger dag_promote_model
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

try:
    from airflow.operators.python import PythonOperator
except ImportError:
    pass

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5081")
MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "model-csic")
FEATURES_VERSION = os.environ.get("MLFLOW_FEATURES_VERSION", "v5")
MIN_RECALL = float(os.environ.get("MIN_RECALL", "0.95"))
SNS_TOPIC_ARN = os.environ.get("AIRFLOW_VAR_SNS_BLUE_TEAM_TOPIC_ARN", "")


def find_best_candidate(**kwargs):
    """Busca el mejor candidato entre los runs de v5."""
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    # Buscar experimento
    exp = client.get_experiment_by_name(MODEL_NAME)
    if not exp:
        raise ValueError(f"Experimento '{MODEL_NAME}' no encontrado")

    # Filtrar runs de v5 con Recall >= MIN_RECALL
    candidates = []
    for run in client.search_runs(exp.experiment_id):
        features_version = run.data.params.get("features_version", "")
        if features_version != FEATURES_VERSION:
            continue

        recall = run.data.metrics.get("recall", 0)
        if recall < MIN_RECALL:
            continue

        precision = run.data.metrics.get("precision", 0)
        candidates.append({
            "run_id": run.info.run_id,
            "model": run.data.params.get("model", "unknown"),
            "recall": recall,
            "precision": precision,
            "roc_auc": run.data.metrics.get("roc_auc", 0),
            "threshold": run.data.metrics.get("threshold", 0),
            "start_time": run.info.start_time,
        })

    if not candidates:
        raise ValueError(
            f"No hay candidatos con Recall >= {MIN_RECALL} "
            f"y features_version={FEATURES_VERSION}"
        )

    # Ordenar por Precision descendente, y en caso de empate, por el más reciente
    candidates.sort(key=lambda x: (x["precision"], x["start_time"]), reverse=True)
    best = candidates[0]

    print(f"\n=== MEJOR CANDIDATO ===")
    print(f"Run ID: {best['run_id']}")
    print(f"Modelo: {best['model']}")
    print(f"Recall: {best['recall']:.4f} | Precision: {best['precision']:.4f} | ROC-AUC: {best['roc_auc']:.4f}")
    print(f"Threshold: {best['threshold']:.4f}")
    print(f"\nCandidates evaluados: {len(candidates)}")

    # Guardar en XCom para el siguiente task
    kwargs["ti"].xcom_push(key="best_candidate", value=best)
    return best


def promote_to_staging(**kwargs):
    """Promueve el mejor candidato a alias=staging."""
    import mlflow
    from mlflow.tracking import MlflowClient

    ti = kwargs["ti"]
    best = ti.xcom_pull(task_ids="find_best_candidate", key="best_candidate")
    if not best:
        raise ValueError("No se encontró candidato desde find_best_candidate")

    run_id = best["run_id"]
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    model_name_raw = best["model"]
    algo_slug = model_name_raw.lower().replace(" ", "")
    model_uri = f"runs:/{run_id}/model-{algo_slug}"

    # Buscar si ya existe
    registered_versions = client.search_model_versions(filter_string=f"name='{MODEL_NAME}'")
    existing = [v for v in registered_versions if v.run_id == run_id]

    if existing:
        version = existing[0].version
        print(f"Modelo ya registrado: {MODEL_NAME} v{version}")
    else:
        # Crear el modelo registrado si no existe
        try:
            client.create_registered_model(MODEL_NAME)
            print(f"Modelo registrado creado: {MODEL_NAME}")
        except Exception:
            print(f"Modelo {MODEL_NAME} ya existe, continuando...")

        registered = client.create_model_version(
            name=MODEL_NAME,
            source=model_uri,
            run_id=run_id,
        )
        version = registered.version
        print(f"Modelo registrado: {MODEL_NAME} v{version}")

    # Asignar alias=staging (MLflow 3.x — alias en registered model)
    client.set_registered_model_alias(MODEL_NAME, "staging", str(version))
    print(f"Alias 'staging' asignado a {MODEL_NAME} v{version}")

    # Tags
    client.set_model_version_tag(MODEL_NAME, version, "deployment_stage", "candidate")
    client.set_model_version_tag(MODEL_NAME, version, "selected_at", datetime.now().strftime("%Y-%m-%d"))

    result = {
        **best,
        "model_version": version,
        "mlflow_url": f"http://localhost:5081/#/models/{MODEL_NAME}",
    }

    print(f"\n✅ Modelo listo para revisión del Blue Team")
    print(f"   MLflow: {result['mlflow_url']}")

    kwargs["ti"].xcom_push(key="promotion_result", value=result)
    return result


def send_sns_alert(**kwargs):
    """Envía alerta SNS al Blue Team."""
    ti = kwargs["ti"]
    result = ti.xcom_pull(task_ids="promote_to_staging", key="promotion_result")
    if not result:
        print("No se encontró resultado desde promote_to_staging")
        return

    message = {
        "subject": f"[MLSecOps] Modelo候选 Listo para Revisión — {MODEL_NAME}",
        "model_name": MODEL_NAME,
        "model_version": result.get("model_version"),
        "run_id": result.get("run_id"),
        "model": result.get("model"),
        "recall": round(result.get("recall", 0), 4),
        "precision": round(result.get("precision", 0), 4),
        "roc_auc": round(result.get("roc_auc", 0), 4),
        "threshold": round(result.get("threshold", 0), 4),
        "mlflow_url": result.get("mlflow_url"),
        "action_required": "Revisar modelo en MLflow y aprobar/rechazar para producción",
        "timestamp": datetime.now().isoformat(),
    }

    # SNS deshabilitado — solo imprime el mensaje que se enviaría
    print("=" * 60)
    print("MENSAJE SNS QUE SE ENVIARÍA AL BLUE TEAM:")
    print("=" * 60)
    print(json.dumps(message, indent=2))
    print("=" * 60)
    print(f"To: {SNS_TOPIC_ARN or 'AIRFLOW_VAR_SNS_BLUE_TEAM_TOPIC_ARN no configurado'}")
    print("=" * 60)


with DAG(
    dag_id="dag_promote_model",
    description="Stage 6 - Selección automática de candidato + promoción a staging + SNS",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["stage-6", "promote", "mlflow", "sns", "auto"],
) as dag:

    find_best_candidate = PythonOperator(
        task_id="find_best_candidate",
        python_callable=find_best_candidate,
        do_xcom_push=True,
    )

    promote_to_staging = PythonOperator(
        task_id="promote_to_staging",
        python_callable=promote_to_staging,
        do_xcom_push=True,
    )

    notify_blue_team = PythonOperator(
        task_id="notify_blue_team",
        python_callable=send_sns_alert,
        trigger_rule="all_success",
    )

    find_best_candidate >> promote_to_staging >> notify_blue_team