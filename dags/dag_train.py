"""
DAG - Stage 3: Train Model A (CSIC 2010)

Ejecuta el script de entrenamiento para generar los modelos basados
en features_v5.parquet y registrarlos en MLflow Model Registry.

Pipeline:
    verify_features -> train_and_register

Trigger: manual (schedule=None)
"""

import os
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

ROOT = Path(__file__).resolve().parents[1]

# Tomamos python3 por defecto o la variable de entorno
PYTHON = os.environ.get("MLSEC_PYTHON", "python3")

DATA_INPUT = ROOT / "data" / "processed" / "csic2010" / "features_v5.parquet"

# PYTHONPATH para que Python encuentre el paquete src
PYTHONPATH = str(ROOT)


def check_features_exist():
    if not DATA_INPUT.exists():
        raise FileNotFoundError(
            f"Features no encontradas: {DATA_INPUT}\n"
            "Ejecutar dag_preprocess primero."
        )
    size_mb = DATA_INPUT.stat().st_size / 1024 / 1024
    print(f"Features de entrada encontradas: {DATA_INPUT} ({size_mb:.1f} MB)")


with DAG(
    dag_id="dag_train",
    description="Stage 3 - Train Model CSIC 2010 (Registro en MLflow)",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["stage-3", "train", "csic2010", "mlflow"],
) as dag:

    verify_features = PythonOperator(
        task_id="verify_features",
        python_callable=check_features_exist,
    )

    train_and_register = BashOperator(
        task_id="train_and_register",
        bash_command=(
            f"{PYTHON} -m src.mlsec.data.train_model_a "
            f"--input {DATA_INPUT} "
            f"--model-name model-csic"
        ),
        env={"PYTHONPATH": PYTHONPATH, "MLFLOW_TRACKING_URI": os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")},
    )

    verify_features >> train_and_register
