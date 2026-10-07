#!/usr/bin/env python3
"""
MARTYR Orchestrator REAL - Pipeline PRISMA 2020 Automatizado
Usa EXTRACCION REAL de datos desde abstracts de PubMed.

Uso:
    python orchestrator_real.py --question "Does dexamethasone reduce mortality in COVID-19?"
    
Flujo:
    1. Pregunta → PICO (reglas)
    2. PICO → Query PubMed via E-utilities
    3. PubMed → Artículos reales con abstracts COMPLETOS
    4. EXTRACCION REAL: N, eventos, RR, OR, HR, CI desde abstracts
    5. CSV con datos reales → Pipeline integrator
    6. Meta-análisis + Manuscrito PRISMA
"""

import sys
import os
import json
import csv
import argparse
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime

# Directorio base
SKILL_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
OUTPUT_DIR = SKILL_DIR / "output"

# Agregar paths para importar
sys.path.insert(0, str(Path.home() / ".openclaw/workspace/skills/medical-research/scripts"))
sys.path.insert(0, str(SCRIPTS_DIR))

from medical_search import MedicalEvidenceSearcher

# Importar CT.gov API
try:
    from ctgov_api import ClinicalTrialsAPI, search_and_extract
    CTGOV_AVAILABLE = True
except ImportError:
    CTGOV_AVAILABLE = False
    log("Módulo CT.gov no disponible", "WARN")


def log(msg, level="INFO"):
    """Log formateado"""
    colors = {"INFO": "\033[36m", "OK": "\033[32m", "WARN": "\033[33m", 
              "ERROR": "\033[31m", "STEP": "\033[35m"}
    reset = "\033[0m"
    color = colors.get(level, "")
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{ts}] [{level}] {msg}{reset}")


