"""
DAG - Stage 2: Preprocess CSIC 2010

Genera features estructuradas (v5) desde el CSV crudo del dataset CSIC 2010.
Output: features_v5.parquet (27 features + label)

Pipeline:
    verify_input -> generate_features -> verify_output

Trigger: manual (schedule=None)
"""

import os
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

ROOT = Path(__file__).resolve().parents[1]

PYTHON = os.environ.get("MLSEC_PYTHON", "python3")

DATA_INPUT = ROOT / "data" / "raw" / "csic2010" / "csic_database.csv"
DATA_OUTPUT = ROOT / "data" / "processed" / "csic2010" / "features_v5.parquet"

PREPROCESS_SCRIPT = ROOT / "src" / "mlsec" / "data" / "preprocess_csic.py"

# PYTHONPATH para que Python encuentre el paquete src
PYTHONPATH = str(ROOT)


def check_input_exists():
    if not DATA_INPUT.exists():
        raise FileNotFoundError(
            f"CSV crudo no encontrado: {DATA_INPUT}\n"
            "El dataset CSIC 2010 debe estar en data/raw/csic2010/"
        )
    size_mb = DATA_INPUT.stat().st_size / 1024 / 1024
    print(f"Input encontrado: {DATA_INPUT} ({size_mb:.1f} MB)")


def check_output_exists():
    if not DATA_OUTPUT.exists():
        raise FileNotFoundError(f"Features no generadas: {DATA_OUTPUT}")
    size_mb = DATA_OUTPUT.stat().st_size / 1024 / 1024
    print(f"Output encontrado: {DATA_OUTPUT} ({size_mb:.1f} MB)")


with DAG(
    dag_id="dag_preprocess",
    description="Stage 2 - Preprocess CSIC 2010 (generación de features v5)",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["stage-2", "preprocess", "csic2010"],
) as dag:

    verify_input = PythonOperator(
        task_id="verify_input",
        python_callable=check_input_exists,
    )

    generate_features = BashOperator(
        task_id="generate_features",
        bash_command=(
            f"{PYTHON} -m src.mlsec.data.preprocess_csic "
            f"--input {DATA_INPUT} "
            f"--output {DATA_OUTPUT}"
        ),
        env={"PYTHONPATH": PYTHONPATH},
    )

    verify_output = PythonOperator(
        task_id="verify_output",
        python_callable=check_output_exists,
    )

    verify_input >> generate_features >> verify_output