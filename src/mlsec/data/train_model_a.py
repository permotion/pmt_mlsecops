"""
Stage 3 — Train Model A (Core Training Logic)

Este módulo contiene la lógica de entrenamiento de Model A.
Es usado por:
- notebooks/experiments/model_a_experiments.ipynb (experimentación)
- src/mlsec/data/train_model_a.py (producción via DAG)

El código de training está en un solo lugar (DRY).

Uso como script:
    python -m src.mlsec.data.train_model_a \
        --input data/processed/csic2010/features_v4.parquet \
        --model-name model-csic

Uso como módulo:
    from src.mlsec.data.train_model_a import train_model_a
    results = train_model_a(features_path, model_name="model-csic")
"""

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier
import mlflow
import mlflow.sklearn

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

RANDOM_STATE = 42
MIN_RECALL = 0.95
MIN_PRECISION = 0.75
MIN_RECALL_VAL = 0.955  # Más estricto en validación para calibrar threshold
TEST_SIZE = 0.30
VAL_SIZE = 0.50

CONTINUOUS_FEATURES = ["url_length", "url_query_length", "content_length"]


# ─────────────────────────────────────────────────────────────────────────────
# Funciones de training
# ─────────────────────────────────────────────────────────────────────────────


def find_best_threshold(y_true, y_proba, min_recall=MIN_RECALL_VAL):
    """
    Encuentra el threshold que maximiza Precision manteniendo Recall >= min_recall.

    Args:
        y_true: Ground truth labels
        y_proba: Predicted probabilities for positive class
        min_recall: Minimum recall to maintain

    Returns:
        Optimal threshold float
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    mask = recalls[:-1] >= min_recall
    if not mask.any():
        return float(thresholds[np.argmax(recalls[:-1])])
    return float(thresholds[np.where(mask, precisions[:-1], 0).argmax()])


def train_model_a(
    features_path: Path,
    model_name: str = "model-csic",
    experiment_name: Optional[str] = None,
    mlflow_tracking_uri: Optional[str] = None,
    continuous_features: list = None,
    min_recall: float = MIN_RECALL,
    min_precision: float = MIN_PRECISION,
    min_recall_val: float = MIN_RECALL_VAL,
    skip_promote: bool = False,
) -> dict:
    """
    Entrena 4 modelos (LR, RF, XGBoost, LightGBM) con features_v4.parquet.

    Todos los modelos se loggean a MLflow. El mejor modelo (por Recall >= 0.95
    y mayor Precision) se registra en el Model Registry con alias 'staging'
    si pasa los criterios.

    Args:
        features_path: Path al archivo parquet de features
        model_name: Nombre del modelo en MLflow Model Registry (ej: "model-csic")
        experiment_name: Nombre del experimento MLflow (None = usa model_name)
        mlflow_tracking_uri: URI de tracking de MLflow (None = usar env var)
        continuous_features: Lista de features continuas a escalar
        min_recall: Criterio mínimo de recall en test
        min_precision: Criterio mínimo de precision en test
        min_recall_val: Recall mínimo para calibración de threshold en val
        skip_promote: Si True, no promueve el mejor modelo a staging

    Returns:
        Dict con:
            - results: dict de métricas por modelo
            - best_model: tuple (name, model, threshold, metrics, run_id) o None
    """
    if continuous_features is None:
        continuous_features = CONTINUOUS_FEATURES

    # Use model_name as experiment_name if not provided
    if experiment_name is None:
        experiment_name = model_name

    execution_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Setup MLflow ──────────────────────────────────────────────────────────
    if mlflow_tracking_uri is None:
        mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)

    print(f"MLflow tracking: {mlflow_tracking_uri}")
    print(f"Experiment: {experiment_name}")

    # ── Load data ─────────────────────────────────────────────────────────────
    input_path = Path(features_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Features no encontradas: {input_path}\n"
            "Ejecutar dag_preprocess primero"
        )

    print(f"\nCargando features: {input_path}")
    df = pd.read_parquet(input_path)
    print(f"  Shape: {df.shape}")
    print(f"  Label: {df['label'].value_counts().to_dict()}")

    # ── Prepare features ───────────────────────────────────────────────────────
    feature_cols = [c for c in df.columns if c != "label"]
    X = df[feature_cols].values.astype(np.float32)
    y = df["label"].values

    # ── Split 70/15/15 ────────────────────────────────────────────────────────
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=VAL_SIZE, stratify=y_temp, random_state=RANDOM_STATE
    )
    print(f"\nSplit: Train={len(y_train):,} Val={len(y_val):,} Test={len(y_test):,}")

    # ── Prepare continuous indices ────────────────────────────────────────────
    continuous_idx = [feature_cols.index(c) for c in continuous_features]

    # ── Scale pos weight for imbalanced models ───────────────────────────────
    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    scale = neg / pos
    print(f"scale_pos_weight: {scale:.3f} (neg={neg:,}, pos={pos:,})")

    # ── Define models ─────────────────────────────────────────────────────────
    models = [
        (
            "LogisticRegression",
            LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=RANDOM_STATE,
            ),
        ),
        (
            "RandomForest",
            RandomForestClassifier(
                n_estimators=200,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
        (
            "XGBoost",
            XGBClassifier(
                n_estimators=200,
                scale_pos_weight=scale,
                eval_metric="logloss",
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbosity=0,
            ),
        ),
        (
            "LightGBM",
            LGBMClassifier(
                n_estimators=200,
                scale_pos_weight=scale,
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbose=-1,
            ),
        ),
    ]

    # ── Train and evaluate each model ─────────────────────────────────────────
    results = {}
    best_model = None
    best_score = 0

    print("\n" + "=" * 60)
    for name, base_model in models:
        algo_slug = name.lower().replace(" ", "")
        run_name = f"model-csic-{algo_slug}-features-v5"

        # Wrap in Pipeline with ColumnTransformer for continuous features
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), continuous_idx)
            ],
            remainder='passthrough'
        )
        model = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', base_model)
        ])

        with mlflow.start_run(run_name=run_name, description=f"Model CSIC {name} - {execution_time}"):
            mlflow.set_tag("model_name", name)
            mlflow.set_tag("features_version", "v5")
            mlflow.set_tag("execution_time", execution_time)
            mlflow.log_param("model", name)
            mlflow.log_param("features_version", "v5")
            mlflow.log_param("n_features", len(feature_cols))
            mlflow.log_param("min_recall_val", min_recall_val)
            mlflow.log_param("execution_time", execution_time)

            # Train
            model.fit(X_train, y_train)

            # Predict probabilities
            val_proba = model.predict_proba(X_val)[:, 1]
            threshold = find_best_threshold(y_val, val_proba, min_recall_val)
            mlflow.log_param("threshold", round(threshold, 4))

            val_pred = (val_proba >= threshold).astype(int)
            test_proba = model.predict_proba(X_test)[:, 1]
            test_pred = (test_proba >= threshold).astype(int)

            # Evaluate
            val_auc = roc_auc_score(y_val, val_proba)
            val_recall = recall_score(y_val, val_pred)
            val_precision = precision_score(y_val, val_pred)

            test_auc = roc_auc_score(y_test, test_proba)
            test_recall = recall_score(y_test, test_pred)
            test_precision = precision_score(y_test, test_pred)
            cm = confusion_matrix(y_test, test_pred)
            fp = int(cm[0, 1])

            gap = abs(val_precision - test_precision)

            # Log model artifact (which is now a full scikit-learn Pipeline)
            mlflow.sklearn.log_model(model, f"model-{algo_slug}")

            # Log metrics
            mlflow.log_metric("roc_auc_val", round(val_auc, 4))
            mlflow.log_metric("recall_val", round(val_recall, 4))
            mlflow.log_metric("precision_val", round(val_precision, 4))
            mlflow.log_metric("roc_auc", round(test_auc, 4))
            mlflow.log_metric("recall", round(test_recall, 4))
            mlflow.log_metric("precision", round(test_precision, 4))
            mlflow.log_metric("fp", fp)
            mlflow.log_metric("gap_precision", round(gap, 4))

            # Log feature names
            for i, feat in enumerate(feature_cols):
                mlflow.log_param(f"feature_{i}", feat)

            print(f"\n{name}:")
            print(
                f"  Val: ROC-AUC={val_auc:.4f} Recall={val_recall:.4f} "
                f"Precision={val_precision:.4f}"
            )
            print(
                f"  Test: ROC-AUC={test_auc:.4f} Recall={test_recall:.4f} "
                f"Precision={test_precision:.4f} FP={fp}"
            )
            print(f"  Threshold: {threshold:.4f}")
            print(
                f"  Gap: {gap:.4f} {'✅' if gap <= 0.05 else '❌'}"
                f" | Criterios: Recall>={min_recall} {'✅' if test_recall >= min_recall else '❌'} "
                f"Precision>={min_precision} {'✅' if test_precision >= min_precision else '❌'}"
            )

            results[name] = {
                "threshold": threshold,
                "val_auc": val_auc,
                "val_recall": val_recall,
                "val_precision": val_precision,
                "test_auc": test_auc,
                "test_recall": test_recall,
                "test_precision": test_precision,
                "fp": fp,
                "gap": gap,
                "run_id": mlflow.active_run().info.run_id,
            }

            # Track best: prioritize recall >= min_recall, then precision
            if test_recall >= min_recall and test_precision >= best_score:
                best_score = test_precision
                best_model = (name, model, threshold, results[name])

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESUMEN DE MODELOS")
    print(
        f"{'Modelo':<22} {'ROC-AUC':>8} {'Recall':>8} {'Precision':>10} {'FP':>6}"
    )
    print("-" * 60)
    for name, m in results.items():
        print(
            f"{name:<22} {m['test_auc']:>8.4f} {m['test_recall']:>8.4f} "
            f"{m['test_precision']:>10.4f} {m['fp']:>6d}"
        )
    print(f"\nCriterios: Recall >= {min_recall} | Precision >= {min_precision}")

    # ── Promote best model ─────────────────────────────────────────────────────
    if best_model and not skip_promote:
        name, model, threshold, metrics = best_model
        if (
            metrics["test_recall"] >= min_recall
            and metrics["test_precision"] >= min_precision
        ):
            print(f"\n{'='*60}")
            print(f"BEST MODEL: {name}")
            print(
                f"  Recall: {metrics['test_recall']:.4f} >= {min_recall} ✅"
            )
            print(
                f"  Precision: {metrics['test_precision']:.4f} >= {min_precision} ✅"
            )
            print(f"  Threshold: {threshold:.4f}")

            run_id = metrics["run_id"]
            register_model(
                name, model, run_id,
                registry_name=model_name,
                execution_time=execution_time,
            )
        else:
            print(f"\n❌ Best model ({name}) no pasa criterios — no se promueve")
            print(
                f"  Recall: {metrics['test_recall']:.4f} "
                f"{'✅' if metrics['test_recall'] >= min_recall else '❌'}"
            )
            print(
                f"  Precision: {metrics['test_precision']:.4f} "
                f"{'✅' if metrics['test_precision'] >= min_precision else '❌'}"
            )
    elif skip_promote:
        print("\n(Skipping promote --skip-promote)")

    print("\nEntrenamiento completado!")
    return {"results": results, "best_model": best_model}


def register_model(
    model_name: str,
    model,
    run_id: str,
    registry_name: str,
    execution_time: str,
):
    """
    Registra el modelo en MLflow Model Registry como 'candidate'.
    (La promoción a 'staging' se hace en el Stage 6 de Blue Team).

    Args:
        model_name: Nombre del algoritmo (para display)
        model: El modelo sklearn ya entrenado
        run_id: MLflow run ID del mejor modelo
        registry_name: Nombre del modelo en el registry (ej: "model-csic")
        execution_time: Timestamp de ejecución para descripción
    """
    algo_slug = model_name.lower()
    model_uri = f"runs:/{run_id}/model-{algo_slug}"

    # Register model
    registered = mlflow.register_model(
        model_uri,
        name=registry_name,
    )
    print(f"  Modelo registrado: {registered.name} v{registered.version}")

    client = mlflow.MlflowClient()
    
    # Update description using client
    client.update_model_version(
        name=registered.name,
        version=registered.version,
        description=f"{registry_name} - {execution_time} - {model_name}"
    )

    # Asignar tags de candidato
    client.set_model_version_tag(registry_name, registered.version, "deployment_stage", "candidate")
    client.set_model_version_tag(registry_name, registered.version, "algorithm", model_name)
    client.set_model_version_tag(registry_name, registered.version, "trained_at", execution_time)


# ─────────────────────────────────────────────────────────────────────────────
# Script entry point
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Stage 3 — Train Model A")
    parser.add_argument(
        "--input",
        required=True,
        help="Path al parquet de features",
    )
    parser.add_argument(
        "--model-name",
        default="model-csic",
        help="Nombre del modelo en MLflow Registry (ej: model-csic)",
    )
    parser.add_argument(
        "--skip-promote",
        action="store_true",
        help="No promover a staging",
    )
    args = parser.parse_args()

    train_model_a(
        features_path=Path(args.input),
        model_name=args.model_name,
        skip_promote=args.skip_promote,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())