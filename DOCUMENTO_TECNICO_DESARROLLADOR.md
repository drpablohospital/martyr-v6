# Documento Técnico - Martyr v6.0
## Para Desarrolladores de Software

**Versión:** 6.0  
**Fecha:** 2026-10-06  
**Arquitectura:** Pipeline PRISMA 2020 en Python puro

---

## 1. ARQUITECTURA GENERAL

### 1.1 Visión de Alto Nivel

Martyr es un pipeline de meta-análisis sistemático que automatiza las 14 fases del proceso PRISMA 2020. Está diseñado como una colección de módulos independientes que se integran mediante un orquestador central.

```
┌─────────────────────────────────────────────┐
│           Pipeline PRISMA 2020              │
├─────────────────────────────────────────────┤
│  Fase 1  │ Protocolo PROSPERO + PICO        │
│  Fase 2  │ Búsqueda PRISMA-S (4 bases)     │
│  Fase 3  │ Ingesta + Deduplicación          │
│  Fase 4  │ Screening doble ciego + κ        │
│  Fase 5  │ Extracción doble + ICC           │
│  Fase 6  │ Calibración gold-standard        │
│  Fase 7  │ RoB 2.0 / ROBINS-I               │
│  Fase 8  │ Pooling + I²/τ²                  │
│  Fase 8.5│ Claim Extractor                    │
│  Fase 8.6│ Claim-Level GRADE                  │
│  Fase 9  │ Subgrupos + Metarregresión       │
│  Fase 10 │ Sesgo de publicación             │
│  Fase 11 │ Manuscrito APA 7                 │
│  Fase 12 │ AMSTAR 2 autoevaluación          │
└─────────────────────────────────────────────┘
```

### 1.2 Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Lenguaje | Python | 3.12+ |
| Estadísticas | scipy, statsmodels | >=1.17.0 |
| Visualización | matplotlib | >=3.10.0 |
| Datos | pandas, numpy | >=2.2.0, >=2.0.0 |
| Web scraping | requests, beautifulsoup4 | >=2.32.0, >=4.13.0 |
| Testing | pytest | >=8.3.0 |

### 1.3 Estructura de Directorios

```
martyr/
├── SKILL.md                          # Definición de skill (OpenClaw)
├── requirements.txt                  # Dependencias
├── README_USUARIO.md                 # Guía para usuarios
├── DOCUMENTO_TECNICO_DESARROLLADOR.md  # Este archivo
├── DOCUMENTO_METODOLOGICO.txt        # Documento para revistas
├── IMPLEMENTATION_SUMMARY_v6.0.md    # Resumen de implementación
├── AUDITORIA_SKILL_v6.0_FINAL.md     # Auditoría de calidad
│
├── scripts/                          # Código fuente
│   ├── __init__.py
│   ├── pipeline_integrator.py        # Orquestador principal
│   ├── claim_extractor.py            # Extractor de afirmaciones
│   ├── search/                       # Búsqueda bibliográfica
│   │   ├── pubmed_client.py
│   │   ├── cochrane_client.py
│   │   ├── clinicaltrials_client.py
│   │   └── semantic_scholar_client.py
│   ├── stats/                        # Análisis estadístico
│   │   ├── __init__.py
│   │   ├── pooling.py               # Modelos efectos
│   │   ├── heterogeneity.py         # I², τ²
│   │   ├── subgroup_analysis.py     # Subgrupos
│   │   ├── publication_bias.py      # Sesgo publicación
│   │   ├── claim_level_grade.py     # GRADE por claim
│   │   ├── amstar2.py               # AMSTAR 2
│   │   └── risk_of_bias.py          # RoB 2.0 / ROBINS-I
│   ├── plots/                        # Visualización
│   │   ├── __init__.py
│   │   ├── forest_plot.py
│   │   └── funnel_plot.py
│   ├── screening/                    # Screening dual
│   │   ├── __init__.py
│   │   └── dual_screening.py
│   ├── extraction/                   # Extracción dual
│   │   ├── __init__.py
│   │   └── dual_extraction.py
│   ├── manuscript/                   # Generación manuscrito
│   │   ├── __init__.py
│   │   └── generate_manuscript.py
│   └── utils/                        # Utilidades compartidas
│       ├── __init__.py
│       ├── data_loaders.py          # Carga y validación CSV
│       ├── json_utils.py            # Serialización JSON
│       └── logger.py               # Logging estructurado
│
├── tests/                            # Tests automatizados
│   ├── __init__.py
│   ├── conftest.py                  # Fixtures compartidos
│   ├── test_claim_extractor.py      # 15 tests
│   ├── test_claim_level_grade.py    # 19 tests
│   ├── test_subgroup_analysis.py    # 18 tests
│   └── test_amstar2.py             # 20 tests
│
├── examples/                         # Datos de ejemplo
│   └── aki_rrt_studies.csv         # Dataset AKI/RRT
│
└── biblioteca/                       # [NUEVO] Almacén de resultados
    ├── README.md
    └── .gitkeep
```