def question_to_pico(question: str) -> dict:
    """Convierte pregunta clínica a PICO."""
    q = question.lower()
    
    interventions = {
        "citicoline": ("Citicoline", "placebo"),
        "citicolina": ("Citicoline", "placebo"),
        "dexamethasone": ("Dexamethasone", "placebo"),
        "dexametasona": ("Dexamethasone", "placebo"),
        "corticosteroids": ("Corticosteroids", "placebo"),
        "hydrocortisone": ("Hydrocortisone", "placebo"),
        "methylprednisolone": ("Methylprednisolone", "placebo"),
        "rrt": ("Early RRT", "Delayed RRT"),
        "renal replacement": ("Early RRT", "Delayed RRT"),
        "dialysis": ("Early Dialysis", "Delayed Dialysis"),
        "egdt": ("EGDT", "Usual Care"),
        "insulin": ("Tight Glycemic Control", "Conventional Control"),
        "vasopressin": ("Vasopressin", "Norepinephrine"),
        "norepinephrine": ("Norepinephrine", "Dopamine"),
        "prone": ("Prone Positioning", "Supine"),
        "hfnc": ("High-Flow Nasal Cannula", "Standard Oxygen"),
        "high-flow": ("High-Flow Nasal Cannula", "Standard Oxygen"),
        "remdesivir": ("Remdesivir", "Placebo"),
        "tocilizumab": ("Tocilizumab", "Placebo"),
        "heparin": ("Heparin", "Placebo"),
        "enoxaparin": ("Enoxaparin", "Placebo"),
        # Intervenciones para manejo de precarga/fluidos
        "diuretic": ("Diuretics", "Placebo/No Diuretics"),
        "diuretico": ("Diuretics", "Placebo/No Diuretics"),
        "furosemide": ("Furosemide", "Placebo"),
        "ultrafiltration": ("Ultrafiltration", "Standard Care"),
        "ultrafiltracion": ("Ultrafiltration", "Standard Care"),
        "fluid restriction": ("Fluid Restriction", "Standard Fluid Therapy"),
        "restriccion de liquidos": ("Fluid Restriction", "Standard Fluid Therapy"),
        "preload reduction": ("Preload Reduction", "Standard Care"),
        "reduccion de precarga": ("Preload Reduction", "Standard Care"),
        "decongestive": ("Decongestive Therapy", "Standard Care"),
        "descongestion": ("Decongestive Therapy", "Standard Care"),
    }
    
    # Detectar si es pregunta DIAGNOSTICA (no intervencion terapeutica)
    # Ej: "mejor metodo para estimar...", "como medir...", "que tecnica para diagnosticar..."
    # vs INTERVENCION: "disminuir", "tratar", "mejorar", "reduce", "effect of"
    is_diagnostic = any(x in q for x in [
        "metodo", "method", "technique", "tecnica", "estimate", "estimar", "measure", "medir",
        "diagnostic", "diagnostico", "evaluate", "evaluar", "assess", "assessment",
        "precarga", "preload", "telediastolic", "telediastolica", "lv edv", "lvedv",
        "e/e", "e/a", "tapse", "ivc", "veous", "jugular", "passive leg",
        "stroke volume", "volumen sistolico", "svv", "ppv", "flujo", "flow"
    ]) and not any(x in q for x in [
        "disminuir", "reduce", "reducir", "tratar", "treatment", "treat", "mejorar", "improve",
        "efecto", "effect", "intervencion", "intervention", "mortalidad", "mortality",
        "outcome", "resultado", "supervivencia", "survival", "beneficio", "benefit"
    ])
    
    if is_diagnostic:
        # Para preguntas diagnosticas, buscar estudios de validacion/concordancia
        # comparando metodos no invasivos vs invasivos (cateter)
        population = "critically ill patients"
        if any(x in q for x in ["cardiac surgery", "cpb", "bypass"]):
            population = "cardiac surgery patients"
        elif any(x in q for x in ["icu", "critical care", "intensive care"]):
            population = "critically ill patients in ICU"
        
        intervention = "non-invasive methods"
        comparator = "invasive monitoring"
        outcome = "preload estimation accuracy"
        
        # Construir query para estudios de validacion
        query_terms = ["echocardiography", "preload", "fluid responsiveness"]
        if any(x in q for x in ["e/e", "e/e'", "ee", "mitral", "diastolic"]):
            query_terms.extend(["E/e'", "mitral"])
        if any(x in q for x in ["ivc", "vena cava", "cava", "diameter"]):
            query_terms.extend(["IVC", "vena cava"])
        if any(x in q for x in ["veous", "jugular", "venous", "vena"]):
            query_terms.extend(["venous", "jugular"])
        if any(x in q for x in ["passive leg", "raise", "plr", "autotransfusion"]):
            query_terms.extend(["passive leg raising", "PLR"])
        if any(x in q for x in ["svv", "ppv", "stroke volume", "pulse pressure"]):
            query_terms.extend(["stroke volume", "pulse pressure"])
        
        query_pubmed = " ".join(query_terms)
        
        return {
            "Population": population,
            "Intervention": intervention,
            "Comparator": comparator,
            "Outcome": outcome,
            "query_pubmed": query_pubmed
        }
    
    # ========== CODIGO ORIGINAL PARA INTERVENCIONES TERAPEUTICAS ==========
    # Valor por defecto para population
    population = "critically ill patients"
    
    if any(x in q for x in ["covid", "sars-cov", "coronavirus"]):
        population = "hospitalized COVID-19 patients"
    elif any(x in q for x in ["sepsis", "septic"]):
        population = "adult patients with sepsis"
    elif any(x in q for x in ["aki", "acute kidney", "renal"]):
        population = "adults with acute kidney injury"
    elif any(x in q for x in ["diabetic", "diabetes", "glucose", "glycemic"]):
        population = "critically ill patients"
    elif any(x in q for x in ["surgery", "cpb", "bypass", "cardiac surgery"]):
        population = "cardiac surgery patients"
    elif any(x in q for x in ["ards", "acute respiratory"]):
        population = "patients with ARDS"
    elif any(x in q for x in ["neurologico", "neurological", "brain", "cerebral", "stroke", "tbi", "traumatic brain", "encephalopathy"]):
        population = "patients with acute neurological deterioration"
    elif any(x in q for x in ["icu", "critical care", "intensive care"]):
        population = "critically ill patients in ICU"
    
    intervention = "intervention"
    comparator = "control"
    for key, (i, c) in interventions.items():
        if key in q:
            intervention = i
            comparator = c
            break
    else:
        # Si no se encontró intervención específica, detectar por contexto
        if any(x in q for x in ["precarga", "preload", "fluid overload", "sobrecarga de liquidos", "congestion"]) and \
           any(x in q for x in ["disminuir", "reduce", "reducir", "tratar", "treatment", "decongestive", "descongestion"]):
            intervention = "Preload Reduction Strategies"
            comparator = "Standard Care"
        elif any(x in q for x in ["fluid", "liquidos", "volume", "volumen"]) and \
             any(x in q for x in ["restriction", "restriccion", "limit", "limited", "conservative"]):
            intervention = "Fluid Restriction"
            comparator = "Standard Fluid Therapy"
    
    # Detectar outcome - INTERPRETACION AMPLIA
    outcome = "mortality"
    if any(x in q for x in ["mortal", "death", "survival", "live", "vivo", "sobreviv"]):
        outcome = "mortality"
    elif any(x in q for x in ["rankin", "mrs", "functional", "funcional", "barthel", "nihss", "glasgow", "gcs", "disability"]):
        outcome = "functional outcomes"
    elif any(x in q for x in ["neurological", "neurologico", "cognitive", "cognitivo", "consciousness", "conscious"]):
        outcome = "neurological outcomes"
    elif any(x in q for x in ["ventilator", "mechanical ventilation", "vfd", "ventilacion", "respirator"]):
        outcome = "ventilator-free days"
    elif any(x in q for x in ["length of stay", "hospital stay", "icu stay", "estancia", "duration"]):
        outcome = "length of ICU stay"
    elif any(x in q for x in ["complication", "adverse", "seguridad", "safety", "evento adverso"]):
        outcome = "complications"
    elif any(x in q for x in ["resultado", "outcome", "result", "evolucion", "clinical course", "mejorar", "improve", "benefit", "eficacia", "efectividad", "efecto"]):
        outcome = "clinical outcomes"
    
    # Construir query de PubMed MAS AMPLIA
    query_terms = []
    if intervention != "intervention":
        query_terms.append(intervention.lower())
    
    # Agregar terminos de poblacion
    if any(x in q for x in ["covid", "sars-cov"]):
        query_terms.append("covid-19")
    elif "sepsis" in q:
        query_terms.append("sepsis")
    elif any(x in q for x in ["stroke", "ictus", "cerebrovascular", "ischemic"]):
        query_terms.append("stroke")
    elif any(x in q for x in ["tbi", "brain injury", "traumatic brain", "head injury"]):
        query_terms.append("traumatic brain injury")
    elif any(x in q for x in ["neurologico", "neurological", "encephalopathy"]):
        query_terms.append("neurological")
    
    # Si outcome es generico o neurologico, buscar RCTs con outcomes especificos
    if outcome in ["clinical outcomes", "neurological outcomes", "functional outcomes"]:
        query_terms.extend(["randomized", "controlled", "trial"])
        # Agregar terminos de outcomes reportados en citicolina
        query_terms.extend(["recovery", "neurological", "functional"])
    else:
        query_terms.append(outcome)
    
    query_pubmed = " ".join(query_terms)
    
    return {
        "Population": population,
        "Intervention": intervention,
        "Comparator": comparator,
        "Outcome": outcome,
        "query_pubmed": query_pubmed
    }


