# Protocolo de Verificación — 7 Gates Obligatorios

Esta skill **no avanza sola**. En cada gate debes detenerte, mostrar el estado actual, y pedir confirmación explícita al usuario antes de continuar. No asumas aprobación. No resumas por encima. No saltes gates.

---

## Formato Obligatorio en Cada Gate

```
━━━ GATE [N]: [NOMBRE] ━━━
Estado: [qué se hizo]
Artefacto: [archivo o tabla generada]
Hallazgos clave: [bullets]
⚠️ Acción requerida: [qué debe revisar el usuario]
¿Apruebas y continúo? (sí / no / ajustar)
```

---

## GATE 1 — Congelamiento de la Estrategia de Búsqueda

**Antes de buscar nada.**

- Presenta la pregunta PICO/PECO reformulada.
- Muestra los términos MeSH, palabras clave, operadores booleanos y filtros propuestos.
- Muestra las bases de datos objetivo (PubMed como mínimo, según `martyria`).
- ⚠️ El usuario debe aprobar la estrategia. Una vez aprobada, **queda congelada**: no se modifica sin volver a este gate.

---

## GATE 2 — Consistencia del Cribado

**Después del cribado por título/abstract.**

- Reporta número inicial, duplicados eliminados, excluidos por título/abstract, y seleccionados para texto completo.
- Si hubo doble cribado, reporta **κ de Cohen** y discrepancias.
- Muestra el diagrama de flujo PRISMA en borrador.
- ⚠️ El usuario valida criterios de inclusión/exclusión aplicados y resuelve empates.

---

## GATE 3 — Calibración de Extracción

**Antes de extraer todos los datos.**

- Extrae completamente **3 estudios piloto**.
- Muestra la tabla de extracción: tamaño de efecto, IC, n, diseño, riesgo de sesgo preliminar.
- ⚠️ El usuario confirma que el formato y los criterios de extracción son correctos. Solo entonces se extrae el resto.

---

## GATE 4 — Verificación Numérica

**Antes de correr el modelo final.**

- Presenta la matriz de datos consolidada (estudio, efecto, varianza, peso).
- Muestra el script/método que se usará (`scipy.stats`/`statsmodels`) y los parámetros elegidos.
- ⚠️ El usuario revisa que **los números coincidan con los papers originales**. Este gate atrapa errores de dedo y de unidades.

---

## GATE 5 — Modelo y Heterogeneidad

**Después de correr el análisis principal.**

- Reporta: efecto agrupado, IC 95%, I², τ², intervalo de predicción, Q.
- Muestra forest plot.
- Si I² es alto, presenta subgrupos o meta-regresión exploratoria.
- ⚠️ El usuario decide si el modelo es defendible o si hay que ajustar (efectos fijos vs aleatorios, outliers, sensitivity analysis).

---

## GATE 6 — Sesgo de Publicación y Certeza

**Antes de interpretar.**

- Funnel plot, Egger, trim-and-fill (si aplica).
- Evaluación GRADE: certeza alta/moderada/baja/muy baja, con justificación por dominio.
- ⚠️ El usuario valida el juicio de certeza. No se redacta discusión sin esto.

---

## GATE 7 — Cierre e Interpretación

**Antes de entregar.**

- Borrador completo con PRISMA 2020 (27 ítems) chequeado uno por uno.
- Limitaciones, implicaciones clínicas, conflicto de interés, financiamiento.
- Limpieza final de citas y referencias.
- ⚠️ El usuario da el visto bueno final. Sin esto, la salida se marca como **BORRADOR**, nunca como final.

---

## Reglas Transversales

### Si dice "ajustar"
Vuelves al paso correspondiente, corriges, y **vuelves a presentar el mismo gate**. No avanzas con deuda pendiente.

### Si un gate no aplica
Lo declaras explícitamente como:
```
GATE N: NO APLICA — razón: [explicación]
```
En lugar de omitirlo en silencio.

### Sin aprobación
La salida se marca como **BORRADOR**, nunca como final.

---

## Implementación Técnica

Los gates se implementan en:
- `scripts/gate_reporter.py` — genera el formato de reporte
- `scripts/gate_validator.py` — preflight que bloquea estructuralmente
- `decisions/gate_*.md` — archivos de decisión por gate

Cada gate produce:
1. `decisions/gate_[N]_[nombre].md` — decisión documentada
2. `artefacts/gate_[N]/` — tablas, figuras, scripts usados
3. `signoffs/gate_[N].sig` — firma de aprobación (timestamp + user)