# CSIC 2010 — HTTP Web Attack Dataset

## Fuente
- **Nombre:** HTTP CSIC 2010 Web Application Attacks
- **Organización:** CSIC (Spanish National Research Council)
- **URL original:** http://www.isi.csic.es/dataset/
- **Fuente de descarga:** https://www.kaggle.com/datasets/ispangler/csic-2010-web-application-attacks
- **Fecha de descarga:** 2026-04-09
- **Licencia:** Copyright authors — uso en investigación

## Descripción

Dataset de requests HTTP generados automáticamente para probar aplicaciones web.
Contiene tráfico normal y ataques contra una aplicación de e-commerce (tienda1).

## Archivos

| Archivo | Descripción | Registros |
|---|---|---|
| `csic_database.csv` | Dataset completo en formato CSV | 61.065 |

**Nota:** Esta versión de Kaggle es un CSV pre-procesado del dataset original
(el original viene en archivos .txt de HTTP raw separados por split train/test).

## Distribución de clases

| Label | Clase | Registros |
|---|---|---|
| 0 | Normal | 36.000 |
| 1 | Attack | 25.065 |

## Features

`Method`, `User-Agent`, `Pragma`, `Cache-Control`, `Accept`, `Accept-encoding`,
`Accept-charset`, `language`, `host`, `cookie`, `content-type`, `connection`,
`lenght`, `content`, `URL`, `classification`

## Tipos de ataques incluidos

SQL Injection, Buffer Overflow, Information Gathering, Files Disclosure,
CRLF Injection, XSS, Parameter Tampering, CSRF

## SHA-256

```
c420f0bc0464376de75b6c419a0ac226fe69fe12c8ac4908843273721e44e637  csic_database.csv
```
