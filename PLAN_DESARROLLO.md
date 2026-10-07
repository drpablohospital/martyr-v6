# Plan de Desarrollo Martyr v5.0

## Fase 1: Generación de Visualizaciones (Forest/Funnel Plots)
- Implementar scripts/plots/forest_plot.py
- Implementar scripts/plots/funnel_plot.py  
- Integrar con martyr.py
- Probar con dataset AKI-RRT

## Fase 2: Screening Doble Ciego (κ de Cohen)
- Implementar scripts/screening/dual_screening.py
- Cálculo de kappa de Cohen con 2 investigadores
- Exportar a CSV con resolución de conflictos

## Fase 3: Extracción Doble + ICC
- Implementar scripts/extraction/dual_extraction.py
- Cálculo de ICC para concordancia entre extractores

## Fase 4: RoB 2.0 / ROBINS-I + GRADE
- Implementar evaluación de riesgo de sesgo
- Implementar sistema GRADE para certeza de evidencia

## Fase 5: Pipeline Completo y Manuscrito
- Integrar todo en pipeline end-to-end
- Generar manuscrito APA 7 con PRISMA checklist
- Implementar AMSTAR 2 autoevaluación

## Fase 6: Testing y Validación
- Probar pipeline completo con tema nuevo
- Validar resultados contra calculadoras estándar
