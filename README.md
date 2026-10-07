# Martyr v5.0 — Meta-Análisis Médico PRISMA 2020

Sistema de meta-análisis sistemático médico de grado publicable, ejecutado enteramente en **Python puro**. Diseñado para OpenClaw. **No requiere R**.

## Características Principales

- **Pipeline PRISMA 2020** de 12 fases con **7 gates de aprobación obligatorios**
- **Motor estadístico Python puro**: scipy + statsmodels + numpy + pandas
- **Búsqueda paralela** reutilizada de Martyria v4.0 (PubMed/Cochrane/CT/Semantic Scholar)
- **Forest plots y funnel plots** nativos con matplotlib
- **Manuscrito APA 7** con PRISMA 2020 checklist
- **Calibración gold-standard** con κ de Cohen e ICC

## Filosofía de Diseño

1. **Rojo/Verde computados por Python, no leídos por LLM**
2. **7 gates de aprobación bloquean estructuralmente** — no avanzan sin firma
3. **Calibración gold-standard** responde "¿qué tan preciso es el agente?" con datos
4. **Python puro — cero dependencia de R**
5. **Reutiliza Martyria v4.0** — búsqueda, seminales, cache

## Instalación

```bash
# Dependencias (ya instaladas en tu sistema)
python3 -m pip install scipy statsmodels pandas matplotlib numpy lifelines

# Clonar/crear en skills/
cd ~/.openclaw/workspace/skills/martyr
```

## Uso Rápido

### Meta-análisis directo desde CSV

```bash
python3 martyr.py --data-file examples/aki_rrt_studies.csv --effect-type RR --model DL
```

### Pipeline PRISMA completo

```bash
python3 martyr.py \
  --topic "timing of renal replacement therapy in AKI" \
  --pico "P:ICU patients with AKI KDIGO stage 3;I:early RRT (<12h);C:late RRT;O:mortality 90-day" \
  --full-prisma
```

### Solo búsqueda

```bash
python3 martyr.py --topic "sepsis bundle compliance" --search-only
```

## Estructura de Directorios

```
martyr/
├── martyr.py              # Orquestador principal
├── SKILL.md               # Skill para OpenClaw
├── README.md              # Este archivo
├── requirements.txt       # Dependencias Python
├── scripts/
│   ├── stats/             # Motor estadístico
│   │   ├── pooling.py     # FE/RE con 5 estimadores
│   │   ├── effects.py     # Conversiones OR/RR/RD/d/g
│   │   ├── heterogeneity.py # I², τ², Q, H
│   │   └── __init__.py
│   ├── search/            # Búsqueda (de Martyria)
│   ├── extraction/        # Extracción de datos
│   ├── plots/             # Forest, funnel, PRISMA
│   ├── gate_reporter.py   # Sistema de 7 gates
│   └── ...
├── references/
│   └── GATES.md           # Protocolo de verificación
├── decisions/             # Decisiones aprobadas
├── signoffs/              # Firmas de aprobación
├── artefacts/             # Artefactos por gate
└── output/                # Resultados
```

## Pipeline de 12 Fases PRISMA

| Fase | Descripción | Gate |
|---|---|---|
| L1 | Protocolo PROSPERO + PICO | — |
| L2 | Búsqueda PRISMA-S | — |
| L3 | Ingesta + deduplicación | — |
| L4 | Screening doble ciego + κ | **SP1** |
| L5 | Extracción doble + ICC | **SP2** |
| L6 | Calibración gold-standard | **SP3** |
| L7 | RoB 2.0 / ROBINS-I | — |
| L8 | Efectos + modelo + I² | **SP4** |
| L9 | Subgrupos + metarregresión | **SP5** |
| L10 | Sesgo publicación + sensibilidad | **SP6** |
| L11 | GRADE + manuscrito APA 7 | **SP7** |
| L12 | AMSTAR 2 autoevaluación | — |

## Formato CSV de Entrada

```csv
study_id,author,year,n_i,n_c,events_i,events_c,effect_measure,rr,rr_ci_lower,rr_ci_upper,subgroup
AKIKI2016,Gaudry,2016,311,308,150,153,RR,0.98,0.83,1.16,early
ELAIN2016,Zarbock,2016,112,119,44,65,RR,0.72,0.55,0.95,early
STARRT2019,STARRT-AKI,2019,1465,1462,643,639,RR,1.00,0.92,1.09,early
IDEAL2020,IDEAL-ICU,2020,488,492,239,238,RR,1.01,0.88,1.16,early
```

## Dependencias

| Paquete | Versión | Uso |
|---|---|---|
| scipy | ≥1.17 | Pooling, distribuciones |
| statsmodels | ≥0.14 | Meta-regresión |
| pandas | ≥2.3 | Manipulación datos |
| numpy | ≥2.4 | Álgebra lineal |
| matplotlib | ≥3.10 | Forest/funnel plots |
| lifelines | ≥0.30 | Análisis supervivencia |

## Versión

v5.0.0 — 2026-09-22

**Philosofia**: Meta-análisis PRISMA publicable, Python puro, gates humanos reales, integrado con OpenClaw.
