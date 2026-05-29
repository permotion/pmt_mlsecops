# Resultados — Stage 1: Curation

---

Esta sección documenta los outputs y hallazgos del Stage 1 del pipeline. Los resultados se documentan a nivel estructural — mostrando qué información genera cada stage y qué análisis es posible extraer — sin exponer datos sensibles del dataset.

---

## Stage 1 — Curation: `dag_curate_dataset`

### Output: `curation_report.md`

El script `curate_dataset.py` genera un reporte en Markdown con el siguiente contenido:

#### Sección 1: Header

```markdown
**Fecha:** YYYY-MM-DD HH:MM:SS
**Dataset:** data/raw/csic2010/csic_database.csv
**Total de filas:** 61,065
```

#### Sección 2: PII Encontrado

Tabla que enumera cada tipo de PII escaneado:

| Tipo de PII | Occurrencias | Estado |
|-------------|--------------|--------|
| Session tokens JSESSIONID | ~61,065 | ✅ ENCONTRADO |
| Teléfonos | Varía | ⚠️ POSIBLE FALSO POSITIVO |
| Emails | 0 | ❌ NO ENCONTRADO |
| IPs | 0 | ❌ NO ENCONTRADO |

**Análisis:** Los session tokens aparecen en todos los registros porque el dataset original fue generado con sesiones sintéticas. **No representan PII real** — son placeholders del dataset de investigación.

#### Sección 3: Empresas y Organizaciones

| Empresa/Organización | Estado | Columnas |
|---------------------|--------|----------|
| hackademy | ✅ ENCONTRADO | host |
| ekoparty | ✅ ENCONTRADO | host |
| csic | ✅ ENCONTRADO | varias |
| universidad de granada | ⚠️ ENCONTRADO | varias |

**Análisis:** Las menciones a Hackademy y Ekoparty aparecen en el hostname sintético `plataformahackademy.ekoparty.org`. Este hostname **no representa datos reales** — es un placeholder sintético creado para generar el dataset. CSIC aparece porque es la institución creadora del dataset.

#### Sección 4: Balance de Clases

```markdown
| Clase | Cantidad | Porcentaje |
|-------|----------|------------|
| Normal | 36,000 | 59.0% |
| Ataque | 25,065 | 41.0% |
| **Total** | **61,065** | **100%** |
```

**Análisis:** El dataset tiene un desbalance leve (59/41). No requiere técnicas de oversampling como SMOTE — con `class_weight='balanced'` es suficiente.

#### Sección 5: Conclusiones

```markdown
### ⚠️ Hallazgos importantes

Se encontró PII del siguiente tipo: session_token.
**Acción requerida:** Evaluar si estos datos deben ser removidos o anonimizados antes del training.

Se encontraron referencias a: hackademy, ekoparty.
**Acción requerida:** Verificar que estos datos son legítimos para uso en training.
```

**Análisis:** El reporte indica que los session tokens son ubiquitous pero no sensibles (son sintéticos). Las menciones a empresas son en datos de contexto, no en payloads de ataque.

#### Sección 6: Sign-off

```markdown
- [ ] MLOps (revisión de hallazgos completada)
- [ ] Decisión: ¿El dataset requiere sanitización adicional?
```

### Estructura de archivos generados

```
data/curated/csic2010/
└── curation_report.md   ← output del stage
```

---

## Responsable

**MLOps** — curado y revisión de hallazgos del dataset