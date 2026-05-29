# Dataset Curation Report — CSIC 2010

**Fecha:** 2026-05-27 12:22:27
**Dataset:** `/opt/airflow/data/raw/csic2010/csic_database.csv`
**Total de filas:** 61,065

---

## Resumen

Este reporte documenta el análisis de PII (Personally Identifiable Information) y
referencias a empresas/organizaciones en el dataset CSIC 2010.

**Nota:** Este DAG solo escanea y reporta. No modifica el dataset.

---

## PII Encontrado

| Tipo de PII | Occurrencias | Estado |
|-------------|--------------|--------|
| Session tokens JSESSIONID | 61,065 | ✅ ENCONTRADO |
| Números de teléfono | 68,997 | ✅ ENCONTRADO |
| Direcciones de email | 0 | ❌ NO ENCONTRADO |
| Direcciones IP | 0 | ❌ NO ENCONTRADO |

### Detalle de hallazgos


#### Session tokens JSESSIONID
Ocurrencias: 61,065

Ejemplos (primeros 3):
```
1. JSESSIONID=1F767F17239C9B670A39E9B10C3825F4
```
```
2. JSESSIONID=81761ACA043B0E6014CA42A4BCD06AB5
```
```
3. JSESSIONID=933185092E0B668B90676E0A2B0767AF
```

#### Números de teléfono
Ocurrencias: 68,997

Ejemplos (primeros 3):
```
1. modo=insertar&precio=2672&B1=Pasar+por+caja
```
```
2. modo=registro&login=cen&password=40a5E&nombre=Nurit&apellidos=Ferrandez+Caba%F1as&email=tarpey%40bwd
```
```
3. modo=registro&login=de_la&password=roder%F3n&nombre=Franklin&apellidos=Canella&email=pockaj-bushman%
```

---

## Empresas y Organizaciones Buscadas

| Empresa/Organización | Estado | Columnas |
|---------------------|--------|----------|
| hackademy | ✅ ENCONTRADO | URL |
| ekoparty | ✅ ENCONTRADO | URL |
| csic | ❌ NO ENCONTRADO | - |
| consejo superior de investigaciones científicas | ❌ NO ENCONTRADO | - |
| universidad de granada | ❌ NO ENCONTRADO | - |

### Detalle de empresas


#### hackademy
✅ **ENCONTRADO**
Columnas: URL
Muestra:
```
http://plataformahackademy.ekoparty.org/tienda1/miembros/salir.jsp/ HTTP/1.1
```

#### ekoparty
✅ **ENCONTRADO**
Columnas: URL
Muestra:
```
http://plataformahackademy.ekoparty.org/tienda1/miembros/salir.jsp/ HTTP/1.1
```

#### csic
❌ **NO ENCONTRADO** — No hay referencias a esta empresa/organización en el dataset.

#### consejo superior de investigaciones científicas
❌ **NO ENCONTRADO** — No hay referencias a esta empresa/organización en el dataset.

#### universidad de granada
❌ **NO ENCONTRADO** — No hay referencias a esta empresa/organización en el dataset.

---

## Balance de Clases

| Clase | Cantidad | Porcentaje |
|-------|----------|------------|
| Normal | 36,000 | 59.0% |
| Ataque | 25,065 | 41.0% |
| **Total** | **61,065** | **100%** |

---

## Conclusiones

### ⚠️ Hallazgos importantes

Se encontró PII del siguiente tipo: session_token, phone.
**Acción requerida:** Evaluar si estos datos deben ser removidos o anonimizados antes del training.

Se encontraron referencias a: hackademy, ekoparty.
**Acción requerida:** Verificar que estos datos son legítimos para uso en training.

---

## Sign-off

- [ ] MLOps (revisión de hallazgos completada)
- [ ] Decisión: ¿El dataset requiere sanitización adicional?