---

## 2. MÓDULOS PRINCIPALES

### 2.1 Pipeline Integrator (`pipeline_integrator.py`)

**Clase principal:** `PRISMAPipeline`

**Responsabilidad:** Orquesta las 14 fases del meta-análisis.

**Flujo de ejecución:**
```python
pipeline = PRISMAPipeline(
    topic="Corticosteroides en sepsis",
    pico="P:Sepsis;I:Corticoides;C:Placebo;O:Mortalidad",
    output_dir="output/"
)

result = pipeline.run(data_file="estudios.csv")
```

**Métodos clave:**

| Método | Fase | Descripción |
|--------|------|-------------|
| `run()` | Todas | Ejecuta pipeline completo |
| `phase2_search()` | 2 | Búsqueda en 4 bases de datos |
| `phase8_pooling()` | 8 | Meta-análisis con I² |
| `phase85_claim_extractor()` | 8.5 | Extrae afirmaciones clínicas |
| `phase86_claim_level_grade()` | 8.6 | Evalúa GRADE por afirmación |
| `phase9_subgroup_analysis()` | 9 | Análisis de subgrupos |
| `phase10_publication_bias()` | 10 | Evalúa sesgo de publicación |
| `phase12_amstar2()` | 12 | Autoevaluación AMSTAR 2 |

**Formato de salida:**
- `pipeline_result.json` — Resultado completo del pipeline
- `manuscript.md` — Manuscrito PRISMA en Markdown
- `pipeline_log.txt` — Log de ejecución
- `audit/` — Directorio con auditoría completa

### 2.2 Claim Extractor (`claim_extractor.py`)

**Clases principales:** `ClinicalClaimExtractor`, `EvidenceSynthesizer`

**Responsabilidad:** Extrae afirmaciones clínicas del meta-análisis y las estructura para evaluación GRADE.

**Flujo:**
```
Datos de estudios → Dirección del efecto → Magnitud del efecto →
Consistencia → Afirmaciones estructuradas (JSON)
```

**Formato de salida:**
```json
{
  "claims": [
    {
      "claim_id": "CLAIM_001",
      "claim_type": "intervention_effectiveness",
      "claim_text": "Los corticosteroides reducen la mortalidad en sepsis (RR 0.93, IC 95%: 0.87-0.99)",
      "direction": "benefit",
      "magnitude": "small",
      "consistency_score": 0.85,
      "supporting_studies": [...]
    }
  ],
  "meta": {
    "total_claims": 5,
    "extraction_date": "2026-10-06T18:00:00"
  }
}
```

### 2.3 Claim-Level GRADE (`stats/claim_level_grade.py`)

**Clase principal:** `ClaimLevelGRADE`

**Responsabilidad:** Evalúa la calidad de evidencia por cada afirmación individual usando el framework GRADE.

**5 Dominios de Evaluación:**
1. **Risk of Bias** — Riesgo de sesgo de estudios de soporte
2. **Inconsistency** — Heterogeneidad (I²) del meta-análisis
3. **Indirectness** — Indirectitud de la evidencia
4. **Imprecision** — Imprecisión (anchura IC)
5. **Publication Bias** — Sesgo de publicación

