---
name: martyr
description: >
  Meta-análisis sistemático médico PRISMA 2020 completo en Python puro.
  Pipeline de 12 fases con 7 gates de aprobación obligatorios,
  extracción de afirmaciones clínicas (claims), evaluación GRADE por afirmación,
  análisis de subgrupos con covariables categóricas y continuas,
  metarregresión multivariable, y autoevaluación AMSTAR 2.
  Use para meta-análisis médico, revisión sistemática PRISMA,
  efectos combinados, forest plot, análisis heterogeneidad, subgrupos,
  evaluación de afirmaciones clínicas con nivel de evidencia.
license: MIT
metadata:
  author: Pablo
  version: 6.0.0
  stack: Python 3.12 + scipy + statsmodels + pandas + matplotlib + numpy
---

# MARTYR v6.0 — Meta-Análisis Médico PRISMA 2020 + Claims + Subgrupos + AMSTAR 2

Sistema de meta-análisis sistemático médico de grado publicable, ejecutado enteramente en Python.
Diseñado para OpenClaw. **No requiere R**.

## Filosofía de Diseño (5 Decisiones Clave)

1. **Rojo/Verde computados por Python, no leídos por LLM** — `scripts/stats/audit_engine.py`
2. **7 gates de aprobación bloquean estructuralmente** — `scripts/gate_reporter.py` + `preflight.py`
3. **Calibración gold-standard** responde "¿qué tan preciso es el agente?" con datos
4. **Python puro — cero R** — scipy, statsmodels, matplotlib
5. **Reutiliza Martyria v4.0** — búsqueda, seminales, cache

## Pipeline 14 Fases PRISMA (ACTUALIZADO v6.0)

| Fase | Qué hace | Salida | Puerta |
|---|---|---|---|
| L1 | Protocolo PROSPERO + PICO | 01_protocol.md | — |
| L2 | Búsqueda PRISMA-S 4 bases | 02_search.md | — |
| L3 | Ingesta + deduplicación | prisma_records.csv | — |
| L4 | Screening doble ciego + κ | 03_screening.md | **SP1** |
| L5 | Extracción doble + ICC | 04_extraction.md | **SP2** |
| L6 | Calibración gold-standard | 05_calibration.md | **SP3** |
| L7 | RoB 2.0 / ROBINS-I | 06_rob.md | — |
| L8 | Efectos + modelo + I²/τ²/PI | 07_model.md | **SP4** |
| **L8.5** | **Claim Extractor** | **claims_*.json** | — |
| **L8.6** | **Claim-Level GRADE** | **grade_claims_*.json** | — |
| L9 | Subgrupos + metarregresión | 08_moderators.md | **SP5** |
| L10 | Sesgo publicación + sensibilidad | 09_bias.md | **SP6** |
| L11 | GRADE global + manuscrito APA 7 | 10_grade.md | **SP7** |
| L12 | AMSTAR 2 autoevaluación | 11_amstar.md | — |

### Nuevas Fases v6.0

**Fase 8.5 — Claim Extractor:**
- Extrae afirmaciones clínicas individuales del meta-análisis
- Identifica: efecto principal, intervención, control, outcome, dirección
- Genera claims estructurados con metadatos de evidencia

**Fase 8.6 — Claim-Level GRADE:**
- Evalúa calidad de evidencia para CADA afirmación individual
- Usa inconsistencia real (I²) en vez de consistencia de dirección
- Asigna: STRONG / MODERATE / WEAK / VERY_WEAK por afirmación

---

## Uso

### Pipeline Completo v6.0 (Recomendado)

```bash
cd ~/.openclaw/workspace/skills/martyr

# Pipeline completo con análisis de subgrupos y AMSTAR 2
python3 scripts/pipeline_integrator.py --topic "Corticosteroides en Sepsis" \
  --pico "P:Sepsis;I:Corticosteroides;C:Placebo;O:Mortalidad" \
  --data-file examples/aki_rrt_studies.csv \
  --effect-type RR --model DL \
  --output-dir output/
```