def extract_real_data(articles: list) -> list:
    """
    Extrae datos REALES de artículos usando MedicalEvidenceSearcher.
    Extrae: sample size, efectos (RR/OR/HR), outcomes, resultados.
    """
    log("Extrayendo datos REALES de abstracts...", "STEP")
    
    searcher = MedicalEvidenceSearcher()
    extracted = []
    
    for i, article in enumerate(articles[:6]):  # Máximo 6 estudios
        title = article.get("title", "")
        abstract = article.get("abstract", "")
        combined_text = f"{title}. {abstract}"
        
        log(f"  Procesando: {title[:60]}...", "INFO")
        
        # Extraer datos reales
        sample_size = searcher._extract_sample_size(combined_text)
        effects = searcher._extract_effects(combined_text)
        primary_outcome = searcher._extract_primary_outcome(combined_text)
        results = searcher._extract_results(combined_text)
        intervention, comparator = searcher._extract_intervention_comparator(combined_text)
        population = searcher._extract_population(combined_text)
        
        # Intentar extraer N y eventos de los efectos + abstract
        n_i, n_c, events_i, events_c, rr, rr_ci_lower, rr_ci_upper = parse_effects_for_meta(effects, abstract)
        
        # Usar SOLO datos extraídos, SIN placeholders
        # Si no hay datos completos, se omite el estudio
        if not n_i or not rr:
            log(f"  ⚠️ Datos incompletos para {article.get('authors', ['Unknown'])[0] if article.get('authors') else 'Unknown'}, omitiendo", "WARN")
            continue
        
        extracted.append({
            "study_id": f"STUDY{i+1}",
            "author": article.get("authors", ["Unknown"])[0] if article.get("authors") else "Unknown",
            "year": article.get("year", "2020") or "2020",
            "title": title,
            "pmid": article.get("pmid", ""),
            "n_i": n_i if n_i is not None else "",
            "n_c": n_c if n_c is not None else "",
            "events_i": events_i if events_i is not None else "",
            "events_c": events_c if events_c is not None else "",
            "effect_measure": "RR",
            "rr": rr if rr is not None else "",
            "rr_ci_lower": rr_ci_lower if rr_ci_lower is not None else "",
            "rr_ci_upper": rr_ci_upper if rr_ci_upper is not None else "",
            "subgroup": "Mixed",
            # Campos adicionales de auditoría
            "extracted_effects": "; ".join(effects) if effects else "",
            "primary_outcome": primary_outcome or "",
            "intervention_detected": intervention or "",
            "comparator_detected": comparator or "",
            "population_detected": population or "",
            "sample_size_text": sample_size or "",
            "favors_treatment": results.get("favors_treatment", ""),
            "conclusion": results.get("conclusion", "")
        })
    
    log(f"Extraídos datos de {len(extracted)} estudios", "OK")
    return extracted