**Rating:**
- `HIGH` → `STRONG` recommendation
- `MODERATE` → `CONDITIONAL` recommendation
- `LOW` → `WEAK` recommendation
- `VERY_LOW` → `WEAK` recommendation

### 2.4 Subgrupos (`stats/subgroup_analysis.py`)

**Clase principal:** `SubgroupAnalysis`

**Responsabilidad:** Analiza efectos modificados por covariables categóricas y continuas.

**Métodos:**
- `add_categorical_covariate()` — Agrega covariable categórica
- `add_continuous_covariate()` — Agrega covariable continua
- `run_subgroup_analysis()` — Ejecuta análisis
- `run_moderator_regression()` — Meta-regresión multivariable

### 2.5 AMSTAR 2 (`stats/amstar2.py`)

**Clase principal:** `AMSTAR2Assessment`

**Responsabilidad:** Autoevalúa la calidad metodológica de la revisión sistemática.

**16 Criterios:**
- C1-C4: Críticos (protocolo, criterios, screening dual, extracción dual)
- C5-C10: Importantes (búsqueda, riesgo sesgo, fuentes, duplicados, síntesis)
- C11-C16: Menores (conflictos, financiamiento, etc.)

**Rating global:**
- `high` — Calidad alta
- `moderate` — Calidad moderada
- `low` — Calidad baja
- `critically_low` — Calidad críticamente baja

---

## 3. UTILIDADES COMPARTIDAS (`scripts/utils/`)

### 3.1 Data Loaders (`data_loaders.py`)

```python
# Cargar estudios desde CSV
studies = load_studies("estudios.csv")

# Validar datos de entrada
is_valid, errors = validate_studies_data(studies)
```

**Schema requerido para CSV:**
- `study_id` (string) — Identificador único
- `pmid` (string) — PubMed ID
- `title` (string) — Título del estudio
- `author` (string) — Primer autor
- `year` (int) — Año de publicación
- `effect_size` (float) — Tamaño del efecto (RR/OR/HR)
- `ci_lower` (float) — Límite inferior IC 95%
- `ci_upper` (float) — Límite superior IC 95%
- `n_treatment` (int) — Tamaño grupo tratamiento
- `n_control` (int) — Tamaño grupo control
- `events_treatment` (int) — Eventos en tratamiento
- `events_control` (int) — Eventos en control
- `intervention` (string) — Descripción intervención
- `control` (string) — Descripción control

### 3.2 JSON Utils (`json_utils.py`)

```python
# Convertir tipos NumPy a Python nativos
result = to_python_types(claims_data)

# Guardar JSON de forma segura (maneja booleanos NumPy)
save_json_safe(result, "claims.json")
```

### 3.3 Logger (`logger.py`)

```python
# Configurar logger
logger = setup_logger("martyr", log_file="pipeline.log")

# Usar PipelineLogger para secciones
pl = PipelineLogger("martyr", output_dir="output/")
pl.section("Fase 8: Pooling")
pl.info("Calculando efecto combinado...")
```

---

## 4. INTERFAZ DE LÍNEA DE COMANDOS

### 4.1 Pipeline Completo

```bash
python scripts/pipeline_integrator.py \
  --topic "Corticosteroides en sepsis" \
  --pico "P:Sepsis;I:Corticoides;C:Placebo;O:Mortalidad" \
  --data-file examples/aki_rrt_studies.csv \
  --output-dir output/
```

### 4.2 Claim Extractor (standalone)

```bash
python scripts/claim_extractor.py \
  --input estudios.csv \
  --output output/claims/
```

### 4.3 Tests

```bash
# Todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/test_claim_extractor.py -v
pytest tests/test_claim_level_grade.py -v
pytest tests/test_subgroup_analysis.py -v
pytest tests/test_amstar2.py -v
```

---

## 5. FORMATOS DE DATOS

