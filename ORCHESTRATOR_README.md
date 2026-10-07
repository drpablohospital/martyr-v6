# MARTYR Orchestrator - Pipeline Automatizado PRISMA 2020

## ¿Qué hace?

Convierte una pregunta clínica normal en un meta-análisis completo con metodología PRISMA:

**Entrada:** Pregunta clínica (ej: "Does dexamethasone reduce mortality in COVID-19?")
**Salida:** Meta-análisis con forest plot, funnel plot, manuscrito PRISMA, reporte de auditoría

## Uso

```bash
cd ~/.openclaw/workspace/skills/martyr

python3 scripts/automated_pipeline/orchestrator.py \
  --question "Tu pregunta clinica aqui" \
  --max-results 15 \
  --output-dir mi_analisis/
```

## Flujo Automático (6 pasos)

1. **PICO automático** — Detecta Población, Intervención, Comparador, Outcome
2. **Búsqueda PubMed** — Busca artículos reales via API de NCBI
3. **Filtrado** — Selecciona RCTs y meta-análisis
4. **Extracción** — Genera CSV con datos de estudios
5. **Meta-análisis** — Calcula efecto combinado, heterogeneidad, GRADE
6. **Manuscrito** — Genera manuscrito PRISMA 2020 + plots

## Archivos Generados

```
output/
└── mi_analisis/
    ├── evidence_report_TIMESTAMP.json    # Artículos encontrados (auditoría)
    ├── studies_TIMESTAMP.csv              # Datos para meta-análisis
    └── analysis_TIMESTAMP/
        ├── pipeline_summary_TIMESTAMP.json # Resultados estadísticos
        ├── manuscript_TIMESTAMP.md          # Manuscrito PRISMA
        ├── pipeline_log_TIMESTAMP.json      # Log de ejecución
        ├── forest_plot_*.png               # Forest plot
        └── funnel_plot_*.png              # Funnel plot
```

## Limitaciones Conocidas

- **Extracción de datos**: Los N y eventos son simulados (placeholders). 
  Para un análisis real, necesitas extraer manualmente los datos de cada artículo
  (número de pacientes, eventos en cada grupo) y actualizar el CSV.
  
- **Subgrupos**: Requieren datos de covariables (edad, severidad, etc.)

- **Sesgo de publicación**: Requiere errores estándar por estudio

- **AMSTAR 2**: Requiere evaluación manual

## Ejemplo de Preguntas que Funcionan

```bash
# COVID-19
python3 scripts/automated_pipeline/orchestrator.py \
  --question "Does dexamethasone reduce mortality in COVID-19?"

# Sepsis
python3 scripts/automated_pipeline/orchestrator.py \
  --question "Does early goal-directed therapy improve survival in sepsis?"

# AKI
python3 scripts/automated_pipeline/orchestrator.py \
  --question "Is early renal replacement therapy better than delayed in AKI?"

# Diabetes
python3 scripts/automated_pipeline/orchestrator.py \
  --question "Does tight glycemic control reduce mortality in ICU patients?"
```

## Estado

✅ Funcional — genera pipeline completo desde pregunta clínica
⚠️ Requiere revisión manual de datos extraídos para análisis real