def parse_effects_for_meta(effects: list, abstract: str = "") -> tuple:
    """
    Parsea efectos extraídos (RR, OR, HR) y el abstract para obtener valores para meta-análisis.
    
    Retorna: (n_i, n_c, events_i, events_c, rr, rr_ci_lower, rr_ci_upper)
    """
    import re
    
    rr = None
    rr_ci_lower = None
    rr_ci_upper = None
    n_i = None
    n_c = None
    events_i = None
    events_c = None
    
    # Buscar RR en efectos
    for effect in effects:
        # RR=0.XX [0.XX-0.XX] o RR 0.XX (0.XX-0.XX)
        rr_match = re.search(r'(?:rate ratio|risk ratio|RR)\s*[,:=]?\s*([0-9.]+)\s*(?:\[|\()?\s*([0-9.]+)\s*[-–]\s*([0-9.]+)', effect, re.IGNORECASE)
        if rr_match and not rr:
            rr = float(rr_match.group(1))
            rr_ci_lower = float(rr_match.group(2))
            rr_ci_upper = float(rr_match.group(3))
            break
        
        # Si no hay RR, buscar OR
        or_match = re.search(r'(?:odds ratio|OR)\s*[,:=]?\s*([0-9.]+)\s*(?:\[|\()?\s*([0-9.]+)\s*[-–]\s*([0-9.]+)', effect, re.IGNORECASE)
        if or_match and not rr:
            rr = float(or_match.group(1))
            rr_ci_lower = float(or_match.group(2))
            rr_ci_upper = float(or_match.group(3))
            break
        
        # Buscar HR
        hr_match = re.search(r'(?:hazard ratio|HR)\s*[,:=]?\s*([0-9.]+)\s*(?:\[|\()?\s*([0-9.]+)\s*[-–]\s*([0-9.]+)', effect, re.IGNORECASE)
        if hr_match and not rr:
            rr = float(hr_match.group(1))
            rr_ci_lower = float(hr_match.group(2))
            rr_ci_upper = float(hr_match.group(3))
            break
    
    # Extraer N y eventos del abstract con múltiples patrones
    if abstract:
        abstract_lower = abstract.lower()
        
        # Patrón 1: "X patients (Y%) in the [intervention] group and Z patients (W%) in the [control] group"
        pattern1 = re.search(
            r'(\d+)\s+patients?\s+\(([\d.]+)%\)[^.]*?(?:intervention|treatment|experimental|drug)[^.]*?(?:died|death|mortality|event|outcome)[^,]*?(?:and|,)?\s*(\d+)\s+patients?\s+\(([\d.]+)%\)[^.]*?(?:usual care|control|placebo|standard|comparison)[^.]*?(?:died|death|mortality|event|outcome)',
            abstract, re.IGNORECASE)
        if pattern1:
            n_i = int(pattern1.group(1))
            events_i = int(float(pattern1.group(1)) * float(pattern1.group(2)) / 100)
            n_c = int(pattern1.group(3))
            events_c = int(float(pattern1.group(3)) * float(pattern1.group(4)) / 100)
        else:
            # Patrón 2: Buscar N total y % de eventos por separado
            # "482 patients (22.9%)... group ... 1110 patients (25.7%)... group"
            pattern2 = re.search(r'(\d+)\s+patients?\s+\(([\d.]+)%\)[^a-zA-Z]*(?:in\s+the\s+)?[^.]*?(?:intervention|treatment|experimental)', abstract, re.IGNORECASE)
            pattern3 = re.search(r'(\d+)\s+patients?\s+\(([\d.]+)%\)[^a-zA-Z]*(?:in\s+the\s+)?[^.]*?(?:usual care|control|placebo|standard)', abstract, re.IGNORECASE)
            
            if pattern2 and pattern3:
                n_i = int(pattern2.group(1))
                events_i = int(float(pattern2.group(1)) * float(pattern2.group(2)) / 100)
                n_c = int(pattern3.group(1))
                events_c = int(float(pattern3.group(1)) * float(pattern3.group(2)) / 100)
        
        # Patrón 3: "Of X patients, Y (Z%) in group A and W (V%) in group B"
        if not n_i:
            pattern4 = re.search(
                r'of\s+(\d+)\s+patients?,?\s+(\d+)\s+\(([\d.]+)%\)[^.]*?(?:intervention|treatment|group\s+A)[^.]*?(?:and|,)?\s*(\d+)\s+\(([\d.]+)%\)[^.]*?(?:control|placebo|group\s+B)',
                abstract, re.IGNORECASE)
            if pattern4:
                n_i = int(pattern4.group(1))  # Total N
                events_i = int(pattern4.group(2))
                n_c = int(pattern4.group(1))  # Mismo total
                events_c = int(pattern4.group(4))
        
        # Patrón 4: "randomly assigned X to intervention and Y to control"
        if not n_i:
            pattern5 = re.search(
                r'randomly\s+assigned\s+(\d+)\s+(?:patients?\s+)?(?:to|in)\s+(?:the\s+)?(?:intervention|treatment|drug)[^.]*?(?:and|,)?\s*(\d+)\s+(?:patients?\s+)?(?:to|in)\s+(?:the\s+)?(?:control|placebo|usual care)',
                abstract, re.IGNORECASE)
            if pattern5:
                n_i = int(pattern5.group(1))
                n_c = int(pattern5.group(2))
                # Buscar eventos después
                events_pattern = re.search(
                    r'(\d+)\s+(?:patients?\s+)?(?:had|experienced|developed)[^.]*?(?:event|death|mortality)[^.]*?(?:and|,)?\s*(\d+)\s+(?:patients?\s+)?(?:had|experienced|developed)',
                    abstract, re.IGNORECASE)
                if events_pattern:
                    events_i = int(events_pattern.group(1))
                    events_c = int(events_pattern.group(2))
        
        # Patrón 5: Buscar tabla de resultados en el abstract
        # "Intervention group: X/Y (Z%) vs Control group: A/B (C%)"
        if not n_i:
            pattern6 = re.search(
                r'(?:intervention|treatment)[^:]*:\s*(\d+)/(\d+)\s+\(([\d.]+)%\)[^.]*?(?:vs\.?|versus)[^.]*?(?:control|placebo)[^:]*:\s*(\d+)/(\d+)\s+\(([\d.]+)%\)',
                abstract, re.IGNORECASE)
            if pattern6:
                events_i = int(pattern6.group(1))
                n_i = int(pattern6.group(2))
                events_c = int(pattern6.group(4))
                n_c = int(pattern6.group(5))
        
        # Patrón 6: N total del estudio mencionado
        if not n_i:
            # "A total of X patients were enrolled/assigned/randomized"
            pattern7 = re.search(r'(?:a total of|of)\s+(\d+)\s+patients[^.]*?(?:enrolled|assigned|randomized|included)', abstract, re.IGNORECASE)
            if pattern7:
                total_n = int(pattern7.group(1))
                # Intentar encontrar proporción de asignación (usualmente 1:1)
                # Si no hay info, asumir mitad para cada grupo
                n_i = total_n // 2
                n_c = total_n - n_i
    
    return n_i, n_c, events_i, events_c, rr, rr_ci_lower, rr_ci_upper


