#!/usr/bin/env python3
"""
claim_extractor.py - Extractor de Afirmaciones Clínicas

Extrae afirmaciones estructuradas desde datos de estudios para evaluación GRADE.
Cada afirmación es rastreable a los estudios que la soportan.

Input: CSV con datos de estudios (formatos soportados: aki_rrt_studies.csv, etc.)
Output: JSON con afirmaciones + archivos de auditoría

Uso:
    python3 claim_extractor.py --input data.csv --output output/
"""

import argparse
import csv
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

# Importar utilidades compartidas
sys.path.insert(0, str(Path(__file__).parent / 'utils'))
from data_loaders import load_studies, validate_studies_data
from json_utils import save_json_safe, to_python_types

# Configurar logger
logger = logging.getLogger('claim_extractor')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)


def determine_direction(effect_size, ci_lower, ci_upper):
    """Determina dirección del efecto."""
    if effect_size is None:
        return "uncertain"
    if ci_lower and ci_lower > 1.0:
        return "favors_control" if effect_size > 1 else "favors_intervention"
    elif ci_upper and ci_upper < 1.0:
        return "favors_intervention" if effect_size < 1 else "favors_control"
    else:
        return "no_difference" if 0.9 < effect_size < 1.1 else "uncertain"


def determine_magnitude(effect_size):
    """Determina magnitud del efecto."""
    if effect_size is None:
        return "uncertain"
    rr = abs(effect_size)
    if rr < 0.70 or rr > 1.43:
        return "large"
    elif rr < 0.85 or rr > 1.18:
        return "moderate"
    elif rr < 0.95 or rr > 1.05:
        return "small"
    else:
        return "uncertain"


def calculate_consistency(studies):
    """
    Calcula consistencia entre estudios considerando dirección Y magnitud.
    
    Un consistency_score de 1.0 significa que todos los estudios concuerdan
    en dirección Y magnitud similar. Un score bajo indica heterogeneidad.
    """
    if not studies:
        return 0.0
    
    # Obtener efectos válidos
    effects = []
    for s in studies:
        effect = s.get('effect_size') or s.get('rr') or s.get('or') or s.get('hr')
        if effect is not None:
            effects.append(effect)
    
    if len(effects) < 2:
        return 1.0  # Un solo estudio es "consistente" consigo mismo
    
    # Calcular direcciones
    directions = []
    for s in studies:
        effect = s.get('effect_size') or s.get('rr') or s.get('or') or s.get('hr')
        ci_lower = s.get('ci_lower') or s.get('rr_ci_lower') or s.get('or_ci_lower')
        ci_upper = s.get('ci_upper') or s.get('rr_ci_upper') or s.get('or_ci_upper')
        if effect is not None:
            direction = determine_direction(effect, ci_lower, ci_upper)
            if direction not in ['uncertain', 'no_difference']:
                directions.append(direction)
    
    # Consistencia de dirección (0-1)
    from collections import Counter
    if directions:
        counts = Counter(directions)
        max_count = max(counts.values())
        direction_consistency = max_count / len(directions)
    else:
        direction_consistency = 0.0
    
    # Consistencia de magnitud (0-1)
    # Calcular coeficiente de variación de los efectos (en escala log)
    import math
    log_effects = [math.log(e) for e in effects if e > 0]
    if len(log_effects) >= 2:
        mean_log = sum(log_effects) / len(log_effects)
        variance_log = sum((x - mean_log)**2 for x in log_effects) / len(log_effects)
        std_log = math.sqrt(variance_log)
        cv = std_log / abs(mean_log) if mean_log != 0 else 0
        # Convertir CV a score de consistencia (menor CV = mayor consistencia)
        magnitude_consistency = max(0, 1 - cv)
    else:
        magnitude_consistency = 1.0
    
    # Score combinado: promedio ponderado
    # Dirección pesa más (70%) que magnitud (30%)
    combined = (0.7 * direction_consistency) + (0.3 * magnitude_consistency)
    
    return combined