### 5.1 Entrada: CSV de Estudios

```csv
study_id,pmid,title,author,year,effect_size,ci_lower,ci_upper,n_treatment,n_control,events_treatment,events_control,intervention,control
STUDY001,12345678,"Trial of Steroids","Smith J",2020,0.93,0.87,0.99,500,500,45,48,"Hydrocortisone","Placebo"
```

### 5.2 Salida: Pipeline Result (JSON)

```json
{
  "topic": "Corticosteroides en sepsis",
  "phases_completed": [1, 2, 3, 4, 5, 6, 7, 8, 8.5, 8.6, 9, 10, 11, 12],
  "meta_analysis": {
    "pooled_effect": 0.93,
    "ci_lower": 0.87,
    "ci_upper": 0.99,
    "p_value": 0.023,
    "i2": 42.8,
    "tau2": 0.015,
    "model": "random_effects"
  },
  "claims": [...],
  "subgroup_analysis": {...},
  "publication_bias": {...},
  "amstar2": {...},
  "manuscript": "...",
  "audit": {
    "pipeline_log": "output/pipeline_log.txt",
    "claim_files": "output/claims/",
    "grade_files": "output/grade/"
  }
}
```

---

## 6. TESTING

### 6.1 Estrategia de Testing

| Tipo | Cobertura | Archivos |
|------|-----------|----------|
| Unit tests | Módulos individuales | `test_*.py` |
| Fixtures | Datos de prueba compartidos | `conftest.py` |
| Integration | Pipeline completo | `test_pipeline.py` |

### 6.2 Fixtures Disponibles

```python
# conftest.py
@pytest.fixture
def sample_studies():
    """10 estudios de ejemplo."""
    return [...]

@pytest.fixture
def sample_claims():
    """Claims extraídos de ejemplo."""
    return [...]

@pytest.fixture
def mock_meta_analysis():
    """Resultado de meta-análisis mock."""
    return {...}
```

---

## 7. EXTENSIÓN Y CUSTOMIZACIÓN

### 7.1 Agregar Nuevo Módulo Estadístico

```python
# scripts/stats/nuevo_modulo.py
class NuevoAnalisis:
    def __init__(self, studies):
        self.studies = studies
    
    def calcular_metrica(self):
        # Implementación
        return resultado
```

### 7.2 Integrar al Pipeline

```python
# En pipeline_integrator.py
from stats.nuevo_modulo import NuevoAnalisis

def phase_nuevo(self):
    analisis = NuevoAnalisis(self.studies)
    resultado = analisis.calcular_metrica()
    self.results["nuevo"] = resultado
```

---

## 8. DEPURACIÓN Y TROUBLESHOOTING

### 8.1 Logs de Pipeline

Cada ejecución genera:
- `pipeline_log.txt` — Log completo con timestamps
- `pipeline_result.json` — Resultado estructurado
- `audit/` — Directorio con auditoría

### 8.2 Niveles de Logging

| Nivel | Uso |
|-------|-----|
| DEBUG | Detalles de cálculos estadísticos |
| INFO | Progreso de fases |
| WARNING | Datos incompletos, asunciones |
| ERROR | Fallos que detienen el pipeline |

### 8.3 Verificación Post-Ejecución

```bash
# Verificar que todos los archivos se generaron
ls output/
# pipeline_result.json
# manuscript.md
# pipeline_log.txt
# audit/
# claims/
# grade/
# plots/

# Verificar integridad JSON
python -c "import json; json.load(open('output/pipeline_result.json'))"
```

---

## 9. REFERENCIAS TÉCNICAS

| Estándar | Implementación |
|----------|---------------|
| PRISMA 2020 | 14 fases del pipeline |
| GRADE | Claim-Level GRADE (5 dominios) |
| AMSTAR 2 | 16 criterios autoevaluados |
| PRISMA-S | Búsqueda en 4 bases de datos |
| RoB 2.0 | Evaluación riesgo de sesgo |

---

*Documento técnico para desarrolladores. Martyr v6.0*