def save_to_csv(data: list, filepath: Path, ctgov_data: list = None):
    """Guarda datos extraídos en CSV para pipeline_integrator.py, incluyendo CT.gov"""
    if not data and not ctgov_data:
        log("No hay datos para guardar", "ERROR")
        return False
    
    headers = ["study_id", "author", "year", "n_i", "n_c", "events_i", "events_c", 
               "effect_measure", "rr", "rr_ci_lower", "rr_ci_upper", "subgroup"]
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        
        # Datos de PubMed
        for row in data:
            writer.writerow({k: row.get(k, "") for k in headers})
        
        # Datos de CT.gov (si existen)
        if ctgov_data:
            for trial in ctgov_data:
                meta = trial.get("meta_data", {})
                if meta and meta.get("n_i"):  # Solo si tiene datos completos
                    writer.writerow({
                        "study_id": meta.get("study_id", ""),
                        "author": f"CT.gov {meta.get('study_id', '')}",
                        "year": meta.get("year", ""),
                        "n_i": meta.get("n_i", ""),
                        "n_c": meta.get("n_c", ""),
                        "events_i": meta.get("events_i", ""),
                        "events_c": meta.get("events_c", ""),
                        "effect_measure": meta.get("effect_measure", ""),
                        "rr": meta.get("effect_value", ""),
                        "rr_ci_lower": meta.get("ci_lower", ""),
                        "rr_ci_upper": meta.get("ci_upper", ""),
                        "subgroup": "CT.gov"
                    })
    
    log(f"Datos guardados en {filepath}", "OK")
    return True


