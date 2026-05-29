# Docker — PMT MLSecOps

Infraestructura local con Docker Compose.

---

## Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **postgres** | 5432 | PostgreSQL 15 (metastore compartido) |
| **mlflow** | 5081 | MLflow tracking server |
| **airflow-webserver** | 5080 | Airflow UI (admin / admin) |
| **airflow-scheduler** | — | Airflow scheduler |
| **nginx-artifacts** | 5083 | Proxy HTTP para artefactos MLflow |

---

## Quick start

```bash
# 1. Copiar variables de entorno
cd docker
cp .env.example .env

# 2. Levantar servicios
docker compose up -d

# 3. Esperar a que inicialicen (~30 segundos)
docker compose logs -f mlflow
docker compose logs -f airflow-webserver

# 4. Verificar que están levantados
docker compose ps
```

---

## URLs de acceso

- **MLflow UI**: http://localhost:5081
- **Airflow UI**: http://localhost:5080 (admin / admin)
- **Artefactos MLflow**: http://localhost:5083

---

## Comandos útiles

```bash
# Ver logs de un servicio
docker compose logs -f mlflow
docker compose logs -f airflow-webserver
docker compose logs -f airflow-scheduler

# Reiniciar un servicio
docker compose restart mlflow

# Rebuild si se cambiaron Dockerfiles
docker compose build mlflow
docker compose build airflow-webserver
docker compose build airflow-scheduler

# Bajar todo
docker compose down

# Bajar todo y eliminar volúmenes (LIMPIA TODO)
docker compose down -v

# Ver estado de los servicios
docker compose ps
```

---

## Estructura de directorios montados

```
../
├── dags/              → /opt/airflow/dags (Airflow)
├── src/               → /opt/airflow/src (código Python)
├── data/              → /opt/airflow/data (datasets, uploads)
└── mlflow-artifacts/  → /opt/mlflow/artifacts (artefactos MLflow)
```

---

## Credenciales por defecto

| Servicio | Usuario | Contraseña |
|----------|---------|------------|
| Airflow UI | admin | admin |
| PostgreSQL | airflow | airflow |

⚠️ **Cambiar en producción**: Editar `.env` antes de levantar.

---

## Troubleshooting

### "Connection refused" al mlflow

Esperar ~15 segundos a que PostgreSQL inicialice. El healthcheck está configurado con `condition: service_healthy`.

### Airflow no conecta a PostgreSQL

Verificar que el volumen `postgres-data` se creó correctamente:
```bash
docker compose ls
```

### MLflow no puede descargar artefactos

El volumen `mlflow-artifacts` debe estar compartido entre mlflow y nginx-artifacts. Verificar con:
```bash
docker compose exec mlflow ls /opt/mlflow/artifacts
```
