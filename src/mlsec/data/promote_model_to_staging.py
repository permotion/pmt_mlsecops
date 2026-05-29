"""
Promueve un modelo registrado a alias=staging en MLflow.

Uso:
    python -m src.mlsec.data.promote_model_to_staging \
        --run-id d234a90a3a32490183467fb8214ffd46 \
        --model-name model-csic

Alias disponibles en MLflow 3.x:
- staging: candidato para revisión del Blue Team
- production:deployado y sirviendo predicciones
- archived: modelos descartados
"""

import argparse
import json
import mlflow
from mlflow.tracking import MlflowClient

MLFLOW_TRACKING_URI = "http://localhost:5081"


def promote_to_staging(
    run_id: str,
    model_name: str = "model-csic",
    mlflow_tracking_uri: str = MLFLOW_TRACKING_URI,
):
    """
    Promueve el modelo de un run específico a alias=staging.

    Args:
        run_id: MLflow run ID del modelo a promover
        model_name: Nombre del modelo en el Registry (ej: "model-csic")
        mlflow_tracking_uri: URI del MLflow tracking server

    Returns:
        dict: Métricas del modelo {recall, precision, roc_auc, threshold, model_version}
    """
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    client = MlflowClient()

    # Obtener información del run
    run = client.get_run(run_id)
    model_version = run.data.params.get("model", "unknown")
    features_version = run.data.params.get("features_version", "unknown")
    recall = run.data.metrics.get("recall", 0)
    precision = run.data.metrics.get("precision", 0)
    roc_auc = run.data.metrics.get("roc_auc", 0)
    threshold = run.data.metrics.get("threshold", 0)

    print(f"Run ID: {run_id}")
    print(f"Modelo: {model_version}")
    print(f"Features: {features_version}")
    print(f"Recall: {recall:.4f} | Precision: {precision:.4f} | ROC-AUC: {roc_auc:.4f}")

    # Obtener el modelo del registry
    model_uri = f"runs:/{run_id}/model"

    # Buscar si ya existe una versión del modelo
    registered_versions = client.search_model_versions(filter_string=f"name='{model_name}'")
    if registered_versions:
        existing = [v for v in registered_versions if v.run_id == run_id]
        if existing:
            version = existing[0].version
            print(f"Modelo ya registrado: {model_name} v{version}")
        else:
            registered = client.create_model_version(
                name=model_name,
                source=model_uri,
                run_id=run_id,
            )
            version = registered.version
            print(f"Modelo registrado: {model_name} v{version}")
    else:
        registered = client.create_model_version(
            name=model_name,
            source=model_uri,
            run_id=run_id,
        )
        version = registered.version
        print(f"Modelo registrado: {model_name} v{version}")

    # Asignar alias=staging (MLflow 3.x — alias en registered model)
    client.set_registered_model_alias(model_name, "staging", str(version))
    print(f"Alias 'staging' asignado a {model_name} v{version}")

    # Tags para tracking
    client.set_model_version_tag(model_name, version, "deployment_stage", "candidate")
    client.set_model_version_tag(model_name, version, "promoted_at", "2026-05-21")

    print(f"\n✅ Modelo listo para revisión del Blue Team")
    print(f"   MLflow: http://localhost:5081/#/models/{model_name}")

    return {
        "model_name": model_name,
        "model_version": version,
        "recall": recall,
        "precision": precision,
        "roc_auc": roc_auc,
        "threshold": threshold,
        "mlflow_url": f"http://localhost:5081/#/models/{model_name}",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Promueve un modelo a alias=staging en MLflow"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID del modelo a promover (ej: d234a90a3a32490183467fb8214ffd46)",
    )
    parser.add_argument(
        "--model-name",
        default="model-csic",
        help="Nombre del modelo en MLflow Registry",
    )
    parser.add_argument(
        "--mlflow-uri",
        default="http://localhost:5081",
        help="MLflow tracking URI",
    )
    args = parser.parse_args()

    result = promote_to_staging(
        run_id=args.run_id,
        model_name=args.model_name,
        mlflow_tracking_uri=args.mlflow_uri,
    )

    # Output JSON para que el DAG pueda parsear
    print(f"\n__MLFLOW_RESULT__:{json.dumps(result)}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())