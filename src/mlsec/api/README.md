# MLSecOps - Model Serving API

Esta API disponibiliza el modelo de Machine Learning entrenado para detección de ataques web. Utiliza FastAPI y se conecta directamente al Model Registry de MLflow.

> [!NOTE]
> La API es "ciega" a las versiones. Siempre descarga automáticamente el modelo que tenga el alias `@staging` (o `@production` dependiendo de la configuración), garantizando que siempre se evalúa el modelo correcto sin necesidad de redesplegar el servicio.

## Requisitos y Ejecución

Para correr la API localmente, asegúrate de tener el entorno virtual activado y el servidor de MLflow corriendo en `http://localhost:5081`.

```bash
uvicorn src.mlsec.api.model_serving:app --host 0.0.0.0 --port 5082 --reload
```

---

## Endpoints Disponibles

### 1. Health Check
Verifica que el servicio esté vivo y que el modelo se haya cargado exitosamente desde MLflow.

```bash
curl -s http://localhost:5082/health
```

### 2. Información del Modelo
Muestra los metadatos del modelo cargado, incluyendo su nombre, versión, métricas de entrenamiento (Recall, Precision, Threshold) y el algoritmo utilizado.

```bash
curl -s http://localhost:5082/model/info
```

### 3. Predicción desde HTTP Request (`/predict/http`)
Recibe una simulación de un request HTTP (método, URL, body) y extrae las variables (features) dinámicamente para pasarlas por el modelo.

**Ejemplo de Tráfico Benigno (Normal)**
Debido a la naturaleza del dataset CSIC 2010, el modelo está ajustado para URLs con una longitud promedio (~48 caracteres) y una profundidad de path específica.
```bash
curl -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "url": "http://localhost:8080/a/a/a/a/bxxxxxxxxxxxxxxxxxxxxxxxx",
    "content_length": 0,
    "content_type": "",
    "body": ""
  }'
```

**Ejemplo de Tráfico Malicioso (Ataque SQLi)**
Contiene caracteres codificados (`%27`), inyecciones (`--`) y palabras clave maliciosas en el payload.
```bash
curl -X POST http://localhost:5082/predict/http \
  -H "Content-Type: application/json" \
  -d '{
    "method": "POST",
    "url": "http://localhost:8080/tienda/login.jsp",
    "content_length": 45,
    "content_type": "application/x-www-form-urlencoded",
    "body": "username=admin%27+OR+1%3D1--&password=123"
  }'
```

### 4. Predicción Directa (`/predict`)
Recibe directamente el vector de las 27 características (features) ya calculadas. Ideal para integraciones con un Web Application Firewall (WAF) que ya extraiga las métricas internamente.

**Ejemplo de Vector Benigno:**
```bash
curl -X POST http://localhost:5082/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
        "method_is_get": 1,
        "method_is_post": 0,
        "method_is_put": 0,
        "url_length": 48,
        "url_param_count": 0,
        "url_pct_density": 0,
        "url_path_depth": 5,
        "url_query_length": 0,
        "url_has_query": 0,
        "url_has_pct27": 0,
        "url_has_pct3c": 0,
        "url_has_dashdash": 0,
        "url_has_script": 0,
        "url_has_select": 0,
        "content_length": 0,
        "content_pct_density": 0,
        "content_param_count": 0,
        "content_param_density": 0,
        "content_has_pct27": 0,
        "content_has_pct3c": 0,
        "content_has_dashdash": 0,
        "content_has_script": 0,
        "content_has_select": 0,
        "url_query_ratio": 0,
        "content_url_ratio": 0,
        "is_long_post": 0,
        "url_length_get": 48
    }
  }'
```

### 5. Aprobación del Blue Team (`/model/approve`)
> [!IMPORTANT]
> Este endpoint es de uso exclusivo del **Blue Team**. Una vez auditada la API con éxito, se ejecuta este comando para firmar el modelo actual cargado en memoria.

Inyecta automáticamente el tag `deployment_stage = approved` al modelo directamente en la base de datos de MLflow. Esto desbloquea el `dag_deploy_prod` para enviarlo a Producción.

```bash
curl -X POST http://localhost:5082/model/approve
```

## Entendiendo las Respuestas

Cada respuesta de predicción tiene el siguiente formato:

```json
{
  "prediction": 0, 
  "probability": 0.0821,
  "threshold": 0.2502,
  "model_version": "5",
  "latency_ms": 1.79
}
```

- **prediction**: `0` significa tráfico normal, `1` significa que se detectó un ataque.
- **probability**: Nivel de confianza del modelo sobre si es malicioso.
- **threshold**: El límite por encima del cual la probabilidad se marca como `1`. Al estar ajustado para alta sensibilidad (alto recall), este límite es de ~0.25.
- **latency_ms**: El tiempo que tomó hacer la inferencia y el escalado de características en tiempo real.
