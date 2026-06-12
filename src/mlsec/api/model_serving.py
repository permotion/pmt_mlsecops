"""
Model Serving API — CSIC 2010 (features v5)

Levanta el modelo desde MLflow Model Registry (alias=staging) y expone
endpoints para predicción y health check. El algoritmo concreto (XGBoost,
LightGBM, etc.) depende del run promovido en MLflow — ver GET /model/info.

Descarga el artifact automáticamente via REST API de MLflow.

Uso:
    uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload

Endpoints:
    GET  /health         — Health check + modelo cargado
    GET  /model/info     — Info del modelo (threshold, metrics, version)
    POST /predict       — Predicción con features en JSON
"""

import os
import time
import json
from contextlib import asynccontextmanager

import mlflow
import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sklearn.preprocessing import StandardScaler

# Config
MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5081")
MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME", "model-csic")
STAGE = os.environ.get("MLFLOW_MODEL_ALIAS", "staging")
PORT = int(os.environ.get("UVICORN_PORT", "5082"))

# MLflow setup
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def load_model_info():
    """Obtiene metadata del modelo desde el Model Registry."""
    client = mlflow.tracking.MlflowClient()

    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, STAGE)
        version = mv.version
        run_id = mv.run_id
        deployment_stage = mv.tags.get("deployment_stage", "unknown")
        selected_at = mv.tags.get("selected_at", "unknown")
    except Exception as e:
        raise RuntimeError(f"No se encontró modelo con alias '{STAGE}': {e}")

    run = client.get_run(run_id)
    metrics = {
        "recall": run.data.metrics.get("recall", 0),
        "precision": run.data.metrics.get("precision", 0),
        "roc_auc": run.data.metrics.get("roc_auc", 0),
        "threshold": run.data.metrics.get("threshold", 0),
    }
    params = {
        "model": run.data.params.get("model", "unknown"),
        "features_version": run.data.params.get("features_version", "unknown"),
    }

    return {
        "model_name": MODEL_NAME,
        "stage": STAGE,
        "version": str(version),
        "run_id": run_id,
        "deployment_stage": deployment_stage,
        "selected_at": selected_at,
        "metrics": metrics,
        "params": params,
        "loaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# Global model instance and scaler
_model = None
_model_info = None



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo al levantar el servidor."""
    global _model, _model_info, _scaler_info
    print(f"[model_serving] Iniciando...")

    try:
        # 1. Obtener info del modelo desde Model Registry
        _model_info = load_model_info()
        version = _model_info["version"]
        print(f"[model_serving] Modelo: {MODEL_NAME} v{version}")
        print(f"[model_serving] Run ID: {_model_info['run_id']}")
        print(f"[model_serving] Métricas: recall={_model_info['metrics']['recall']:.4f}, "
              f"precision={_model_info['metrics']['precision']:.4f}, "
              f"threshold={_model_info['metrics']['threshold']:.4f}")

        # 2. Cargar modelo directamente desde el URI de MLflow
        model_uri = f"models:/{MODEL_NAME}@{STAGE}"
        print(f"[model_serving] Descargando modelo desde {model_uri}...")
        try:
            _model = mlflow.sklearn.load_model(model_uri)
        except Exception:
            print(f"[model_serving] Buscando MLmodel dentro de subdirectorios de {model_uri}...")
            local_dir = mlflow.artifacts.download_artifacts(model_uri)
            if not os.path.exists(os.path.join(local_dir, "MLmodel")):
                for root, dirs, files in os.walk(local_dir):
                    if "MLmodel" in files:
                        local_dir = root
                        break
            _model = mlflow.sklearn.load_model(local_dir)
        print(f"[model_serving] Modelo {_model_info['params']['model']} cargado exitosamente.")



        print(f"[model_serving] Listo en puerto {PORT}")

    except Exception as e:
        print(f"[model_serving] ERROR al cargar modelo: {e}")
        raise

    yield
    print("[model_serving] Shutting down...")


app = FastAPI(
    title="MLSecOps Model Serving",
    description=f"API para predicción con modelo {MODEL_NAME} desde MLflow Registry",
    version="1.0.0",
    lifespan=lifespan,
)


# ---- Request/Response models ----

class PredictRequest(BaseModel):
    features: dict = Field(
        description="Diccionario de features. Debe contener las 27 features de features_v5.parquet"
    )

class PredictHTTPRequest(BaseModel):
    method: str = Field(description="Método HTTP: GET, POST, PUT, DELETE, etc.")
    url: str = Field(description="URL completa con path y query string")
    content_length: int = Field(default=0, description="Content-Length del request body")
    content_type: str = Field(default="", description="Content-Type header")
    body: str = Field(default="", description="Request body (para POST/PUT)")

class PredictResponse(BaseModel):
    prediction: int = Field(description="0=normal, 1=ataque")
    probability: float = Field(description="Probabilidad de la clase positiva (ataque)")
    threshold: float = Field(description="Threshold usado para la predicción")
    model_version: str = Field(description="Versión del modelo en MLflow")
    latency_ms: float = Field(description="Latencia de la predicción en ms")

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    model_version: str | None
    threshold: float | None
    recall: float | None
    precision: float | None

class ModelInfoResponse(BaseModel):
    model_name: str
    stage: str
    version: str | None
    run_id: str | None
    deployment_stage: str | None
    selected_at: str | None
    metrics: dict | None
    params: dict | None
    loaded_at: str

class ApproveResponse(BaseModel):
    status: str
    message: str
    version: str

# ---- Endpoints ----

@app.get("/health", response_model=HealthResponse)
def health():
    if _model_info is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado")
    metrics = _model_info.get("metrics", {}) if _model_info else {}
    return HealthResponse(
        status="ok",
        model_loaded=True,
        model_name=MODEL_NAME,
        model_version=_model_info.get("version") if _model_info else None,
        threshold=metrics.get("threshold"),
        recall=metrics.get("recall"),
        precision=metrics.get("precision"),
    )

@app.get("/model/info", response_model=ModelInfoResponse)
def model_info():
    if _model_info is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado")
    return ModelInfoResponse(**_model_info)

@app.post("/model/approve", response_model=ApproveResponse)
def approve_model():
    """
    Endpoint de seguridad para el Blue Team.
    Agrega el tag 'deployment_stage=approved' al modelo actualmente cargado.
    """
    if _model_info is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado")
    
    try:
        client = mlflow.tracking.MlflowClient()
        version = _model_info.get("version")
        
        # Etiquetar el modelo en el Registry
        client.set_model_version_tag(MODEL_NAME, version, "deployment_stage", "approved")
        
        # Actualizar memoria local para consistencia
        _model_info["deployment_stage"] = "approved"
        
        return ApproveResponse(
            status="success",
            message=f"Modelo {MODEL_NAME} v{version} firmado y aprobado exitosamente por Blue Team.",
            version=version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al intentar aprobar el modelo: {e}")

def extract_features_from_http(method: str, url: str, content_length: int = 0, content_type: str = "", body: str = "") -> dict:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path
    query = parsed.query
    host = parsed.netloc

    full_url = host + path + ("?" + query if query else "")
    url_length = len(full_url)

    url_param_count = url.count("=")
    url_pct_density = (url.count("%") / url_length) if url_length > 0 else 0
    url_path_depth = path.count("/")
    url_query_length = len(query)
    url_has_query = 1 if query else 0
    url_has_pct27 = 1 if ("%27" in url or "'" in url) else 0
    url_has_pct3c = 1 if ("%3C" in url or "<" in url) else 0
    url_has_dashdash = 1 if "--" in url else 0
    url_has_script = 1 if "script" in url.lower() else 0
    url_has_select = 1 if "SELECT" in url else 0

    content_param_count = body.count("=")
    content_pct_density = (body.count("%") / len(body)) if len(body) > 0 else 0
    content_param_density = (content_param_count / len(body)) if len(body) > 0 else 0
    content_has_pct27 = 1 if ("%27" in body or "'" in body) else 0
    content_has_pct3c = 1 if ("%3C" in body or "<" in body) else 0
    content_has_dashdash = 1 if "--" in body else 0
    content_has_script = 1 if "script" in body.lower() else 0
    content_has_select = 1 if "SELECT" in body else 0

    url_query_ratio = url_query_length / url_length if url_length > 0 else 0
    content_url_ratio = content_length / url_query_length if url_query_length > 0 else 0

    method = method.upper()
    is_long_post = 1 if method == "POST" and content_length > 100 else 0
    url_length_get = url_length if method == "GET" else 0

    features = {
        "method_is_get": 1 if method == "GET" else 0,
        "method_is_post": 1 if method == "POST" else 0,
        "method_is_put": 1 if method == "PUT" else 0,
        "url_length": url_length,
        "url_param_count": url_param_count,
        "url_pct_density": url_pct_density,
        "url_path_depth": url_path_depth,
        "url_query_length": url_query_length,
        "url_has_query": url_has_query,
        "url_has_pct27": url_has_pct27,
        "url_has_pct3c": url_has_pct3c,
        "url_has_dashdash": url_has_dashdash,
        "url_has_script": url_has_script,
        "url_has_select": url_has_select,
        "content_length": content_length,
        "content_pct_density": content_pct_density,
        "content_param_count": content_param_count,
        "content_param_density": content_param_density,
        "content_has_pct27": content_has_pct27,
        "content_has_pct3c": content_has_pct3c,
        "content_has_dashdash": content_has_dashdash,
        "content_has_script": content_has_script,
        "content_has_select": content_has_select,
        "url_query_ratio": url_query_ratio,
        "content_url_ratio": content_url_ratio,
        "is_long_post": is_long_post,
        "url_length_get": url_length_get,
    }

    return features

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if _model_info is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado")

    start = time.time()
    try:
        FEATURE_COLS = [
            'method_is_get', 'method_is_post', 'method_is_put',
            'url_length', 'url_param_count', 'url_pct_density', 'url_path_depth',
            'url_query_length', 'url_has_query', 'url_has_pct27', 'url_has_pct3c',
            'url_has_dashdash', 'url_has_script', 'url_has_select',
            'content_length', 'content_pct_density', 'content_param_count',
            'content_param_density', 'content_has_pct27', 'content_has_pct3c',
            'content_has_dashdash', 'content_has_script', 'content_has_select',
            'url_query_ratio', 'content_url_ratio', 'is_long_post', 'url_length_get',
        ]

        available_features = {k: v for k, v in request.features.items() if k in FEATURE_COLS}

        ordered_values = []
        for col in FEATURE_COLS:
            if col in available_features:
                ordered_values.append(available_features[col])
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Feature faltante: {col}. Se esperaban {len(FEATURE_COLS)} features."
                )

        X = np.array([ordered_values], dtype=np.float32)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar features: {e}")

    try:
        proba = _model.predict_proba(X)[0, 1]
        threshold = _model_info.get("metrics", {}).get("threshold", 0.5)
        
        # Fallback a 0.25 si en MLflow dice 0 (por bug del Stage 4)
        if threshold == 0:
            print("[model_serving] WARNING: threshold=0 en run, usando default 0.2502")
            threshold = 0.2502
            
        pred = 1 if proba >= threshold else 0

        # ---- STAGE 9: LOGGING PARA MONITOREO ----
        import csv
        import os
        from datetime import datetime
        try:
            log_path = "data/processed/production_logs.csv"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            file_exists = os.path.isfile(log_path)
            with open(log_path, 'a', newline='') as f:
                # Add timestamp and prediction to features
                log_row = request.features.copy()
                log_row['timestamp'] = datetime.now().isoformat()
                log_row['prediction'] = pred
                log_row['probability'] = proba
                
                fieldnames = ['timestamp', 'prediction', 'probability'] + FEATURE_COLS
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                if not file_exists:
                    writer.writeheader()
                writer.writerow(log_row)
        except Exception as e:
            print(f"[model_serving] Error guardando log para Stage 9: {e}")
        # ----------------------------------------

        end_time = time.time()
        latency_ms = round((end_time - start_time) * 1000, 2)

        return PredictResponse(
            prediction=pred,
            probability=round(proba, 4),
            threshold=round(threshold, 4),
            model_version=str(_model_info.get("version", "?")) if _model_info else "?",
            latency_ms=round(latency_ms, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {e}")


@app.post("/predict/http", response_model=PredictResponse)
def predict_http(request: PredictHTTPRequest):
    if _model_info is None:
        raise HTTPException(status_code=503, detail="Modelo no cargado")

    try:
        features = extract_features_from_http(
            method=request.method,
            url=request.url,
            content_length=request.content_length,
            content_type=request.content_type,
            body=request.body,
        )
        predict_req = PredictRequest(features=features)
        return predict(predict_req)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar request HTTP: {e}")


@app.get("/predict/nginx")
async def predict_nginx(request: Request):
    """
    Endpoint diseñado para funcionar con auth_request de NGINX.
    Lee las cabeceras originales X-Original-URI y X-Original-Method,
    extrae features al vuelo, predice, y devuelve 200 OK (permitido)
    o 403 Forbidden (bloqueado por WAF).
    """
    try:
        method = request.headers.get("x-original-method", "GET")
        uri = request.headers.get("x-original-uri", "/")
        
        # --- REGLA DETERMINISTA (ALLOWLIST) ---
        # Los WAF Híbridos no pasan rutas estáticas puras por el motor de ML.
        # Esto evita Falsos Positivos OOD (Out-of-Distribution).
        if method == "GET" and (uri == "/" or uri.startswith("/assets/") or uri.endswith((".css", ".js", ".png", ".ico", ".jpg"))):
            return Response(status_code=200)
            
        # NGINX proxy pasa la URI original sin el host. 
        # El dataset CSIC 2010 tenía URLs completas (ej: http://localhost:8080/tienda1/...)
        # Si no agregamos esto, url_length queda muy corto y el modelo lo marca como anomalía.
        url = "http://localhost:8080" + uri
        
        features = extract_features_from_http(
            method=method,
            url=url,
            content_length=0,
            content_type="",
            body="",
        )
        predict_req = PredictRequest(features=features)
        
        # Internamente llamamos a predict() que devuelve un Pydantic Model
        result = predict(predict_req)
        
        if result.prediction == 1:
            # NGINX recibirá un 403 y bloqueará la petición original
            raise HTTPException(status_code=403, detail="[AI WAF] Attack Detected")
            
        # NGINX recibirá un 200 y dejará pasar la petición original
        return Response(status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        # En caso de error de parseo, por seguridad bloqueamos
        raise HTTPException(status_code=403, detail=f"[AI WAF] Parse Error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