def extract_main_claim(studies):
    """Extrae afirmación principal de eficacia."""
    if not studies:
        return None
    
    # Identificar intervención y control (con defaults inteligentes)
    intervention = studies[0].get('intervention')
    control = studies[0].get('control')
    
    # Si no hay intervention/control, usar defaults basados en datos disponibles
    if not intervention:
        # Intentar inferir del subgrupo o usar genérico
        subgroup = studies[0].get('subgroup')
        if subgroup:
            intervention = f"Intervención ({subgroup})"
        else:
            intervention = "Intervención"
    
    if not control:
        # Ver si hay múltiples subgrupos → usar como comparación
        subgroups = set(s.get('subgroup', '') for s in studies if s.get('subgroup'))
        if len(subgroups) > 1:
            control = "Comparador"
        else:
            control = "Control"
    
    outcome = studies[0].get('outcome', 'outcome principal')
    
    # Calcular efecto combinado
    effects = []
    weights = []
    
    for s in studies:
        effect = s.get('effect_size') or s.get('rr') or s.get('or') or s.get('hr')
        if effect is not None:
            effects.append(effect)
            weight = s.get('weight') or (s.get('n_i', 0) + s.get('n_c', 0)) or 100
            weights.append(weight)
    
    if not effects:
        return None
    
    total_weight = sum(weights)
    pooled_effect = sum(e * w for e, w in zip(effects, weights)) / total_weight
    
    # Usar CI del primer estudio o defaults
    ci_lower = studies[0].get('ci_lower') or studies[0].get('rr_ci_lower')
    ci_upper = studies[0].get('ci_upper') or studies[0].get('rr_ci_upper')
    
    direction = determine_direction(pooled_effect, ci_lower, ci_upper)
    magnitude = determine_magnitude(pooled_effect)
    
    # Generar texto
    direction_text = {
        "favors_intervention": "reduce",
        "favors_control": "aumenta",
        "no_difference": "no tiene efecto significativo sobre",
        "uncertain": "tiene efecto incierto sobre"
    }
    
    magnitude_text = {
        "large": "marcadamente",
        "moderate": "moderadamente",
        "small": "levemente",
        "uncertain": ""
    }
    
    claim_text = f"{intervention} {direction_text.get(direction, 'tiene efecto sobre')} {magnitude_text.get(magnitude, '')} {outcome} vs {control}".strip()
    
    # Recopilar estudios de soporte
    supporting_studies = []
    for s in studies:
        effect = s.get('effect_size') or s.get('rr') or s.get('or') or s.get('hr')
        if effect is not None:
            supporting_studies.append({
                "study_id": s.get('study_id', ''),
                "pmid": s.get('pmid', ''),
                "author": s.get('author', ''),
                "effect_size": effect,
                "ci_lower": s.get('ci_lower') or s.get('rr_ci_lower'),
                "ci_upper": s.get('ci_upper') or s.get('rr_ci_upper'),
                "n_total": (s.get('n_i', 0) + s.get('n_c', 0)) or s.get('n_total')
            })
    
    consistency = calculate_consistency(studies)
    
    return {
        "claim_id": "C001",
        "claim_text": claim_text,
        "claim_type": "efficacy",
        "direction": direction,
        "magnitude": magnitude,
        "pooled_effect": pooled_effect,
        "supporting_studies": supporting_studies,
        "n_supporting": len(supporting_studies),
        "consistency_score": consistency,
        "clinical_significance": "high" if magnitude == "large" and consistency > 0.8 else "moderate" if magnitude == "moderate" else "low"
    }


def extract_subgroup_claims(studies):
    """Extrae afirmaciones de subgrupos si existen."""
    claims = []
    
    # Buscar diferentes subgrupos
    subgroups = {}
    for s in studies:
        sg = s.get('subgroup')
        if sg:
            if sg not in subgroups:
                subgroups[sg] = []
            subgroups[sg].append(s)
    
    if len(subgroups) >= 2:
        for sg_name, sg_studies in subgroups.items():
            effects = [s.get('rr') or s.get('effect_size') for s in sg_studies if s.get('rr') or s.get('effect_size')]
            if effects:
                pooled = sum(effects) / len(effects)
                claims.append({
                    "claim_id": f"C_{sg_name}",
                    "claim_text": f"En subgrupo {sg_name}: efecto {pooled:.2f}",
                    "claim_type": "subgroup",
                    "subgroup": sg_name,
                    "pooled_effect": pooled,
                    "n_studies": len(sg_studies),
                    "supporting_studies": [s.get('study_id', '') for s in sg_studies]
                })
    
    return claims


