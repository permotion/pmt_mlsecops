# Matriz RACI

---

## Roles y responsabilidades

| Rol | Responsabilidad principal |
|-----|--------------------------|
| **MLOps** | Entrenamiento, registro de candidatos, mantenimiento de pipeline |
| **Blue Team** | Validación, promoción a producción, monitoreo en producción |
| **Red Team** | Búsqueda de payloads frescos, testing adversarial, detección de gaps |
| **Airflow** | Automatización del pipeline de entrenamiento y scheduling |

---

## Proceso: Detection Model Lifecycle

| Actividad | MLOps | Blue Team | Airflow | Red Team |
|-----------|:-----:|:---------:|:-------:|:--------:|
| 1. Trigger training | I | I | **R** | — |
| 2. Verify raw data | I | — | **R** | — |
| 3. Preprocess features | I | — | **R** | — |
| 4. Train model | I | — | **R** | — |
| 5. Evaluate criteria | I | — | **R** | — |
| 6. Register in Staging | I | — | **R** | — |
| 7. Notificar a Blue Team | I | I | **R** | — |
| 8. Revisar modelo en Staging | — | **R** | I | — |
| 9. Decidir aprobación/rechazo | — | **A** | — | — |
| 10. Promover a Production | — | **R/A** | — | — |
| 11. Archivar Production anterior | — | **R/A** | — | — |
| 12. API carga modelo Production | — | — | **R** | — |
| 13. Monitorear en producción | I | **R** | I | — |
| 14. Buscar payloads frescos | — | I | **R** | **R** |
| 15. Testar payloads contra API | — | I | **R** | **R** |
| 16. Generar FN Report | — | I | **R** | **R** |
| 17. Alertar si threshold superado | — | **R** | — | **R** |
| 18. Evaluar gaps del Red Team | — | **R** | I | — |
| 19. Solicitar re-training | **R** | C | — | I |

---

## Clave de códigos

| Código | Significado |
|--------|-------------|
| **R** | Responsible — Ejecuta la tarea directamente |
| **A** | Accountable — Rinde cuentas final, tiene autoridad para aprobar/rechazar |
| **C** | Consulted — Prove input antes de decisiones |
| **I** | Informed — Notificado de resultados |
| **—** | No involucrado |

---

## Métricas de monitoreo

| Métrica | Target | Responsable | Acción si excede |
|---------|--------|-------------|------------------|
| FP rate | < 20% | Blue Team | Recalibrar threshold |
| Recall | ≥ 0.95 | Blue Team | Solicitar re-training |
| Detection rate (Red Team) | ≥ 85% | Red Team | Alertar a Blue Team |