**Salidas v6.0 generadas:**
- `pipeline_summary_*.json` — Resultados estadísticos completos
- `claims_*.json` — Afirmaciones clínicas extraídas
- `grade_claims_*.json` — Evaluación GRADE por afirmación
- `subgroup_analysis_*.json` — Análisis de subgrupos
- `amstar2_*.json` — Evaluación AMSTAR 2 (16 criterios)
- `manuscript_*.md` — Manuscrito PRISMA 2020
- `forest_plot_*.png` — Forest plot
- `funnel_plot_*.png` — Funnel plot

### Modo Automatizado

```bash
# Pipeline completo desde pregunta clínica
python3 scripts/automated_pipeline/orchestrator.py \
  --question "Does dexamethasone reduce mortality in COVID-19?" \
  --max-results 15 \
  --output-dir mi_analisis/
```

### Módulos Individuales

```bash
# Claim Extractor standalone
python3 scripts/claim_extractor.py \
  --data-file examples/aki_rrt_studies.csv \
  --effect-type RR \
  --output-dir output/

# Claim-Level GRADE standalone
python3 scripts/stats/claim_level_grade.py \
  --claims-file output/claims_*.json \
  --heterogeneity-file output/pipeline_summary_*.json \
  --output-dir output/

# Análisis de subgrupos standalone
python3 scripts/stats/subgroup_analysis.py \
  --data-file examples/test_subgroups.csv \
  --effect-type RR \
  --output-dir output/

# AMSTAR 2 standalone
python3 scripts/stats/amstar2.py \
  --data-file examples/aki_rrt_studies.csv \
  --output-dir output/
```

---

## Dependencias (requirements.txt)

```
scipy>=1.17.0,<2.0
statsmodels>=0.14.0,<1.0
pandas>=2.3.0,<3.0
matplotlib>=3.10.0,<4.0
numpy>=2.4.0,<3.0
lifelines>=0.30.0,<1.0
```

---

## Estructura de Directorios (ACTUALIZADA v6.0)

```
martyr/
├── martyr.py                    # Orquestador principal (legacy)
├── SKILL.md                     # Esta skill
├── README.md                    # Documentación extendida
├── AUDITORIA_SKILL_v6.0.md      # Auditoría técnica completa
├── IMPLEMENTATION_SUMMARY_v6.0.md  # Resumen de implementación
├── examples/
│   ├── aki_rrt_studies.csv      # 4 RCTs seminales AKI-RRT
│   ├── aki_rrt_raw.csv          # Datos brutos de extracción
│   ├── test_subgroups.csv       # Ejemplo con covariables
│   └── prisma_explanation.md    # Explicación PRISMA
├── scripts/
│   ├── automated_pipeline/
│   │   └── orchestrator.py      # Pipeline end-to-end
│   ├── stats/                   # Motor estadístico Python
│   │   ├── pooling.py           # FE/RE (DL, REML, HS, SJ, ML)
│   │   ├── effects.py           # Conversiones OR/RR/RD/d/g
│   │   ├── heterogeneity.py     # I², τ², Q, H, PI
│   │   ├── publication_bias.py  # Egger, PET-PEESE, trim-fill
│   │   ├── risk_of_bias.py      # RoB 2.0 / ROBINS-I + GRADE
│   │   ├── claim_level_grade.py # GRADE por afirmación [NUEVO v6.0]
│   │   ├── amstar2.py           # AMSTAR 2 evaluación [NUEVO v6.0]
│   │   └── subgroup_analysis.py # Subgrupos + metarregresión [NUEVO v6.0]
│   ├── plots/
│   │   ├── forest_plot.py       # Forest plot SVG/PNG
│   │   ├── funnel_plot.py       # Funnel plot
│   │   └── __init__.py
│   ├── search/                  # De Martyria v4.0
│   ├── screening/
│   ├── extraction/
│   ├── manuscript/
│   ├── claim_extractor.py       # Extracción de afirmaciones [NUEVO v6.0]
│   ├── pipeline_integrator.py   # Pipeline completo PRISMA + Claims
│   ├── gate_reporter.py         # Sistema de 7 gates
│   └── prisma_checklist.py      # Checklist PRISMA 2020
├── decisions/                   # Decisiones aprobadas
├── signoffs/                    # Firmas de aprobación
└── output/                      # Resultados
```