def generate_claims(studies):
    """Genera todas las afirmaciones."""
    all_claims = []
    
    main_claim = extract_main_claim(studies)
    if main_claim:
        all_claims.append(main_claim)
    
    subgroup_claims = extract_subgroup_claims(studies)
    all_claims.extend(subgroup_claims)
    
    total_studies = len(set(s.get('study_id', '') for s in studies))
    
    return {
        "claims": all_claims,
        "meta": {
            "total_claims": len(all_claims),
            "total_studies_analyzed": total_studies,
            "extraction_date": datetime.now().isoformat(),
            "version": "1.0"
        }
    }


def save_outputs(result, output_dir):
    """Guarda archivos de salida con auditoría."""
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. JSON principal (usando save_json_safe para manejar tipos NumPy)
    claims_file = outdir / f"claims_extracted_{timestamp}.json"
    save_json_safe(result, claims_file)
    
    # 2. Log
    log_file = outdir / f"claims_extraction_log_{timestamp}.txt"
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=== LOG DE EXTRACCIÓN DE AFIRMACIONES ===\n\n")
        f.write(f"Fecha: {result['meta']['extraction_date']}\n")
        f.write(f"Estudios analizados: {result['meta']['total_studies_analyzed']}\n")
        f.write(f"Afirmaciones generadas: {result['meta']['total_claims']}\n\n")
        
        for claim in result['claims']:
            f.write(f"\n--- {claim['claim_id']} ---\n")
            f.write(f"Tipo: {claim['claim_type']}\n")
            f.write(f"Afirmación: {claim['claim_text']}\n")
            f.write(f"Dirección: {claim.get('direction', 'N/A')}\n")
            f.write(f"Magnitud: {claim.get('magnitude', 'N/A')}\n")
            f.write(f"Estudios de soporte: {claim.get('n_supporting', 0)}\n")
            f.write(f"Consistencia: {claim.get('consistency_score', 0):.2f}\n")
    
    # 3. Mapeo CSV
    mapping_file = outdir / f"claims_source_mapping_{timestamp}.csv"
    with open(mapping_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['claim_id', 'claim_text', 'study_id', 'pmid', 'effect_size', 'weight'])
        
        for claim in result['claims']:
            for study in claim.get('supporting_studies', []):
                if isinstance(study, dict):
                    writer.writerow([
                        claim['claim_id'],
                        claim['claim_text'][:100] + '...',
                        study.get('study_id', ''),
                        study.get('pmid', ''),
                        study.get('effect_size', ''),
                        study.get('weight', '')
                    ])
    
    return {
        "claims_file": str(claims_file),
        "log_file": str(log_file),
        "mapping_file": str(mapping_file)
    }


def main():
    parser = argparse.ArgumentParser(description='Extractor de Afirmaciones Clínicas')
    parser.add_argument('--input', '-i', required=True, help='CSV con datos de estudios')
    parser.add_argument('--output', '-o', default='output', help='Directorio de salida')
    
    args = parser.parse_args()
    
    logger.info(f"📊 Cargando datos desde {args.input}...")
    studies = load_studies(args.input)
    logger.info(f"   {len(studies)} registros cargados")
    
    # Validar datos de entrada
    is_valid, errors = validate_studies_data(studies)
    if not is_valid:
        logger.error(f"❌ Error de validación:")
        for error in errors:
            logger.error(f"   - {error}")
        sys.exit(1)
    
    logger.info("✅ Datos validados correctamente")
    
    logger.info("🔍 Extrayendo afirmaciones...")
    result = generate_claims(studies)
    logger.info(f"   {result['meta']['total_claims']} afirmaciones generadas")
    
    logger.info("💾 Guardando archivos...")
    files = save_outputs(result, args.output)
    
    logger.info(f"\n✅ Completado!")
    logger.info(f"   📄 Afirmaciones: {files['claims_file']}")
    logger.info(f"   📋 Log: {files['log_file']}")
    logger.info(f"   🔗 Mapeo: {files['mapping_file']}")
    
    logger.info(f"\n📋 RESUMEN:")
    for claim in result['claims']:
        logger.info(f"\n   [{claim['claim_id']}] {claim['claim_type'].upper()}")
        logger.info(f"   {claim['claim_text']}")
        logger.info(f"   └─ {claim.get('n_supporting', 0)} estudios | Consistencia: {claim.get('consistency_score', 0):.0%}")


if __name__ == '__main__':
    main()
