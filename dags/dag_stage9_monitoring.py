"""
DAG - Stage 9: Monitoreo de Machine Learning (Data Drift)

Este DAG se ejecuta diariamente (schedule='@daily') para vigilar la salud
matemática del modelo en producción.
Compara el dataset original de entrenamiento contra los logs de producción del día.

Pipeline:
    check_logs_exist -> run_evidently_drift -> alert_blue_team_if_drift
"""

import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

try:
    from airflow.operators.python import PythonOperator
except ImportError:
    pass

# Rutas de los datos
REFERENCE_DATA = "data/processed/csic2010/features_v5.parquet"
PRODUCTION_LOGS = "data/processed/production_logs.csv"
REPORT_OUTPUT = "reports/data_drift_report.html"

default_args = {
    'owner': 'blue_team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'dag_stage9_monitoring',
    default_args=default_args,
    description='Monitoreo de Data Drift con Evidently AI',
    schedule_interval='@daily',
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=['mlsecops', 'blue_team', 'monitoring'],
) as dag:

    # 1. Verificar que haya logs de producción para analizar
    check_logs = BashOperator(
        task_id='check_production_logs',
        bash_command=f'test -f {PRODUCTION_LOGS} || (echo "No hay logs de producción" && exit 1)',
        cwd='/opt/airflow',
    )

    # 2. Ejecutar el script de Evidently AI
    run_monitoring = BashOperator(
        task_id='run_evidently_drift',
        bash_command='python src/mlsec/blue_team/stage9_monitoring.py',
        cwd='/opt/airflow',
    )

    # El flujo es lineal
    check_logs >> run_monitoring