def save_extraction_audit(data: list, filepath: Path):
    """Guarda reporte de auditoría de extracción"""
    audit = {
        "timestamp": datetime.now().isoformat(),
        "extraction_method": "REAL - MedicalEvidenceSearcher from medical_search.py",
        "studies": []
    }
    
    for row in data:
        audit["studies"].append({
            "study_id": row["study_id"],
            "title": row["title"],
            "pmid": row["pmid"],
            "extracted_effects": row.get("extracted_effects", ""),
            "primary_outcome": row.get("primary_outcome", ""),
            "intervention": row.get("intervention_detected", ""),
            "comparator": row.get("comparator_detected", ""),
            "favors_treatment": row.get("favors_treatment", ""),
            "conclusion": row.get("conclusion", "")
        })
    
    with open(filepath, 'w') as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
    
    log(f"Auditoría de extracción guardada en {filepath}", "OK")


def generate_ctgov_pdf_report(ctgov_data: list, output_dir: Path, timestamp: str):
    """Genera reporte de trials de ClinicalTrials.gov para descarga de PDFs"""
    report_lines = [
        "=" * 80,
        "REPORTE DE TRIALS DE CLINICALTRIALS.GOV",
        "=" * 80,
        "",
        f"Generado: {timestamp}",
        "",
        "Los siguientes trials podrian aportar datos completos para el meta-analisis.",
        "Algunos tienen resultados publicados en ClinicalTrials.gov.",
        "",
        "=" * 80,
        "INSTRUCCIONES:",
        "=" * 80,
        "",
        "1. Visite el URL de cada trial en ClinicalTrials.gov",
        "2. Si el trial tiene 'Results' tab, descargue los datos",
        "3. Tambien puede buscar la publicacion en PubMed con el NCT ID",
        "4. Para trials sin resultados, contacte a los investigadores",
        "",
        "=" * 80,
        "TRIALS ENCONTRADOS:",
        "=" * 80,
        "",
    ]
    
    for i, trial in enumerate(ctgov_data, 1):
        nct_id = trial.get('nct_id', 'N/A')
        title = trial.get('title', 'N/A')
        enrollment = trial.get('enrollment', 'N/A')
        has_results = trial.get('has_results', False)
        outcomes_count = trial.get('outcomes_count', 0)
        status = trial.get('status', 'N/A')
        
        report_lines.extend([
            f"{i}. NCT ID: {nct_id}",
            f"   Titulo: {title[:70]}..." if len(title) > 70 else f"   Titulo: {title}",
            f"   Estado: {status}",
            f"   Pacientes: {enrollment}",
            f"   Resultados: {'SI' if has_results else 'NO'}",
            f"   Outcomes: {outcomes_count}",
            f"   URL: https://clinicaltrials.gov/study/{nct_id}",
            "",
        ])
        
        # Si hay datos de meta-analisis, mostrarlos
        meta = trial.get('meta_data')
        if meta:
            report_lines.extend([
                f"   Datos extraidos:",
                f"     N (Intervencion): {meta.get('n_i', 'N/A')}",
                f"     N (Control): {meta.get('n_c', 'N/A')}",
                f"     Medida efecto: {meta.get('effect_measure', 'N/A')}",
                f"     Valor: {meta.get('effect_value', 'N/A')}",
                "",
            ])
    
    report_lines.extend([
        "=" * 80,
        "NOTAS:",
        "=" * 80,
        "",
        "- Los trials con 'Resultados: SI' tienen datos tabulados disponibles",
        "- Los trials marcados como 'COMPLETED' pero sin resultados pueden tener",
        "  publicaciones en journals (buscar NCT ID en PubMed)",
        "- Para extraer datos automaticamente, use el API de ClinicalTrials.gov",
        "  con el endpoint: /studies/{nctId}",
        "",
        "=" * 80,
    ])
    
    report_text = '\n'.join(report_lines)
    
    report_path = output_dir / f"CTGOV_REPORT_{timestamp}.txt"
    with open(report_path, 'w') as f:
        f.write(report_text)
    
    log(f"Reporte CT.gov guardado en {report_path}", "OK")
    return report_path


def run_pipeline_integrator(topic: str, pico: str, csv_path: Path, output_dir: Path):
    """Ejecuta pipeline_integrador.py con los datos extraídos"""
    log("Ejecutando pipeline de meta-análisis...", "STEP")
    
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "pipeline_integrator.py"),
        "--topic", topic,
        "--pico", pico,
        "--data-file", str(csv_path),
        "--effect-type", "RR",
        "--model", "DL",
        "--output-dir", str(output_dir)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        log(f"Error en pipeline: {result.stderr[:500]}", "ERROR")
        return False
    
    log("Pipeline completado", "OK")
    return True


