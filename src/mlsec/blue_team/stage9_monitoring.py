"""
Stage 9: ML Observability con Evidently AI
Este script evalúa si el tráfico real (production_logs.csv)
está sufriendo Data Drift respecto al dataset original (features_v5.parquet).
"""
import pandas as pd
import os
from evidently import Report
from evidently.presets import DataDriftPreset

def run_monitoring():
    print("🚀 Iniciando Stage 9: Monitoreo de MLSecOps...")
    
    reference_path = "data/processed/csic2010/features_v5.parquet"
    current_path = "data/processed/production_logs.csv"
    
    if not os.path.exists(reference_path):
        print(f"❌ Error: Dataset de referencia no encontrado: {reference_path}")
        return
        
    if not os.path.exists(current_path):
        print(f"❌ Error: Logs de producción no encontrados: {current_path}. Asegúrate de haber enviado tráfico al WAF.")
        return
        
    print(f"✅ Cargando datos de referencia ({reference_path})...")
    ref_df = pd.read_parquet(reference_path)
    
    print(f"✅ Cargando datos actuales de Producción ({current_path})...")
    curr_df = pd.read_csv(current_path)
    
    # Seleccionamos solo las features matemáticas (ignorando columnas como timestamp o prediction)
    feature_cols = [col for col in ref_df.columns if col not in ['target', 'is_attack', 'id']]
    
    # Comprobación de seguridad para evitar errores si curr_df tiene diferentes columnas
    curr_df = curr_df.reindex(columns=feature_cols).fillna(0)
    
    print("🔍 Ejecutando análisis de Data Drift (Evidently AI)...")
    drift_report = Report(metrics=[DataDriftPreset()])
    snapshot = drift_report.run(reference_data=ref_df[feature_cols], current_data=curr_df[feature_cols])
    
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = f"{report_dir}/data_drift_report.html"
    
    print(f"💾 Guardando reporte interactivo en {report_path}...")
    snapshot.save_html(report_path)
    
    print("==================================================")
    print(f"🎉 ¡Monitoreo completo!")
    print(f"👉 Abre este archivo en tu navegador:")
    print(f"   {os.path.abspath(report_path)}")
    print("==================================================")

if __name__ == "__main__":
    run_monitoring()
