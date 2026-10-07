# PRISMA 2020 — Lo que el software puede vs NO puede verificar

## Items que el SOFTWARE PUEDE verificar automaticamente

| Item | Que verifica | Evidencia que produce Martyr |
|---|---|---|
| **4b** | Que buscaste en PubMed/Cochrane/etc | `search_records.csv` con timestamp, query, fuente, PMID |
| **6a** | Como extrajiste los datos | `calculation_log.csv` con formula usada en cada paso |
| **8b** | Que medida de efecto usaste | `pooled_results.json` dice "RR con IC 95%" |
| **13** | Cual fue el resultado del meta-analisis | `pooled_results.json` con k=4, RR=0.969, I2=42.1% |

## Items que REQUIEREN el MANUSCRITO (escrito por humano)

### Ejemplo 1: Item 3a — "Describe la JUSTIFICACION"

**Lo que PRISMA pide:**
> "Describe the rationale for the review in the context of existing knowledge"

**Lo que el SOFTWARE puede generar (plantilla):**
```
"Acute kidney injury (AKI) is common in ICU patients. The optimal 
timing of renal replacement therapy (RRT) remains controversial."
```

**Lo que el HUMANO debe agregar:**
```
"Previous studies have shown conflicting results. The ELAIN trial 
suggested benefit with early RRT (Zarbock et al., 2016), but the 
AKIKI and STARRT-AKI trials found no difference (Gaudry et al., 
2016; STARRT-AKI Investigators, 2020). These discrepancies may 
be due to differences in patient populations, definitions of AKI, 
and timing protocols."
```

**Por que el software NO puede hacer esto:** Requiere conocimiento del 
contexto clinico, la historia de la literatura, y la capacidad de 
identificar CONTRADICCIONES entre estudios.

---

### Ejemplo 2: Item 16 — "Discute las LIMITACIONES"

**Lo que PRISMA pide:**
> "Discuss the limitations of the review process and the evidence"

**Lo que el SOFTWARE puede generar (generico):**
```
"Limitations include heterogeneity between studies and potential 
publication bias."
```

**Lo que el HUMANO debe agregar:**
```
"Our review has several limitations. First, the definition of 'early' 
RRT varied across trials: ELAIN used KDIGO stage 2 + oliguria, while 
AKIKI used KDIGO stage 3. This clinical heterogeneity may explain the 
different results. Second, the IDEAL-ICU trial was stopped early for 
futility, which may have reduced power to detect smaller effects. 
Third, we did not have access to individual patient data, precluding 
time-to-event analyses."
```

**Por que el software NO puede hacer esto:** Requiere interpretacion 
clinica de por que los estudios difieren, conocimiento de que un 
estudio fue detenido temprano, y juicio sobre que limitaciones son 
MEDICAMENTE relevantes vs estadisticamente relevantes.

---

### Ejemplo 3: Item 17 — "Discute las IMPLICACIONES"

**Lo que PRISMA pide:**
> "Discuss the implications for practice, policy, and future research"

**Lo que el HUMANO debe escribir:**
```
"Our findings suggest that a strategy of initiating RRT only when 
indicated by traditional criteria (fluid overload, hyperkalemia, 
metabolic acidosis) is not inferior to early initiation based on 
KDIGO stages alone. This supports current guidelines that recommend 
watchful waiting rather than automatic RRT initiation."
```

**Por que el software NO puede hacer esto:** Requiere juicio clinico 
sobre que significa "no inferior" en terminos de PRACTICA CLINICA, 
no solo estadistica. Requiere conocimiento de guidelines actuales.

---

## El checklist PRISMA es como un dictamen de IMPUESTOS

| Analogia | Impuestos | PRISMA |
|---|---|---|
| **Lo que el SOFTWARE hace** | Calcula tu ISR, suma ingresos, aplica deducciones | Calcula RR, I2, p-value, genera forest plot |
| **Lo que el HUMANO debe hacer** | Firmar que los datos son correctos, explicar deducciones inusuales | Firmar que la busqueda fue exhaustiva, explicar por que excluiste un estudio, discutir implicaciones clinicas |
| **Responsabilidad** | Tu firmas bajo protesta de decir verdad | Tu firmas como autor del manuscrito |

## En resumen

**PRISMA 2020 NO es un estandar de CALCULOS.**
**PRISMA 2020 es un estandar de TRANSPARENCIA EN EL REPORTE.**

- El SOFTWARE puede y DEBE auditar los calculos ✅
- El SOFTWARE puede y DEBE generar logs de cada paso ✅
- El HUMANO debe escribir el manuscrito con interpretacion clinica ✅
- El HUMANO es responsable de las decisiones metodologicas ✅

**Martyr automatiza lo mecanico. El juicio clinico sigue siendo humano.**