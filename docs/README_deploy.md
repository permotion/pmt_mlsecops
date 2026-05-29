# Stage 7 - Despliegue a Producción

Una vez que el modelo candidato está en `staging` y la API (`model_serving.py`) ha sido validada exhaustivamente por el Blue Team y el equipo de Infraestructura sin incidentes ni falsos positivos críticos, se procede a la etapa de Producción.

## Flujo de Trabajo (Blue Team)

El proceso **no es 100% automático** por diseño; requiere la firma de responsabilidad (aprobación) por parte de un ingeniero de seguridad para evitar que un modelo envenenado o con demasiados falsos positivos tire abajo el tráfico de la empresa.

### Paso 1: Aprobar el Modelo en MLflow
1. Acceder a la interfaz de MLflow (`http://localhost:5081`).
2. Navegar a **Models** -> `model-csic`.
3. Buscar la versión que tenga el alias `staging`.
4. En la sección "Tags", agregar o modificar la key `deployment_stage` con el valor `approved`.

### Paso 2: Ejecutar el DAG de Promoción
Desde Apache Airflow, se debe gatillar el DAG **`dag_deploy_prod`**.

Este DAG realiza tres pasos:
1. **validate_approval**: Falla y aborta el pipeline si el modelo en staging no tiene explícitamente el tag `deployment_stage=approved`.
2. **promote_to_prod**: Mueve o copia el alias a `production` y registra en MLflow el tag `deployed_at` con el timestamp de la operación.
3. **notify_deployment**: Emite una alerta por SNS indicando al WAF que el nuevo modelo ya está activo y que pueden refrescar sus motores de inferencia contra la nueva URI.
