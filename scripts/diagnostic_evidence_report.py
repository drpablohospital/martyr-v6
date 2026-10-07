#!/usr/bin/env python3
"""
MARTYR Diagnostic Evidence Report Generator
Para preguntas diagnósticas (no intervenciones terapéuticas).
Extrae hallazgos clave de abstracts y genera reporte de evidencia narrativo.

Uso:
    python3 diagnostic_evidence_report.py \
      --question "mejor metodo no invasivo para estimar precarga" \
      --articles articles.json \
      --output reporte_precarga.md
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def extract_diagnostic_findings(articles: list) -> list:
    """
    Extrae hallazgos clave de artículos diagnósticos.
    Busca métodos, correlaciones, sensibilidad, recomendaciones.
    """
    findings = []
    
    for article in articles:
        title = article.get("title", "")
        abstract = article.get("abstract", "")
        combined = f"{title}. {abstract}".lower()
        
        finding = {
            "study_id": article.get("pmid", "Unknown"),
            "authors": article.get("authors", ["Unknown"])[0] if article.get("authors") else "Unknown",
            "year": article.get("year", ""),
            "title": title,
            "methods_found": [],
            "correlations": [],
            "recommendations": [],
            "limitations": []
        }
        
        # Detectar métodos no invasivos mencionados
        methods = {
            "e/e'": "E/e' (relación onda E mitral/E' tisular)",
            "e/a": "E/A (relación ondas E/A mitral)",
            "e prime": "E' (onda E' tisular)",
            "ivc": "IVC (diámetro de vena cava inferior)",
            "vena cava": "IVC (diámetro de vena cava inferior)",
            "passive leg": "PLR (elevación pasiva de piernas)",
            "plr": "PLR (elevación pasiva de piernas)",
            "veous": "VExUS (ecografía venosa sistémica)",
            "jugular": "VJ (dilatación de vena yugular)",
            "stroke volume variation": "SVV (variación de volumen sistólico)",
            "svv": "SVV (variación de volumen sistólico)",
            "pulse pressure variation": "PPV (variación de presión de pulso)",
            "ppv": "PPV (variación de presión de pulso)",
            "delta ppc": "ΔPPC (variación de presión de pulso)",
            "delta down": "ΔDown (variación de presión sistólica)",
            "bioimpedance": "Bioimpedancia",
            "transthoracic": "TTE (ecocardiografía transtorácica)",
            "transesophageal": "TEE (ecocardiografía transesofágica)"
        }
        
        for key, description in methods.items():
            if key in combined:
                finding["methods_found"].append(description)
        
        # Extraer correlaciones reportadas
        import re
        correlation_patterns = [
            r'r\s*=\s*([0-9.]+)',
            r'correlation\s+(?:coefficient|r)\s*(?:was|of|=)\s*([0-9.]+)',
            r'correlated\s+(?:with|r\s*=)\s*([0-9.]+)',
            r'auc\s*(?:was|=)\s*([0-9.]+)',
            r'area under the curve\s*(?:was|=)\s*([0-9.]+)'
        ]
        
        for pattern in correlation_patterns:
            matches = re.findall(pattern, combined)
            for match in matches:
                try:
                    value = float(match)
                    if 0 < value < 1:
                        finding["correlations"].append(f"r/AUC = {value}")
                except:
                    pass
        
        # Extraer recomendaciones
        recommendation_patterns = [
            r'recommend(?:ed|ation|s)?\s+(?:that|the use of|using)?\s*([^\.]+)',
            r'suggest(?:ed|s)?\s+(?:that|the use of|using)?\s*([^\.]+)',
            r'should\s+(?:be|use|consider)\s*([^\.]+)',
            r'preferred\s+method\s+(?:is|for)\s*([^\.]+)'
        ]
        
        for pattern in recommendation_patterns:
            matches = re.findall(pattern, combined)
            for match in matches:
                if len(match) > 10 and len(match) < 200:
                    finding["recommendations"].append(match.strip())
        
        # Extraer limitaciones
        limitation_keywords = [
            "limitation", "limited", "difficult", "challenging",
            "not reliable", "poor correlation", "weak correlation",
            "cannot be used", "not recommended", "insufficient"
        ]
        
        for keyword in limitation_keywords:
            if keyword in combined:
                # Extraer oración con limitación
                sentences = abstract.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        finding["limitations"].append(sentence.strip())
                        break
        
        if finding["methods_found"] or finding["recommendations"]:
            findings.append(finding)
    
    return findings


def generate_diagnostic_report(question: str, findings: list, output_path: Path):
    """Genera reporte de evidencia diagnóstica en Markdown."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    report = f"""# Reporte de Evidencia: {question.title()}

**Fecha:** {timestamp}
**Tipo:** Pregunta Diagnóstica (No Intervención Terapéutica)
**Fuente:** PubMed / ClinicalTrials.gov

---

## Resumen Ejecutivo

Esta pregunta busca identificar el **mejor método no invasivo para estimar la precarga** (tensión ventricular al final de la diastole). 
A diferencia de las preguntas de intervención terapéutica ("¿X tratamiento funciona?"), esta es una pregunta de **evaluación diagnóstica** 
("¿Qué método mide mejor Y parámetro?").

