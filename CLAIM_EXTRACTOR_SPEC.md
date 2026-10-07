# Claim Extractor - Especificación Técnica

## Propósito
Extraer afirmaciones clínicas estructuradas desde datos de estudios para evaluación con GRADE.

## Input
- CSV con datos extraídos de estudios (efectos, outcomes, poblaciones, intervenciones)
- Estructura esperada:
  ```csv
  study_id,pmid,intervention,control,outcome,effect_size,ci_lower,ci_upper,n_total,population,subgroup_notes
  ```

## Output
- JSON con afirmaciones estructuradas:
  ```json
  {
    "claims": [
      {
        "claim_id": "C001",
        "claim_text": "Dexametasona reduce mortalidad vs placebo en COVID-19 severo",
        "claim_type": "efficacy|safety|dosing|subgroup",
        "direction": "favors_intervention|favors_control|no_difference",
        "magnitude": "large|moderate|small|uncertain",
        "supporting_studies": [
          {
            "study_id": "RECOVERY",
            "pmid": "PMID3245011",
            "effect_size": 0.83,
            "ci_lower": 0.75,
            "ci_upper": 0.92,
            "weight": 0.45,
            "consistency": "consistent|inconsistent"
          }
        ],
        "consistency_score": 0.85,
        "heterogeneity": {"I2": 25, "p": 0.18},
        "clinical_significance": "high|moderate|low|unclear",
        "confidence_level": "high|moderate|low|very_low"
      }
    ],
    "meta": {
      "total_claims": 5,
      "total_studies_analyzed": 12,
      "extraction_date": "2026-10-06",
      "version": "1.0"
    }
  }
  ```

## Tipos de Afirmaciones a Extraer

### 1. Eficacia Principal
- "[Intervención] es superior/inferior/no diferente a [Control] para [Outcome] en [Población]"
- Basada en: Efecto combinado del meta-análisis + IC

### 2. Seguridad
- "[Intervención] se asocia con mayor/igual/menor riesgo de [Evento adverso]"
- Basada en: Datos de eventos adversos por estudio

### 3. Dosis-Respuesta
- "Dosis de [X-Y] se asocia con mayor beneficio que otras dosis"
- Basada en: Meta-regresión por dosis

### 4. Subgrupos
- "En [Subgrupo específico], el efecto de [Intervención] es [mayor/igual/menor]"
- Basada en: Análisis de subgrupos (Q-between)

### 5. Comparaciones Indirectas (Red)
- "[Intervención A] vs [Intervención B] mediante comparación indirecta"
- Basada en: Meta-análisis en red

## Algoritmo de Extracción

```
1. Cargar datos de estudios (CSV)
2. Agrupar estudios por outcome
3. Para cada outcome:
   a. Calcular efecto combinado (si no existe)
   b. Determinar dirección del efecto
   c. Calcular consistencia entre estudios
   d. Evaluar heterogeneidad
   e. Generar afirmación principal
4. Para datos de dosis:
   a. Ejecutar meta-regresión
   b. Si pendiente significativa → afirmación dosis-respuesta
5. Para covariables:
   a. Ejecutar análisis de subgrupos
   b. Si Q-between significativo → afirmación de subgrupo
6. Para eventos adversos:
   a. Calcular riesgo combinado
   b. Generar afirmación de seguridad
7. Exportar JSON con todas las afirmaciones
```

## Reglas de Consistencia

- **Consistente**: Todos los estudios apuntan en la misma dirección (aunque magnitudes varíen)
- **Mayoritariamente consistente**: >75% de estudios en misma dirección
- **Inconsistente**: <75% en misma dirección o heterogeneidad significativa (I2 > 50%)

## Reglas de Significación Clínica

- **Large**: RR < 0.70 o RR > 1.43 (o equivalente en OR/HR)
- **Moderate**: RR 0.70-0.85 o 1.18-1.43
- **Small**: RR 0.85-0.95 o 1.05-1.18
- **Uncertain**: RR cruza 1.0 o CI muy amplio

## Archivos de Salida (Auditoría Completa)

Para cada ejecución del Claim Extractor:
1. `claims_extracted_YYYYMMDD_HHMMSS.json` - Afirmaciones finales
2. `claims_extraction_log_YYYYMMDD_HHMMSS.txt` - Log del proceso
3. `claims_source_mapping_YYYYMMDD_HHMMSS.csv` - Mapeo afirmación → estudios
4. `claims_intermediate_YYYYMMDD_HHMMSS.json` - Datos intermedios

## Integración con GRADE

Cada afirmación generada incluye placeholder para:
- `evidence_assessment` → Se llena con ClaimLevelGRADE
- `recommendation_strength` → Se calcula post-GRADE

## Test de Validación

Input de prueba: Datos RECOVERY + SOLIDARITY (dexamethasone COVID-19)
Afirmaciones esperadas:
1. "Dexametasona reduce mortalidad en COVID-19 severo" (efficacy)
2. "Dosis de 6mg IV/PO es efectiva" (dosing)
3. "Efecto consistente en subgrupos por severidad" (subgroup)
