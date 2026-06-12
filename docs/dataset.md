# Dataset: CSIC 2010

---

## Descripción General

El dataset **CSIC 2010** fue desarrollado en el **Instituto de Seguridad de la Información — CSIC** (España). Contiene miles de peticiones HTTP generadas automáticamente, dirigidas a una aplicación web de e-commerce, con el objetivo de servir como benchmark académico para la detección de anomalías y ataques web.

En este proyecto utilizamos un formato tabular pre-procesado del dataset, obtenido a través de Kaggle.

| Característica | Detalle |
|----------------|---------|
| **Origen** | Instituto de Seguridad de la Información — CSIC |
| **Fuente actual** | [Kaggle CSIC 2010 (formato CSV)](https://www.kaggle.com) |
| **Año original** | 2010 |
| **Peticiones normales** | 36,000 (~59%) |
| **Peticiones anómalas** | 25,065 (~41%) |
| **Total** | 61,065 requests |

### ¿Por qué un dataset balanceado?

El ratio de este dataset (59:41) no representa un entorno de producción real, donde el tráfico malicioso suele ser menor al 1% (99:1). Sin embargo, este balance artificial tiene ventajas operativas iniciales:

- **Training estable**: El modelo recibe ejemplos abundantes de ambas clases, lo que facilita el aprendizaje de las clases minoritarias sin depender inicialmente de técnicas de remuestreo sintético (SMOTE).
- **Baseline confiable**: Permite establecer métricas base claras antes de someter al modelo al rigor del desbalance de producción.

*(Nota: Dado que el modelo se enfrentará a tráfico desbalanceado en producción, el proyecto aplica calibración de threshold en etapas posteriores para mantener un falso positivo (FP rate) tolerable. Ver [Threshold Calibration](conceptos_threshold.md)).*

---

## Estructura de archivos y flujo de datos

A diferencia de un experimento en Jupyter Notebook, en PMT MLSecOps el dataset atraviesa un flujo MLOps de tres etapas:

```text
data/
├── raw/csic2010/                ← Datos originales
│   ├── csic_database.csv        ← CSV crudo (17 columnas)
│   ├── README.md                ← Documentación original
│   └── CHECKSUMS.sha256         ← Integridad
│
├── curated/csic2010/            ← Datos tras Stage 0 (Curado)
│   ├── curation_report.md       ← Reporte de escaneo PII y deduplicación
│   └── stage1_report.json
│
└── processed/csic2010/          ← Datos tras Stage 2 (Preprocess)
    └── features_v5.parquet      ← Dataset final con 27 features extraídas
```

### División del dataset (Splitting)
Aunque el CSIC 2010 original se distribuye en tres bloques (train normal, test normal, test anómalo), **este proyecto consolida todas las filas en un único CSV** y delega la división al pipeline automatizado. En el script `train_model_a.py`, el dataset se divide dinámicamente usando una partición estratificada **70/15/15** (Train/Validation/Test).

---

## Estructura Raw: Columnas del CSV

El archivo de entrada `csic_database.csv` consta de 17 columnas que representan componentes parseados de las peticiones HTTP.

| Columna | Descripción |
|---------|-------------|
| `Unnamed: 0` | Texto "Normal"/"Anomalous" (redundante, se descarta) |
| `Method` | Método HTTP (ej: GET, POST, PUT). *Nota EDA: el 100% de los PUT son ataques.* |
| `URL` | Request line con path y query string. |
| `content` | Body del request (vacío en métodos GET). |
| `classification` | Variable objetivo (0 = normal, 1 = ataque). Renombrada a `label` en el pipeline. |
| `cookie`, `host`, `Accept`... | Headers HTTP estándar parseados. |
| `lenght` | Content-Length *(Nota: typo "lenght" heredado del dataset original).* |

---

## Tipos de ataques cubiertos

Según la documentación original, el dataset inyecta anomalías que simulan ataques como:
- **Information Gathering**
- **Files Disclosure**
- **Cross-Site Scripting (XSS)**
- **SQL Injection (SQLi)**
- **CRLF Injection**
- **Cross-Site Request Forgery (CSRF)**
- **Parameter Tampering**

*(Nota: En este contexto, ataques como Path Traversal a menudo se clasifican dentro de "Files Disclosure").*

---

## Privacidad y PII (Curación)

Un hallazgo importante de la fase de curación (`dag_curate_dataset`) es la presencia de identificadores sensibles o de sesión en los datos brutos. 
- **JSESSIONID**: Presente en el 100% de las filas de la columna `cookie`.
- El reporte de curación detalla el tratamiento de PII (Personaly Identifiable Information) para garantizar un pipeline limpio.

*(Ver más detalles en: [Stage 0 — Curado del Dataset](stage_0_curation.md))*

---

## Limitaciones conocidas

El dataset CSIC 2010 es un benchmark robusto, pero presenta desafíos técnicos actuales:

| Limitación | Impacto | Mitigación en este proyecto |
|------------|---------|-----------------------------|
| **Antigüedad (2010)** | Faltan técnicas modernas orientadas a APIs (JSON body manipulation), GraphQL o HTTP desync. | **Red Team Agent:** Usa `CrewAI` para consultar repositorios modernos en GitHub (como *PayloadsAllTheThings*) y auditar la API con ataques del día a día. |
| **Morfología limitada** | Criticas por baja variedad en los paths y estructura frente a una red empresarial real. | **Feedback Loop:** Si la tasa de detección del Red Team cae por debajo del 85%, el sistema dispara una alerta de retrain. |
