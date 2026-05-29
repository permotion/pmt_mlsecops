"""
DAG - Stage 1: Curado del Dataset CSIC 2010

Escanea el dataset y genera un reporte de PII encontrado.
No modifica los datos — solo documenta hallazgos.

Pipeline:
    verify_input -> scan_pii -> generate_report

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
REPORT_OUTPUT = ROOT / "data" / "curated" / "csic2010" / "curation_report.md"

CURATE_SCRIPT = ROOT / "src" / "mlsec" / "data" / "curate_dataset.py"

# PYTHONPATH para que Python encuentre el paquete src
PYTHONPATH = str(ROOT)


def check_input_exists():
    if not DATA_INPUT.exists():
        raise FileNotFoundError(
            f"Dataset no encontrado: {DATA_INPUT}\n"
            "El dataset CSIC 2010 debe estar en data/raw/csic2010/"
        )
    size_mb = DATA_INPUT.stat().st_size / 1024 / 1024
    print(f"Input encontrado: {DATA_INPUT} ({size_mb:.1f} MB)")


def show_report():
    if not REPORT_OUTPUT.exists():
        raise FileNotFoundError(f"Report no encontrado: {REPORT_OUTPUT}")

    content = REPORT_OUTPUT.read_text()
    print(f"\n{'='*60}")
    print("CURATION REPORT")
    print('='*60)
    print(content)
    print('='*60)


with DAG(
    dag_id="dag_curate_dataset",
    description="Stage 1 - Curado del Dataset CSIC 2010 (escaneo de PII)",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["stage-1", "curation", "csic2010"],
) as dag:

    verify_input = PythonOperator(
        task_id="verify_input",
        python_callable=check_input_exists,
    )

    scan_pii = BashOperator(
        task_id="scan_pii",
        bash_command=(
            f"{PYTHON} -m src.mlsec.data.curate_dataset "
            f"--input {DATA_INPUT} "
            f"--report {REPORT_OUTPUT}"
        ),
        env={"PYTHONPATH": PYTHONPATH},
    )

    generate_report = PythonOperator(
        task_id="generate_report",
        python_callable=show_report,
    )

    verify_input >> scan_pii >> generate_report