---

## Resultados de Prueba (AKI-RRT, 4 RCTs)

**Datos:** AKIKI 2016, ELAIN 2016, STARRT-AKI 2019, IDEAL-ICU 2020

| Métrica | Valor |
|---|---|
| Pooled RR | 0.969 [0.882-1.063] |
| p-value | 0.502 |
| I² | 42.8% |
| τ² | 0.0038 |
| Q | 5.25 (p=0.155) |
| Certeza GRADE | LOW |

**Claims extraídos (v6.0):**
- C001: Efecto principal (RR 0.969)
- C_early: Timing temprano vs tardío
- C_septic: Shock séptico
- C_COVID: COVID-19

**Subgrupos significativos (v6.0):**
- Intervención: Dexametasona (p=0.004)
- Control: Placebo vs Usual care
- Población: COVID-19

**AMSTAR 2:** Alta calidad (HIGH)

---

## Estado de Desarrollo (ACTUALIZADO v6.0)

| Componente | Estado | Archivo |
|------------|--------|---------|
| **Orquestador Automatizado** | ✅ Completo | `scripts/automated_pipeline/orchestrator.py` |
| **Claim Extractor** | ✅ **NUEVO v6.0** | `scripts/claim_extractor.py` |
| **Claim-Level GRADE** | ✅ **NUEVO v6.0** | `scripts/stats/claim_level_grade.py` |
| **Análisis de Subgrupos** | ✅ **NUEVO v6.0** | `scripts/stats/subgroup_analysis.py` |
| **AMSTAR 2** | ✅ **NUEVO v6.0** | `scripts/stats/amstar2.py` |
| Motor estadístico (pooling) | ✅ Completo | `scripts/stats/pooling.py` |
| Heterogeneidad | ✅ Completo | `scripts/stats/heterogeneity.py` |
| Sesgo de publicación | ✅ Completo | `scripts/stats/publication_bias.py` |
| Forest plot | ✅ Completo | `scripts/plots/forest_plot.py` |
| Funnel plot | ✅ Completo | `scripts/plots/funnel_plot.py` |
| Screening doble + κ | ✅ Completo | `scripts/screening/dual_screening.py` |
| Extracción doble + ICC | ✅ Completo | `scripts/extraction/dual_extraction.py` |
| RoB 2.0 / ROBINS-I | ✅ Completo | `scripts/stats/risk_of_bias.py` |
| GRADE global | ✅ Completo | `scripts/stats/risk_of_bias.py` |
| Pipeline integrador | ✅ Completo | `scripts/pipeline_integrator.py` |
| Generador de manuscrito | ✅ Completo | `scripts/manuscript/generate_manuscript.py` |
| 7 Gates | ✅ Completo | `scripts/gate_reporter.py` |
| ClinicalTrials.gov API v2 | ✅ Completo | `scripts/ctgov_api.py` |
| Red Bayesiana | ✅ Completo | `scripts/bayesian_network_meta.py` |

**Total: 20 módulos, todos funcionales**

---

## Versión

**v6.0.0 — 2026-10-06 — Claims + Subgrupos + AMSTAR 2**

**Nuevas capacidades v6.0:**
- 🔍 **Claim Extractor**: Extrae afirmaciones clínicas individuales del meta-análisis
- 📊 **Claim-Level GRADE**: Evalúa calidad de evidencia por afirmación (STRONG/MODERATE/WEAK/VERY_WEAK)
- 📈 **Subgrupos**: Análisis con covariables categóricas y continuas + metarregresión multivariable
- ⭐ **AMSTAR 2**: Autoevaluación de calidad metodológica (16 criterios)

**Filosofia**: Meta-análisis PRISMA publicable, Python puro, extracción real desde PubMed + CT.gov, gates humanos reales, evaluación de afirmaciones clínicas con nivel de evidencia.
