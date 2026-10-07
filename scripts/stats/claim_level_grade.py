#!/usr/bin/env python3
"""
claim_level_grade.py - Evaluación GRADE a Nivel de Afirmación

Evalúa la calidad de evidencia y fuerza de recomendación para cada afirmación
extraída por el Claim Extractor.

Input: JSON del Claim Extractor + datos del pipeline (RoB, heterogeneidad, etc.)
Output: JSON con evaluación GRADE por afirmación + archivos de auditoría

Uso:
    python3 claim_level_grade.py --claims claims.json --pipeline-data data.json --output output/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


class GRADERating:
    """Niveles de certeza GRADE."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


class ClaimLevelGRADE:
    """
    Evaluación GRADE para afirmaciones individuales.
    
    Cada afirmación se evalúa con los 5 factores de downgrade y 3 de upgrade.
    Genera calidad de evidencia + fuerza de recomendación.
    """
    
    def __init__(self):
        self.ratings_order = {
            GRADERating.HIGH: 4,
            GRADERating.MODERATE: 3,
            GRADERating.LOW: 2,
            GRADERating.VERY_LOW: 1,
        }
    
    def evaluate_risk_of_bias(self, studies):
        """
        Evalúa riesgo de sesgo en estudios de soporte.
        
        Returns: (downgrade_level, reason)
        """
        # Filtrar solo estudios que son diccionarios (no strings)
        valid_studies = [s for s in studies if isinstance(s, dict)]
        
        if not valid_studies:
            return 0, "Sin datos de RoB disponibles"
        
        # Contar estudios por nivel de RoB
        high_rob = sum(1 for s in valid_studies if s.get('rob_level') == 'high')
        some_rob = sum(1 for s in valid_studies if s.get('rob_level') == 'some_concerns')
        total = len(valid_studies)
        
        if total == 0:
            return 0, "Sin datos de RoB"
        
        high_pct = high_rob / total
        some_pct = some_rob / total
        
        if high_pct >= 0.5:
            return 2, f"Mayoría con alto RoB ({high_rob}/{total})"
        elif high_pct >= 0.25 or some_pct >= 0.5:
            return 1, f"Algunos con alto RoB ({high_rob}/{total}) o mitad con preocupaciones"
        else:
            return 0, "Mayoría con bajo RoB"
    
    def evaluate_inconsistency(self, claim):
        """
        Evalúa consistencia entre estudios.
        
        Returns: (downgrade_level, reason)
        """
        consistency = claim.get('consistency_score', 1.0)
        
        # Buscar I² en múltiples ubicaciones posibles
        i2 = 0
        if 'i2' in claim:
            i2 = claim['i2']
        elif 'heterogeneity' in claim and isinstance(claim['heterogeneity'], dict):
            i2 = claim['heterogeneity'].get('I2', 0)
        elif 'heterogeneity' in claim and isinstance(claim['heterogeneity'], (int, float)):
            i2 = claim['heterogeneity']
        
        if consistency < 0.5 or i2 > 75:
            return 2, f"Inconsistencia severa (consistencia={consistency:.0%}, I²={i2}%)"
        elif consistency < 0.75 or i2 > 50:
            return 1, f"Inconsistencia moderada (consistencia={consistency:.0%}, I²={i2}%)"
        else:
            return 0, f"Consistente (consistencia={consistency:.0%}, I²={i2}%)"
    
    def evaluate_imprecision(self, claim):
        """
        Evalúa imprecisión del estimado.
        
        Returns: (downgrade_level, reason)
        """
        effect = claim.get('pooled_effect')
        ci_lower = claim.get('ci_lower')
        ci_upper = claim.get('ci_upper')
        n_supporting = claim.get('n_supporting', 0)
        
        if effect is None:
            return 2, "Sin estimado de efecto"
        
        # Verificar si CI cruza nulo (1.0 para RR/OR, 0 para RD)
        crosses_null = False
        if ci_lower is not None and ci_upper is not None:
            # Para RR/OR: nulo = 1.0
            if ci_lower < 1.0 < ci_upper:
                crosses_null = True
        
        # Imprecisión por tamaño muestral
        small_sample = n_supporting < 3
        
        if crosses_null and small_sample:
            return 2, f"CI cruza nulo y pocos estudios (N={n_supporting})"
        elif crosses_null or small_sample:
            return 1, f"CI cruza nulo" if crosses_null else f"Pocos estudios (N={n_supporting})"
        else:
            return 0, "Precisión adecuada"
    
    def evaluate_publication_bias(self, studies):
        """
        Evalúa sesgo de publicación.
        
        Returns: (downgrade_level, reason)
        """
        # Buscar datos de Egger o funnel plot
        egger_p = None
        for s in studies:
            if 'egger_p' in s:
                egger_p = s['egger_p']
                break
        
        if egger_p is not None and egger_p < 0.10:
            return 1, f"Egger test significativo (p={egger_p:.3f})"
        elif egger_p is not None:
            return 0, f"Sin evidencia de sesgo (Egger p={egger_p:.3f})"
        else:
            return 0, "Sin datos de sesgo de publicación"
    
    def evaluate_indirectness(self, claim):
        """
        Evalúa indirectitud (PICO diferente).
        
        Returns: (downgrade_level, reason)
        """
        # Por simplicidad, asumimos indirectitud si hay subgrupos o dosis diferentes
        subgroups = set()
        for study in claim.get('supporting_studies', []):
            if isinstance(study, dict) and 'subgroup' in study:
                subgroups.add(study['subgroup'])
        
        if len(subgroups) > 2:
            return 1, f"Múltiples poblaciones/dosis ({len(subgroups)} subgrupos)"
        else:
            return 0, "Población/intervención homogénea"
    
    def calculate_upgrade(self, claim):
        """
        Calcula upgrades (solo para evidencia observacional).
        
        Returns: (upgrade_level, reason)
        """
        upgrades = []
        
        # Upgrade por magnitud grande
        magnitude = claim.get('magnitude', 'uncertain')
        if magnitude == 'large':
            upgrades.append((1, "Magnitud grande del efecto"))
        
        # Upgrade por dosis-respuesta
        if claim.get('claim_type') == 'dosing':
            upgrades.append((1, "Relación dosis-respuesta"))
        
        return upgrades
    
    def evaluate_claim(self, claim, pipeline_data=None):
        """
        Evalúa una afirmación con GRADE completo.
        
        Parameters:
        -----------
        claim : dict
            Afirmación del Claim Extractor
        pipeline_data : dict, optional
            Datos adicionales del pipeline (RoB, heterogeneidad, etc.)
        
        Returns:
        --------
        dict con evaluación GRADE completa
        """
        studies = claim.get('supporting_studies', [])
        
        # Determinar diseño base (RCT vs observacional)
        # Por defecto RCT si no hay información
        study_design = "RCT"
        if pipeline_data and 'study_designs' in pipeline_data:
            # La mayoría determina el diseño
            designs = pipeline_data['study_designs']
            if designs.count('observational') > designs.count('RCT'):
                study_design = "observational"
        
        # Certeza base
        base_rating = GRADERating.HIGH if study_design == "RCT" else GRADERating.LOW
        
        # Evaluar factores de downgrade
        downgrades = []
        
        # 1. Riesgo de sesgo
        rob_down, rob_reason = self.evaluate_risk_of_bias(studies)
        if rob_down > 0:
            downgrades.append({
                "factor": "risk_of_bias",
                "severity": rob_down,
                "reason": rob_reason
            })
        
        # 2. Inconsistencia
        inc_down, inc_reason = self.evaluate_inconsistency(claim)
        if inc_down > 0:
            downgrades.append({
                "factor": "inconsistency",
                "severity": inc_down,
                "reason": inc_reason
            })
        
        # 3. Imprecisión
        imp_down, imp_reason = self.evaluate_imprecision(claim)
        if imp_down > 0:
            downgrades.append({
                "factor": "imprecision",
                "severity": imp_down,
                "reason": imp_reason
            })
        
        # 4. Indirectitud
        ind_down, ind_reason = self.evaluate_indirectness(claim)
        if ind_down > 0:
            downgrades.append({
                "factor": "indirectness",
                "severity": ind_down,
                "reason": ind_reason
            })
        
        # 5. Sesgo de publicación
        pub_down, pub_reason = self.evaluate_publication_bias(studies)
        if pub_down > 0:
            downgrades.append({
                "factor": "publication_bias",
                "severity": pub_down,
                "reason": pub_reason
            })
        
        # Evaluar upgrades (solo observacionales)
        upgrades = []
        if study_design == "observational":
            upgrades = self.calculate_upgrade(claim)
        
        # Calcular rating final
        base_value = self.ratings_order[base_rating]
        total_down = sum(d["severity"] for d in downgrades)
        total_up = sum(u[0] for u in upgrades)
        
        final_value = base_value - total_down + total_up
        final_value = max(1, min(4, final_value))
        
        reverse_map = {v: k for k, v in self.ratings_order.items()}
        final_rating = reverse_map[final_value]
        
        # Calcular fuerza de recomendación
        recommendation = self._calculate_recommendation(final_rating, claim)
        
        return {
            "claim_id": claim.get('claim_id'),
            "claim_text": claim.get('claim_text'),
            "study_design": study_design,
            "base_rating": base_rating,
            "overall_quality": final_rating,
            "clinical_rating": recommendation,
            "downgrades": downgrades,
            "upgrades": [{"factor": u[1], "magnitude": u[0]} for u in upgrades],
            "final_rating": final_rating,
            "total_downgrades": total_down,
            "total_upgrades": total_up,
            "recommendation_strength": recommendation,
            "recommendation_rationale": f"Evidencia {final_rating} con {total_down} factores de downgrade",
            "confidence_statement": self._generate_confidence_statement(final_rating)
        }
    
    def _calculate_recommendation(self, rating, claim):
        """Calcula fuerza de recomendación basada en evidencia."""
        direction = claim.get('direction', 'uncertain')
        magnitude = claim.get('magnitude', 'uncertain')
        
        if rating == GRADERating.HIGH and direction != 'uncertain':
            return "STRONG"
        elif rating == GRADERating.MODERATE and direction != 'uncertain':
            return "CONDITIONAL"
        elif rating == GRADERating.LOW and direction != 'uncertain':
            return "WEAK"
        else:
            return "WEAK"
    
    def _generate_confidence_statement(self, rating):
        """Genera declaración de confianza."""
        statements = {
            GRADERating.HIGH: "Muy confiado en que el efecto real está cerca del estimado",
            GRADERating.MODERATE: "Moderadamente confiado; el efecto real puede ser sustancialmente diferente",
            GRADERating.LOW: "Confianza limitada; el efecto real puede ser sustancialmente diferente",
            GRADERating.VERY_LOW: "Muy poca confianza; la estimación es muy incierta"
        }
        return statements.get(rating, "Confianza no evaluada")
    
    def generate_grade_table(self, evaluations):
        """Genera tabla Markdown GRADE para manuscrito."""
        lines = [
            "## Evaluación GRADE por Afirmación",
            "",
            "| Afirmación | Evidencia | Recomendación | Factores de downgrade |",
            "|------------|-----------|---------------|----------------------|",
        ]
        
        for eval in evaluations:
            claim_short = eval['claim_text'][:60] + "..." if len(eval['claim_text']) > 60 else eval['claim_text']
            downgrade_summary = "; ".join([d['factor'] for d in eval['downgrades']]) if eval['downgrades'] else "Ninguno"
            
            lines.append(
                f"| {claim_short} | {eval['final_rating'].upper()} | "
                f"{eval['recommendation_strength'].upper()} | {downgrade_summary} |"
            )
        
        lines.extend([
            "",
            "**Leyenda:**",
            "- Evidencia: HIGH > MODERATE > LOW > VERY_LOW",
            "- Recomendación: STRONG > CONDITIONAL > WEAK"
        ])
        
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Evaluación GRADE a Nivel de Afirmación')
    parser.add_argument('--claims', '-c', required=True, help='JSON del Claim Extractor')
    parser.add_argument('--output', '-o', default='output', help='Directorio de salida')
    
    args = parser.parse_args()
    
    # Cargar afirmaciones
    print(f"📊 Cargando afirmaciones desde {args.claims}...")
    with open(args.claims, 'r', encoding='utf-8') as f:
        claims_data = json.load(f)
    
    claims = claims_data.get('claims', [])
    print(f"   {len(claims)} afirmaciones cargadas")
    
    # Evaluar cada afirmación
    print("🔍 Evaluando con GRADE...")
    grader = ClaimLevelGRADE()
    evaluations = []
    
    for claim in claims:
        evaluation = grader.evaluate_claim(claim)
        evaluations.append(evaluation)
        print(f"   ✅ {claim.get('claim_id')}: {evaluation['final_rating'].upper()} → {evaluation['recommendation_strength'].upper()}")
    
    # Guardar resultados
    print("💾 Guardando archivos...")
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # JSON principal
    result = {
        "claim_grades": evaluations,
        "meta": {
            "total_evaluated": len(evaluations),
            "high": sum(1 for e in evaluations if e['final_rating'] == GRADERating.HIGH),
            "moderate": sum(1 for e in evaluations if e['final_rating'] == GRADERating.MODERATE),
            "low": sum(1 for e in evaluations if e['final_rating'] == GRADERating.LOW),
            "very_low": sum(1 for e in evaluations if e['final_rating'] == GRADERating.VERY_LOW),
            "evaluation_date": datetime.now().isoformat(),
            "version": "1.0"
        }
    }
    
    grade_file = outdir / f"grade_claim_level_{timestamp}.json"
    with open(grade_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    # Explicación textual
    explanation_file = outdir / f"grade_explanation_{timestamp}.txt"
    with open(explanation_file, 'w', encoding='utf-8') as f:
        f.write("=== EXPLICACIÓN GRADE POR AFIRMACIÓN ===\n\n")
        for eval in evaluations:
            f.write(f"\n--- {eval['claim_id']} ---\n")
            f.write(f"Afirmación: {eval['claim_text']}\n")
            f.write(f"Calidad de evidencia: {eval['final_rating'].upper()}\n")
            f.write(f"Recomendación: {eval['recommendation_strength'].upper()}\n")
            f.write(f"Razonamiento: {eval['recommendation_rationale']}\n")
            f.write(f"Confianza: {eval['confidence_statement']}\n")
            
            if eval['downgrades']:
                f.write(f"\nFactores que reducen calidad:\n")
                for d in eval['downgrades']:
                    f.write(f"  - {d['factor']}: {d['reason']} (-{d['severity']})\n")
    
    # Tabla Markdown
    table_file = outdir / f"grade_table_{timestamp}.md"
    with open(table_file, 'w', encoding='utf-8') as f:
        f.write(grader.generate_grade_table(evaluations))
    
    print(f"\n✅ Completado!")
    print(f"   📄 Evaluación: {grade_file}")
    print(f"   📋 Explicación: {explanation_file}")
    print(f"   📊 Tabla: {table_file}")
    
    # Resumen
    print(f"\n📋 RESUMEN GRADE:")
    print(f"   HIGH: {result['meta']['high']}")
    print(f"   MODERATE: {result['meta']['moderate']}")
    print(f"   LOW: {result['meta']['low']}")
    print(f"   VERY_LOW: {result['meta']['very_low']}")


if __name__ == '__main__':
    main()
