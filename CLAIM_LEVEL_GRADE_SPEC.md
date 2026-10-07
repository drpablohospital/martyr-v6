# Claim-Level GRADE - Especificación Técnica

## Propósito
Evaluar la calidad de evidencia y fuerza de recomendación para cada afirmación extraída por el Claim Extractor.

## Input
- JSON del Claim Extractor (`claims_extracted_*.json`)
- Datos adicionales del pipeline (RoB, heterogeneidad, sesgo de publicación)

## Output
- JSON con evaluación GRADE por afirmación:
  ```json
  {
    "claim_grades": [
      {
        "claim_id": "C001",
        "claim_text": "RRT temprana reduce mortalidad vs RRT tardía",
        "grade_assessment": {
          "evidence_quality": "low",
          "downgrades": [
            {"factor": "risk_of_bias", "severity": 1, "reason": "2 estudios con alto RoB"},
            {"factor": "inconsistency", "severity": 1, "reason": "I²=43%, heterogeneidad moderada"},
            {"factor": "imprecision", "severity": 1, "reason": "IC cruza nulo"}
          ],
          "upgrades": [],
          "final_rating": "low",
          "recommendation_strength": "weak",
          "rationale": "Evidencia de baja calidad debido a riesgo de sesgo, inconsistencia e imprecisión"
        }
      }
    ]
  }
  ```

## Reglas GRADE para Claim-Level

### Calidad de Evidencia (4 niveles)
- **HIGH**: Muy confiado en que el efecto real está cerca del estimado
- **MODERATE**: Moderadamente confiado
- **LOW**: Confiabilidad limitada
- **VERY_LOW**: Muy poca confiabilidad

### Factores de Downgrade
1. **Riesgo de sesgo** (-1 o -2)
   - -1: Algunos estudios con alto RoB
   - -2: La mayoría con alto RoB

2. **Inconsistencia** (-1 o -2)
   - -1: I² 30-60% o direcciones opuestas
   - -2: I² > 60% o estimaciones incompatibles

3. **Indirectitud** (-1 o -2)
   - -1: Población/intervención/outcome diferente
   - -2: Múltiples aspectos indirectos

4. **Imprecisión** (-1 o -2)
   - -1: CI cruza nulo o pocos eventos
   - -2: Ambos

5. **Sesgo de publicación** (-1)
   - -1: Evidencia de sesgo (Egger p<0.10, funnel asimétrico)

### Factores de Upgrade (solo observacionales)
1. **Magnitud grande del efecto** (+1 o +2)
2. **Dosis-respuesta** (+1)
3. **Confusión residual** (+1)

### Fuerza de Recomendación
- **Strong**: Beneficio claro > riesgo
- **Conditional**: Balance incierto o valores varían
- **Weak**: Evidencia muy débil o incierta

## Cálculo de Recomendación

```python
def calculate_recommendation(claim, grade):
    # Si evidencia HIGH → Strong (si beneficio claro)
    # Si evidencia MODERATE → Strong o Conditional
    # Si evidencia LOW → Conditional o Weak
    # Si evidencia VERY_LOW → Weak
    
    # Considerar también:
    # - Magnitud del efecto
    # - Riesgo de eventos adversos
    # - Preferencias del paciente
    # - Costo/recursos
```

## Integración con Pipeline

1. El Claim Extractor genera afirmaciones
2. Este módulo evalúa cada afirmación con GRADE
3. El Pipeline Integrator combina ambos en el manuscrito final

## Archivos de Salida

Para cada ejecución:
1. `grade_claim_level_YYYYMMDD_HHMMSS.json` - Evaluación GRADE
2. `grade_explanation_YYYYMMDD_HHMMSS.txt` - Explicación textual
3. `grade_table_YYYYMMDD_HHMMSS.md` - Tabla para manuscrito
