# Conceptos Clave — Threshold Calibration

---

## ¿Qué es el threshold?

En un clasificador binario, el threshold es el valor de probabilidad a partir del cual el modelo decide que es un ataque.

```
Default: probability ≥ 0.50 → prediction = 1 (ataque)
Nuestro: probability ≥ 0.3002 → prediction = 1 (ataque)
```

---

## ¿Por qué calibrar?

Porque el threshold default (0.50) no es óptimo para seguridad. En seguridad, priorizamos **recall** (detectar todos los ataques posibles) aunque sea a costa de más falsos positivos.

---

## Proceso de calibración

1. Entrenar modelo con LightGBM
2. En el **validation set**, buscar el threshold que logra `recall ≥ 0.955`
3. Resultado: **threshold = 0.3002**

---

## Trade-off con threshold 0.3002

| Métrica | Valor |
|---------|-------|
| Recall (test) | 95.4% |
| FP rate (producción 99:1) | ~17.4% |
| Precision (producción 99:1) | ~5.5% |

---

## Threshold alternativo: 0.4723

| Threshold | Recall | FP rate | Precision |
|-----------|--------|---------|-----------|
| 0.3002 | 100% | 17.4% | 5.5% |
| 0.4723 | 96.3% | 12.7% | 7.5% |

Con threshold 0.4723 hay menos FP pero también menos recall.

---

## ¿Por qué 0.50 no es óptimo?

Con 0.50 el recall sería ~90%. Con 0.3002 el recall sube a 95.4%.

La diferencia: se detectan ~5% más de ataques.

**En seguridad, no detectar un ataque es más costoso que investigar un falso positivo.**