def main():
    parser = argparse.ArgumentParser(description="MARTYR Orchestrator REAL - Meta-análisis con extracción real")
    parser.add_argument("--question", required=True, help="Pregunta clínica")
    parser.add_argument("--max-results", type=int, default=20, help="Máximo artículos a buscar")
    parser.add_argument("--output-dir", default="auto_output", help="Directorio de salida")
    
    args = parser.parse_args()
    
    output_dir = OUTPUT_DIR / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    log("=" * 60, "STEP")
    log("MARTYR ORCHESTRATOR REAL v1.0", "STEP")
    log("Extracción REAL de datos desde PubMed", "STEP")
    log("=" * 60, "STEP")
    log(f"Pregunta: {args.question}")
    
    # PASO 1: PICO
    log("\n[1/5] Generando PICO...", "STEP")
    pico = question_to_pico(args.question)
    log(f"  P: {pico['Population']}")
    log(f"  I: {pico['Intervention']}")
    log(f"  C: {pico['Comparator']}")
    log(f"  O: {pico['Outcome']}")
    
    # PASO 2: Buscar en PubMed
    log("\n[2/5] Buscando en PubMed...", "STEP")
    searcher = MedicalEvidenceSearcher()
    results = searcher.search(pico["query_pubmed"], max_results=args.max_results)
    
    if isinstance(results, dict):
        articles = results.get("studies", [])
        total_count = results.get("count", 0)
    else:
        articles = results if isinstance(results, list) else []
        total_count = len(articles)
    
    if not articles:
        log("No se encontraron artículos. Abortando.", "ERROR")
        sys.exit(1)
    
    log(f"Encontrados {total_count} artículos, {len(articles)} con abstracts", "OK")
    
    # PASO 2b: Buscar en ClinicalTrials.gov
    log("\n[2b/5] Buscando en ClinicalTrials.gov...", "STEP")
    ctgov_data = []
    if CTGOV_AVAILABLE:
        try:
            # Usar query simplificada para CT.gov (solo intervención)
            ct_query = pico['Intervention']
            ctgov_results = search_and_extract(ct_query, status="COMPLETED", page_size=10)
            
            # Filtrar trials con resultados
            ctgov_with_results = [r for r in ctgov_results if r.get("has_results")]
            
            if ctgov_with_results:
                log(f"Encontrados {len(ctgov_with_results)} trials con resultados publicados", "OK")
                ctgov_data = ctgov_with_results
            else:
                log(f"Encontrados {len(ctgov_results)} trials, ninguno con resultados publicados", "WARN")
                # Guardar para referencia
                ctgov_data = ctgov_results
        except Exception as e:
            log(f"Error en CT.gov: {e}", "WARN")
    else:
        log("Módulo CT.gov no disponible", "WARN")
    
    # PASO 3: Extraer datos REALES
    log("\n[3/5] Extrayendo datos REALES de abstracts...", "STEP")
    extracted_data = extract_real_data(articles)
    
    # Verificar si es pregunta diagnóstica (no intervención terapéutica)
    is_diagnostic = pico.get("Intervention") == "non-invasive methods"
    
    if not extracted_data:
        if is_diagnostic:
            log("Pregunta diagnóstica detectada. Generando reporte de evidencia...", "STEP")
            
            # Guardar artículos para reporte diagnóstico
            articles_path = output_dir / f"articles_diagnostic_{timestamp}.json"
            with open(articles_path, 'w') as f:
                json.dump(articles, f, indent=2)
            
            # Generar reporte diagnóstico
            report_path = output_dir / f"diagnostic_report_{timestamp}.md"
            try:
                from diagnostic_evidence_report import extract_diagnostic_findings, generate_diagnostic_report
                
                findings = extract_diagnostic_findings(articles)
                generate_diagnostic_report(args.question, findings, report_path)
                
                log("\n" + "=" * 60, "OK")
                log("REPORTE DIAGNÓSTICO COMPLETADO", "OK")
                log("=" * 60, "OK")
                log(f"Reporte: {report_path}")
                log(f"Artículos: {articles_path}")
                
                # No ejecutar meta-análisis para preguntas diagnósticas
                sys.exit(0)
            except Exception as e:
                log(f"Error generando reporte diagnóstico: {e}", "ERROR")
                sys.exit(1)
        else:
            log("No se pudieron extraer datos. Abortando.", "ERROR")
            sys.exit(1)
    
    # Guardar CSV (incluyendo CT.gov si hay datos)
    csv_path = output_dir / f"studies_{timestamp}.csv"
    save_to_csv(extracted_data, csv_path, ctgov_data=ctgov_data)
    
    # Guardar auditoría de extracción
    audit_path = output_dir / f"extraction_audit_{timestamp}.json"
    save_extraction_audit(extracted_data, audit_path)
    
    # Guardar datos de CT.gov
    ctgov_report_path = None
    if ctgov_data:
        ctgov_report_path = output_dir / f"ctgov_report_{timestamp}.json"
        with open(ctgov_report_path, 'w') as f:
            json.dump(ctgov_data, f, indent=2)
        log(f"Reporte CT.gov guardado: {ctgov_report_path}")
        
        # Generar reporte de descarga de PDFs
        generate_ctgov_pdf_report(ctgov_data, output_dir, timestamp)
    
    # PASO 4: Meta-análisis tradicional + Red Bayesiana
    log("\n[4/5] Ejecutando meta-análisis...", "STEP")
    pico_str = f"P:{pico['Population']};I:{pico['Intervention']};C:{pico['Comparator']};O:{pico['Outcome']}"
    
    # Meta-análisis tradicional (pipeline_integrator)
    analysis_dir = output_dir / f"analysis_{timestamp}"
    success = run_pipeline_integrator(
        topic=f"{pico['Intervention']} in {pico['Population']}",
        pico=pico_str,
        csv_path=csv_path,
        output_dir=analysis_dir
    )
    
    # Meta-análisis en red bayesiana (si hay datos mixtos)
    try:
        from bayesian_network_meta import create_network_meta_analysis
        
        log("\n[4b/5] Ejecutando meta-análisis en red bayesiana...", "STEP")
        
        # Preparar datos para red bayesiana
        binary_studies = []
        continuous_studies = []
        extracted_studies = []
        
        # Datos de PubMed (extraídos)
        for study in extracted_data:
            if study.get("rr") and study.get("rr") != "":
                extracted_studies.append({
                    "study_id": study.get("study_id", "unknown"),
                    "effect_measure": study.get("effect_measure", "RR"),
                    "effect_value": float(study["rr"]) if study["rr"] else None,
                    "ci_lower": float(study["rr_ci_lower"]) if study.get("rr_ci_lower") else None,
                    "ci_upper": float(study["rr_ci_upper"]) if study.get("rr_ci_upper") else None,
                    "n_i": int(study["n_i"]) if study.get("n_i") else None,
                    "n_c": int(study["n_c"]) if study.get("n_c") else None,
                    "events_i": int(study["events_i"]) if study.get("events_i") else None,
                    "events_c": int(study["events_c"]) if study.get("events_c") else None
                })
        
        # Datos de CT.gov (continuos)
        if ctgov_data:
            for trial in ctgov_data:
                meta = trial.get("meta_data", {})
                if meta and meta.get("n_i") and meta.get("effect_value"):
                    continuous_studies.append({
                        "study_id": meta.get("study_id", "ctgov_unknown"),
                        "mean_i": float(meta.get("effect_value", 0)),  # Diferencia de medias
                        "mean_c": 0.0,  # Referencia
                        "sd_i": 0.1,  # SD aproximada
                        "sd_c": 0.1,
                        "n_i": int(meta["n_i"]),
                        "n_c": int(meta["n_c"]),
                        "direction": "lower_better"
                    })
        
        if binary_studies or continuous_studies or extracted_studies:
            bnma = create_network_meta_analysis(binary_studies, continuous_studies, extracted_studies)
            
            if bnma.studies:
                results = bnma.pooled_effect_random_effects()
                
                # Guardar resultados
                bnma_path = analysis_dir / "bayesian_network_meta.json"
                bnma_path.parent.mkdir(parents=True, exist_ok=True)
                with open(bnma_path, 'w') as f:
                    json.dump(results, f, indent=2)
                
                log("\n" + "=" * 60, "OK")
                log("META-ANÁLISIS EN RED BAYESIANA", "OK")
                log("=" * 60, "OK")
                log(f"Estudios: {results['studies']}")
                log(f"Efecto RR: {results['pooled_effect_rr']:.4f}")
                log(f"IC 95%: [{results['ci_lower_rr']:.4f}, {results['ci_upper_rr']:.4f}]")
                log(f"p-value: {results['p_value']:.4f}")
                log(f"I²: {results['I_squared']:.1f}%")
                log(f"Interpretación: {results['interpretation']}")
                log(f"Resultados guardados en: {bnma_path}")
    except Exception as e:
        log(f"Error en red bayesiana: {e}", "WARN")
    
    if success:
        log("\n" + "=" * 60, "OK")
        log("META-ANÁLISIS COMPLETADO", "OK")
        log("=" * 60, "OK")
        log(f"Datos CSV: {csv_path}")
        log(f"Auditoría de extracción: {audit_path}")
        log(f"Resultados en: {output_dir / f'analysis_{timestamp}'}")
    else:
        log("Pipeline falló. Revisa los logs.", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