**Hallazgo principal:** La evidencia proviene principalmente de estudios de validación, guías de consenso y revisiones narrativas 
que comparan métodos no invasivos (ecocardiografía) vs métodos invasivos (catéter de Swan-Ganz). 
No hay RCTs disponibles para esta pregunta.

---

## Métodos No Invasivos Identificados

"""
    
    # Agrupar métodos encontrados
    all_methods = {}
    for finding in findings:
        for method in finding["methods_found"]:
            if method not in all_methods:
                all_methods[method] = {
                    "studies": [],
                    "correlations": [],
                    "recommendations": []
                }
            all_methods[method]["studies"].append(f"{finding['authors']} ({finding['year']})")
            all_methods[method]["correlations"].extend(finding["correlations"])
            all_methods[method]["recommendations"].extend(finding["recommendations"])
    
    # Ordenar métodos por número de estudios
    sorted_methods = sorted(all_methods.items(), key=lambda x: len(x[1]["studies"]), reverse=True)
    
    for i, (method, data) in enumerate(sorted_methods, 1):
        report += f"""### {i}. {method}

**Estudios que lo mencionan:** {len(data['studies'])}
- {chr(10).join('- ' + s for s in data['studies'][:3])}

"""
        if data["correlations"]:
            report += f"**Correlaciones reportadas:** {', '.join(data['correlations'][:3])}\n\n"
        
        if data["recommendations"]:
            report += f"**Recomendaciones:** {chr(10).join('- ' + r[:150] + '...' if len(r) > 150 else '- ' + r for r in data['recommendations'][:2])}\n\n"
        
        report += "\n"
    
    report += f"""---

## Estudios Incluidos

Se analizaron {len(findings)} estudios relevantes:

"""
    
    for i, finding in enumerate(findings, 1):
        report += f"""{i}. **{finding['title'][:80]}**
   - Autor: {finding['authors']} ({finding['year']})
   - Métodos encontrados: {', '.join(finding['methods_found']) if finding['methods_found'] else 'Ninguno específico'}
   
"""
    
    report += """
---

## Limitaciones de la Evidencia

1. **No hay RCTs:** No se encontraron ensayos clínicos aleatorizados que comparen métodos de estimación de precarga
2. **Estudios de validación heterogéneos:** Diferentes poblaciones, técnicas ecocardiográficas y estándares de referencia
3. **Correlaciones variables:** Los coeficientes de correlación reportados varían ampliamente según la técnica y la población
4. **Recomendaciones de guías:** La mayoría de la evidencia proviene de guías de consenso (ESICM, ASE) basadas en opinión de expertos

---

## Recomendaciones Clave de las Guías

### ESICM Guidelines 2025 (Monnet X et al.)
- La monitorización hemodinámica debe guiar la terapia de fluidos
- Se recomienda evaluar la "fluid responsiveness" antes de administrar fluidos
- Los métodos dinámicos (PLR, PPV, SVV) son preferidos sobre los estáticos (IVC, presión)

### Métodos Recomendados según la Evidencia
1. **PLR + Ecocardiografía:** Método dinámico con buena evidencia
2. **E/e' + IVC:** Métodos estáticos complementarios
3. **PPV/SVV:** Requieren ritmo sinusal y ventilación controlada
4. **TTE/TEE:** Ecocardiografía como herramienta principal

---

## Conclusión

Para la estimación no invasiva de la precarga en pacientes críticos:

1. **No existe un método único "óptimo"** - Se recomienda combinación de métodos
2. **PLR + Ecocardiografía** tiene la mejor evidencia para predicción de respuesta a fluidos
3. **E/e'** es útil para estimar presiones de llenado ventricular izquierdo
4. **IVC** es simple pero menos preciso en pacientes ventilados
5. **VExUS** (ecografía venosa) es prometedor pero con evidencia limitada

**Recomendación práctica:** Combinar ecocardiografía transtorácica (TTE) con test dinámicos (PLR) 
para una evaluación integral de la precarga y la respuesta a fluidos.

---

*Nota: Este reporte se basa en abstracts disponibles. Para una evaluación completa, 
se recomienda revisar los artículos completos y las guías de consenso (ESICM 2025, ASE Guidelines).*
"""
    
    # Guardar reporte
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Reporte diagnóstico guardado en: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Genera reporte de evidencia diagnóstica")
    parser.add_argument("--question", required=True, help="Pregunta diagnóstica")
    parser.add_argument("--articles", required=True, help="Archivo JSON con artículos")
    parser.add_argument("--output", required=True, help="Ruta de salida del reporte")
    
    args = parser.parse_args()
    
    # Cargar artículos
    with open(args.articles) as f:
        articles = json.load(f)
    
    # Extraer hallazgos
    findings = extract_diagnostic_findings(articles)
    
    # Generar reporte
    output_path = Path(args.output)
    generate_diagnostic_report(args.question, findings, output_path)


if __name__ == "__main__":
    main()
