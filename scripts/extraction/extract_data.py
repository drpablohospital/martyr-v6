#!/usr/bin/env python3
"""
Martyria v3.2 - Data Extractor
Extrae datos cuantitativos REALES de abstracts para sintesis
Mejoras sobre v3.1:
- Parseo de N (tamaño muestral) desde abstract
- Extraccion de resultados con medidas de efecto
- Deteccion de outcomes primarios
- Conclusiones especificas (no genericas)
"""

import re
import json
from typing import Dict, List, Optional, Tuple


class DataExtractorV32:
    """Extrae datos clinicos reales de abstracts de PubMed"""
    
    # Patrones regex mejorados para extraccion
    PATTERNS = {
        "n_total": r'\b(\d{1,3}(?:,\d{3})+|\d+)\s+(?:patients?|subjects?|participants?|individuals?|cases?|patients\s+with)',
        "n_groups": r'\b(\d+)\s+(?:vs\.?\s+|versus\s+|compared\s+to\s+|and\s+)(\d+)',
        "n_enrolled": r'(?:enrolled|included|recruited|randomized|assigned)\s+(\d{1,3}(?:,\d{3})+|\d+)',
        "n_per_group": r'(?:group\s+[A-Z]|intervention|control|placebo|standard)\s*:?\s*(?:n\s*=\s*)?(\d+)',
        "mortality": r'(?:mortality|death|mortality rate|survival)\s*:?\s*(\d+\.?\d*)\s*%',
        "mortality_abs": r'(?:mortality|death)[^\d]*(\d+)[^\d]*(?:of|out of|from)[^\d]*(\d+)',
        "mean_age": r'(?:mean|average)\s+age\s*:?\s*(\d+\.?\d*)',
        "age_range": r'(?:age[d]?\s+)?(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*(?:years?|yr)',
        "icu_stay": r'(?:ICU|intensive care)\s+(?:stay|length|LOS|duration)\s*:?\s*(\d+\.?\d*)\s*(?:days?|d)',
        "hospital_stay": r'(?:hospital|length of stay|LOS)\s*:?\s*(\d+\.?\d*)\s*(?:days?|d)',
        "apache": r'APACHE\s*(?:II|2|III|3)?\s*:?\s*(\d+\.?\d*)',
        "sofa": r'SOFA\s*:?\s*(\d+\.?\d*)',
        "saps": r'SAPS\s*(?:II|2|III|3)?\s*:?\s*(\d+\.?\d*)',
        "rr_ci": r'(?:RR|relative risk|risk ratio)\s*:?\s*(\d+\.?\d*)\s*(?:\(\s*(?:95%\s*)?CI\s*:?\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*\))?',
        "or_ci": r'(?:OR|odds ratio)\s*:?\s*(\d+\.?\d*)\s*(?:\(\s*(?:95%\s*)?CI\s*:?\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*\))?',
        "hr_ci": r'(?:HR|hazard ratio)\s*:?\s*(\d+\.?\d*)\s*(?:\(\s*(?:95%\s*)?CI\s*:?\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*\))?',
        "md_ci": r'(?:MD|mean difference|WMD)\s*:?\s*([\-\d]+\.?\d*)\s*(?:\(\s*(?:95%\s*)?CI\s*:?\s*([\-\d]+\.?\d*)\s*[-–]\s*([\-\d]+\.?\d*)\s*\))?',
        "p_value": r'p\s*[<>=≤≥]?\s*(\d+\.?\d*(?:[eE][\-+]?\d+)?)',
        "confidence_interval": r'(?:95%\s*)?CI\s*:?\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)',
        "sample_size_study": r'(?:randomized|enrolled|included|assigned)\s+(\d{1,3}(?:,\d{3})+|\d+)',
        "follow_up": r'(?:follow[- ]?up|followed)\s*:?\s*(\d+\.?\d*)\s*(?:months?|years?|days?|mo|yr|d)',
        "kdigo_stage": r'KDIGO\s+(?:stage\s+)?(\d)',
        "creatinine": r'creatinine\s*:?\s*(\d+\.?\d*)',
        "urea": r'(?:urea|BUN)\s*:?\s*(\d+\.?\d*)',
    }
    
    def __init__(self):
        self.compiled_patterns = {k: re.compile(v, re.IGNORECASE) for k, v in self.PATTERNS.items()}
    
    def extract(self, article: Dict) -> Dict:
        """
        Extrae todos los datos posibles de un articulo
        """
        abstract = article.get("abstract", "") or ""
        title = article.get("title", "") or ""
        text = title + " " + abstract
        
        extracted = {
            "pmid": article.get("pmid", ""),
            "title": title,
            "journal": article.get("journal", ""),
            "year": article.get("year", ""),
            "doi": article.get("doi", ""),
            "study_type": article.get("study_type", "Other"),
            "authors": article.get("authors", []),
            "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
            "mesh_terms": article.get("mesh_terms", []),
            "relevance_score": article.get("relevance_score", 0.0),
            "data": {},
            "parsed": {}
        }
        
        # Extraer datos numericos
        for key, pattern in self.compiled_patterns.items():
            matches = pattern.findall(text)
            if matches:
                extracted["data"][key] = matches
        
        # Parsear N (tamaño muestral)
        extracted["parsed"]["n_total"] = self._parse_n_total(extracted["data"], text)
        
        # Parsear outcomes
        extracted["outcomes"] = self._extract_outcomes(text)
        
        # Parsear intervenciones
        extracted["interventions"] = self._extract_interventions(text)
        
        # Determinar nivel de evidencia correcto
        extracted["evidence_level"] = self._determine_evidence_level(
            extracted["study_type"], 
            title,
            extracted.get("data", {})
        )
        
        # Extraer conclusiones especificas
        extracted["conclusions"] = self._extract_conclusions(abstract)
        
        # Extraer resultados principales
        extracted["main_results"] = self._extract_main_results(text, extracted["data"])
        
        # Extraer limitaciones
        extracted["limitations"] = self._extract_limitations(abstract)
        
        # Extraer definicion AKI si existe
        extracted["aki_definition"] = self._extract_aki_definition(text)
        
        return extracted
    
    def _parse_n_total(self, data: Dict, text: str) -> Optional[int]:
        """Parsea tamaño muestral desde los datos extraidos"""
        
        # Buscar en n_enrolled primero (mas confiable)
        if "n_enrolled" in data:
            try:
                match = data["n_enrolled"][0]
                if isinstance(match, tuple):
                    n = match[0]
                else:
                    n = match
                return int(n.replace(",", ""))
            except (ValueError, IndexError):
                pass
        
        # Buscar en n_total
        if "n_total" in data:
            try:
                match = data["n_total"][0]
                if isinstance(match, tuple):
                    n = match[0]
                else:
                    n = match
                return int(n.replace(",", ""))
            except (ValueError, IndexError):
                pass
        
        # Buscar patrones especificos
        patterns = [
            r'\b(\d{1,3}(?:,\d{3})+)\s+(?:patients|subjects|participants)\b',
            r'(?:total of|of)\s+(\d{1,3}(?:,\d{3})+)\s+(?:patients|patients?|subjects)',
            r'N\s*=\s*(\d{1,3}(?:,\d{3})+)',
            r'n\s*=\s*(\d{1,3}(?:,\d{3})+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except ValueError:
                    pass
        
        return None
    
    def _extract_outcomes(self, text: str) -> List[str]:
        """Extrae outcomes primarios y secundarios mencionados"""
        outcomes = []
        
        outcome_keywords = {
            "mortality": ["mortality", "death", "survival", "28-day mortality", "hospital mortality"],
            "aki_progression": ["aki progression", "kdigo stage", "aki stage", "worsening aki"],
            "rrt": ["renal replacement therapy", "rrt", "dialysis", "hemodialysis", "crrt"],
            "icu_los": ["icu stay", "icu length", "length of icu stay", "icu los"],
            "hospital_los": ["hospital stay", "hospital length", "length of stay"],
            "mv_duration": ["mechanical ventilation", "ventilator-free days", "ventilation duration"],
            "organ_dysfunction": ["organ dysfunction", "sofa score", "apache score", "organ failure"],
            "sepsis": ["sepsis", "septic shock", "bacteremia"],
            "adverse_events": ["adverse events", "complications", "safety"],
            "recovery": ["renal recovery", "kidney recovery", "recovery of renal function"],
            "creatinine": ["creatinine", "serum creatinine", "sCr"],
            "urea": ["urea", "BUN", "blood urea nitrogen"],
            "urine_output": ["urine output", "oliguria", "diuresis"],
            "inflammatory": ["il-6", "c-reactive protein", "crp", "procalcitonin"],
            "hemodynamic": ["blood pressure", "map", "vasopressor", "norepinephrine"],
            "fluid_balance": ["fluid balance", "fluid overload", "cumulative fluid"],
        }
        
        text_lower = text.lower()
        
        for category, keywords in outcome_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if category not in outcomes:
                        outcomes.append(category)
                    break
        
        return outcomes[:10]
    
    def _extract_interventions(self, text: str) -> List[str]:
        """Extrae intervenciones mencionadas"""
        interventions = []
        
        intervention_keywords = {
            "renal_replacement": ["renal replacement therapy", "rrt", "dialysis", "crrt", "hemodialysis", "hemofiltration"],
            "vasopressors": ["norepinephrine", "epinephrine", "vasopressin", "dobutamine", "vasopressor"],
            "fluids": ["crystalloid", "colloid", "albumin", "saline", "ringer", "fluid resuscitation"],
            "sedation": ["dexmedetomidine", "propofol", "midazolam", "sedation"],
            "ventilation": ["mechanical ventilation", "prone positioning", "ecmo", "hfnc"],
            "antibiotics": ["antibiotics", "meropenem", "piperacillin", "vancomycin"],
            "corticosteroids": ["corticosteroids", "hydrocortisone", "methylprednisolone"],
            "nutrition": ["enteral nutrition", "parenteral nutrition", "immunonutrition"],
            "diuretics": ["furosemide", "diuretics", "loop diuretics"],
            "bicarbonate": ["bicarbonate", "sodium bicarbonate"],
            "goal_directed": ["goal-directed therapy", "early goal-directed", "egdt"],
        }
        
        text_lower = text.lower()
        
        for category, keywords in intervention_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if category not in interventions:
                        interventions.append(category)
                    break
        
        return interventions[:10]
    
    def _determine_evidence_level(self, study_type: str, title: str, data: Dict) -> str:
        """Determina nivel de evidencia segun Oxford/GRADE corregido"""
        
        study_type = study_type or "Other"
        title_lower = (title or "").lower()
        
        # Detectar si es meta-analisis de ECA o de cohortes
        is_meta_analysis = study_type in ["Meta-analysis", "Systematic Review"]
        
        if is_meta_analysis:
            # Verificar si el titulo menciona RCT o cohort
            if any(word in title_lower for word in ["randomized", "rct", "trial", "controlled trial"]):
                return "1a"  # Meta-analisis de ECA
            elif any(word in title_lower for word in ["cohort", "observational", "retrospective", "prospective cohort"]):
                return "2a"  # Meta-analisis de cohortes
            else:
                return "1a"  # Por defecto, asumir ECA
        
        levels = {
            "RCT": "1b",
            "Cohort Study": "2a",
            "Case-Control": "3",
            "Cross-Sectional": "3",
            "Clinical Guideline": "1a",
            "Other": "4"
        }
        
        # Detectar si es cohorte prospectivo vs retrospectivo
        if study_type == "Cohort Study":
            if any(word in title_lower for word in ["prospective", "prospectively"]):
                return "2a"
            elif any(word in title_lower for word in ["retrospective", "retrospectively", "medical records", "chart review"]):
                return "2b"
            else:
                return "2b"  # Default: asumir retrospectivo si no se especifica
        
        return levels.get(study_type, "4")
    
    def _extract_conclusions(self, abstract: str) -> str:
        """Extrae conclusiones especificas del abstract"""
        if not abstract:
            return ""
        
        # Buscar seccion de conclusion
        conclusion_markers = [
            "conclusion:", "conclusions:", "in conclusion",
            "these findings", "we conclude", "our results suggest",
            "this study suggests", "taken together", "in summary",
            "we found that", "our findings indicate"
        ]
        
        abstract_lower = abstract.lower()
        
        for marker in conclusion_markers:
            idx = abstract_lower.find(marker)
            if idx != -1:
                conclusion = abstract[idx:idx+500]
                # Limpiar
                conclusion = conclusion.replace("Conclusion:", "").replace("Conclusions:", "")
                conclusion = conclusion.strip()
                if len(conclusion) > 50:
                    return conclusion
        
        # Si no hay marcador, devolver los ultimos 300 caracteres
        return abstract[-300:] if len(abstract) > 300 else abstract
    
    def _extract_main_results(self, text: str, data: Dict) -> List[Dict]:
        """Extrae resultados principales con medidas de efecto"""
        results = []
        
        # Buscar RR/OR/HR/MD con valores
        for measure_type, pattern_key in [("RR", "rr_ci"), ("OR", "or_ci"), 
                                           ("HR", "hr_ci"), ("MD", "md_ci")]:
            if pattern_key in data:
                for match in data[pattern_key]:
                    try:
                        if isinstance(match, tuple) and len(match) >= 1:
                            value = match[0]
                            ci_lower = match[1] if len(match) > 1 else None
                            ci_upper = match[2] if len(match) > 2 else None
                            
                            result = {
                                "measure": measure_type,
                                "value": value,
                                "ci_lower": ci_lower,
                                "ci_upper": ci_upper,
                                "context": self._extract_context(text, str(value))
                            }
                            results.append(result)
                    except (ValueError, IndexError):
                        continue
        
        return results
    
    def _extract_context(self, text: str, value: str, window: int = 100) -> str:
        """Extrae contexto alrededor de un valor numerico"""
        idx = text.find(value)
        if idx != -1:
            start = max(0, idx - window)
            end = min(len(text), idx + window)
            return text[start:end].strip()
        return ""
    
    def _extract_limitations(self, abstract: str) -> List[str]:
        """Extrae limitaciones mencionadas"""
        limitations = []
        
        if not abstract:
            return limitations
        
        limitation_keywords = {
            "single_center": ["single-center", "single center", "tertiary center"],
            "retrospective": ["retrospective", "chart review", "medical records"],
            "observational": ["observational", "non-randomized", "nonrandomized"],
            "small_sample": ["small sample", "underpowered", "limited sample"],
            "selection_bias": ["selection bias", "referral bias"],
            "confounding": ["confounding", "residual confounding"],
            "missing_data": ["missing data", "lost to follow-up", "incomplete data"],
            "generalizability": ["generalizability", "external validity", "single institution"],
            "surrogate": ["surrogate endpoint", "surrogate outcome"],
        }
        
        text_lower = abstract.lower()
        
        for category, keywords in limitation_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if category not in limitations:
                        limitations.append(category)
                    break
        
        return limitations[:5]
    
    def _extract_aki_definition(self, text: str) -> str:
        """Extrae definicion de AKI usada"""
        aki_patterns = [
            r'KDIGO\s+(?:criteria|definition|guidelines?)',
            r'RIFLE\s+(?:criteria|classification)',
            r'AKIN\s+(?:criteria|definition)',
            r'(?:serum creatinine|sCr)\s+(?:increase|rise|elevation)',
            r'urine output\s+(?:\u003c|less than)',
        ]
        
        for pattern in aki_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                return text[start:end].strip()
        
        return ""
    
    def estimate_nnt(self, extracted_data: Dict) -> Optional[float]:
        """Estima NNT/NNH si hay datos de riesgo relativo"""
        rr_data = extracted_data.get("data", {}).get("rr_ci", [])
        if not rr_data:
            return None
        
        try:
            rr = float(rr_data[0][0]) if isinstance(rr_data[0], tuple) else float(rr_data[0])
            
            if rr < 1:
                return round(1 / (1 - rr), 1) if (1 - rr) > 0 else None
            else:
                return round(1 / (rr - 1), 1) if (rr - 1) > 0 else None
        except (ValueError, IndexError, ZeroDivisionError):
            return None


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python3 extract_data_v32.py <archivo_resultados_pubmed.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    extractor = DataExtractorV32()
    extracted = []
    
    for article in articles:
        data = extractor.extract(article)
        data["nnt"] = extractor.estimate_nnt(data)
        extracted.append(data)
    
    output_file = input_file.replace(".json", "_extracted_v32.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)
    
    print(f"Extraidos datos de {len(extracted)} articulos")
    print(f"Guardado en: {output_file}")
    
    # Mostrar resumen
    print("\n=== RESUMEN DE EXTRACCION v3.2 ===")
    for i, art in enumerate(extracted[:5], 1):
        print(f"\n{i}. {art['title'][:80]}...")
        print(f"   Tipo: {art['study_type']} | Nivel: {art['evidence_level']}")
        print(f"   N: {art['parsed'].get('n_total', 'N/A')}")
        print(f"   Outcomes: {', '.join(art['outcomes'][:5])}")
        print(f"   Intervenciones: {', '.join(art['interventions'][:5])}")
        print(f"   Resultados: {len(art.get('main_results', []))} medidas")
        if art.get('nnt'):
            print(f"   NNT estimado: {art['nnt']}")


if __name__ == "__main__":
    main()
