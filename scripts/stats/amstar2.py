#!/usr/bin/env python3
"""
amstar2.py — Evaluación AMSTAR 2 (A MeaSurement Tool to Assess systematic Reviews)

Implementa los 16 criterios AMSTAR 2 para evaluar calidad de revisiones sistemáticas.
Cada criterio se evalúa como: Sí, Parcialmente, No, o No aplica.

Criterios críticos (deben cumplirse para alta calidad):
• C2: Protocolo pre-especificado (PROSPERO)
• C4: Búsqueda exhaustiva (≥2 bases, ≥1 registro de trials)
• C7: Extracción doble (independiente + conciliación)
• C9: Evaluación de riesgo de sesgo (RoB en cada estudio)
• C11: Meta-análisis apropiado (método adecuado al diseño)
• C13: Investigación de heterogeneidad (fuentes + subgrupos)
• C15: Investigación de sesgo de publicación

Uso:
    from amstar2 import AMSTAR2Assessment
    
    amstar = AMSTAR2Assessment()
    amstar.evaluate_criterion("C2", "yes", "Protocolo registrado en PROSPERO CRD420256789")
    amstar.evaluate_criterion("C4", "yes", "PubMed, Cochrane, EMBASE, CT.gov")
    ...
    
    result = amstar.get_overall_rating()
    # {"rating": "High", "critical_flaws": 0, "non_critical_flaws": 2}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AMSTAR2Rating(str, Enum):
    """Niveles de calidad AMSTAR 2."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    CRITICALLY_LOW = "critically_low"


class CriterionStatus(str, Enum):
    """Estado de cada criterio AMSTAR 2."""
    YES = "yes"
    PARTIAL = "partial"
    NO = "no"
    NA = "na"


@dataclass
class Criterion:
    """Un criterio AMSTAR 2 individual."""
    code: str
    description: str
    is_critical: bool
    status: CriterionStatus = CriterionStatus.NA
    notes: str = ""


class AMSTAR2Assessment:
    """
    Evaluación AMSTAR 2 completa.
    
    Los 16 criterios se evalúan según el instrumento oficial AMSTAR 2.
    La calidad global depende del número de deficiencias en criterios críticos.
    """
    
    CRITERIA_DEFINITIONS = [
        # Criterios críticos (7)
        ("C2", "¿Se estableció un protocolo de revisión antes de realizarla?", True),
        ("C4", "¿La estrategia de búsqueda fue apropiada y exhaustiva?", True),
        ("C7", "¿Se realizó extracción de datos en duplicado?", True),
        ("C9", "¿Se evaluó el riesgo de sesgo de los estudios incluidos?", True),
        ("C11", "¿Se utilizaron métodos apropiados para el meta-análisis?", True),
        ("C13", "¿Se investigaron las fuentes de heterogeneidad?", True),
        ("C15", "¿Se investigó el sesgo de publicación?", True),
        # Criterios no críticos (9)
        ("C1", "¿Se planteó la pregunta de investigación de forma apropiada?", False),
        ("C3", "¿Se justificaron las exclusiones de estudios?", False),
        ("C5", "¿Se realizó selección de estudios en duplicado?", False),
        ("C6", "¿Se describieron las características de los estudios incluidos?", False),
        ("C8", "¿Se describieron los métodos de síntesis de forma adecuada?", False),
        ("C10", "¿Se reportaron las fuentes de financiamiento de los estudios?", False),
        ("C12", "¿Se consideraron el riesgo de sesgo al interpretar resultados?", False),
        ("C14", "¿Los resultados se presentaron con moderación apropiada?", False),
        ("C16", "¿Se reportaron los conflictos de interés de la revisión?", False),
    ]
    
    def __init__(self):
        self.criteria: Dict[str, Criterion] = {}
        self._init_criteria()
    
    def _init_criteria(self):
        """Inicializa todos los criterios con estado NA."""
        for code, description, is_critical in self.CRITERIA_DEFINITIONS:
            self.criteria[code] = Criterion(
                code=code,
                description=description,
                is_critical=is_critical,
                status=CriterionStatus.NA
            )
    
    def evaluate_criterion(self, code: str, status: str, notes: str = "") -> None:
        """
        Evalúa un criterio específico.
        
        Parameters
        ----------
        code : str
            Código del criterio (C1-C16)
        status : str
            "yes", "partial", "no", "na"
        notes : str
            Justificación de la evaluación
        """
        if code not in self.criteria:
            raise ValueError(f"Criterio {code} no existe. Use C1-C16.")
        
        try:
            criterion_status = CriterionStatus(status.lower())
        except ValueError:
            raise ValueError(f"Estado '{status}' inválido. Use: yes, partial, no, na")
        
        self.criteria[code].status = criterion_status
        self.criteria[code].notes = notes
    
    def get_critical_flaws(self) -> Tuple[int, List[str]]:
        """
        Retorna número de deficiencias críticas y sus códigos.
        
        Una deficiencia crítica = criterio crítico con estado "no".
        """
        flaws = []
        for code, criterion in self.criteria.items():
            if criterion.is_critical and criterion.status == CriterionStatus.NO:
                flaws.append(code)
        return len(flaws), flaws
    
    def get_non_critical_flaws(self) -> Tuple[int, List[str]]:
        """
        Retorna número de deficiencias no críticas y sus códigos.
        
        Una deficiencia = criterio no crítico con estado "no".
        """
        flaws = []
        for code, criterion in self.criteria.items():
            if not criterion.is_critical and criterion.status == CriterionStatus.NO:
                flaws.append(code)
        return len(flaws), flaws
    
    def get_overall_rating(self) -> Dict:
        """
        Calcula calidad global según reglas AMSTAR 2.
        
        Reglas:
        • High: 0-1 deficiencia no crítica, 0 críticas
        • Moderate: >1 deficiencia no crítica, 0 críticas
        • Low: 1 deficiencia crítica
        • Critically Low: >1 deficiencia crítica
        """
        critical_count, critical_codes = self.get_critical_flaws()
        non_critical_count, non_critical_codes = self.get_non_critical_flaws()
        
        if critical_count == 0:
            if non_critical_count <= 1:
                rating = AMSTAR2Rating.HIGH
            else:
                rating = AMSTAR2Rating.MODERATE
        elif critical_count == 1:
            rating = AMSTAR2Rating.LOW
        else:
            rating = AMSTAR2Rating.CRITICALLY_LOW
        
        return {
            "rating": rating.value,
            "rating_display": self._get_rating_display(rating),
            "critical_flaws": critical_count,
            "critical_flaw_codes": critical_codes,
            "non_critical_flaws": non_critical_count,
            "non_critical_flaw_codes": non_critical_codes,
            "total_criteria_evaluated": sum(1 for c in self.criteria.values() 
                                             if c.status != CriterionStatus.NA),
            "recommendation": self._get_recommendation(rating)
        }
    
    def _get_rating_display(self, rating: AMSTAR2Rating) -> str:
        """Texto legible del rating."""
        displays = {
            AMSTAR2Rating.HIGH: "Alta calidad",
            AMSTAR2Rating.MODERATE: "Calidad moderada",
            AMSTAR2Rating.LOW: "Calidad baja",
            AMSTAR2Rating.CRITICALLY_LOW: "Calidad críticamente baja"
        }
        return displays[rating]
    
    def _get_recommendation(self, rating: AMSTAR2Rating) -> str:
        """Recomendación basada en calidad."""
        recommendations = {
            AMSTAR2Rating.HIGH: "Revisión confiable. Resultados pueden guiar práctica clínica.",
            AMSTAR2Rating.MODERATE: "Revisión aceptable con limitaciones menores. Interpretar con cautela.",
            AMSTAR2Rating.LOW: "Revisión con deficiencia crítica. Resultados pueden no ser confiables.",
            AMSTAR2Rating.CRITICALLY_LOW: "Revisión con múltiples deficiencias críticas. No confiar en resultados."
        }
        return recommendations[rating]
    
    def get_detailed_report(self) -> Dict:
        """Reporte completo con todos los criterios."""
        return {
            "overall": self.get_overall_rating(),
            "criteria": [
                {
                    "code": c.code,
                    "description": c.description,
                    "is_critical": c.is_critical,
                    "status": c.status.value,
                    "notes": c.notes
                }
                for c in self.criteria.values()
            ],
            "summary": {
                "total": len(self.criteria),
                "critical": sum(1 for c in self.criteria.values() if c.is_critical),
                "non_critical": sum(1 for c in self.criteria.values() if not c.is_critical),
                "yes": sum(1 for c in self.criteria.values() if c.status == CriterionStatus.YES),
                "partial": sum(1 for c in self.criteria.values() if c.status == CriterionStatus.PARTIAL),
                "no": sum(1 for c in self.criteria.values() if c.status == CriterionStatus.NO),
                "na": sum(1 for c in self.criteria.values() if c.status == CriterionStatus.NA),
            }
        }
    
    def export_report(self, output_dir: str = "amstar2_output") -> str:
        """Exporta reporte AMSTAR 2 a JSON."""
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        
        report = self.get_detailed_report()
        filepath = outdir / f"amstar2_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def generate_markdown_table(self) -> str:
        """Genera tabla Markdown para incluir en manuscrito."""
        lines = [
            "## Evaluación AMSTAR 2",
            "",
            "| Criterio | Descripción | Crítico | Estado | Notas |",
            "|----------|-------------|---------|--------|-------|",
        ]
        
        for code in sorted(self.criteria.keys()):
            c = self.criteria[code]
            critical = "Sí" if c.is_critical else "No"
            status_emoji = {
                CriterionStatus.YES: "✅",
                CriterionStatus.PARTIAL: "⚠️",
                CriterionStatus.NO: "❌",
                CriterionStatus.NA: "⬜"
            }
            lines.append(
                f"| {c.code} | {c.description} | {critical} | {status_emoji[c.status]} {c.status.value} | {c.notes} |"
            )
        
        overall = self.get_overall_rating()
        lines.extend([
            "",
            f"**Calidad global: {overall['rating_display']}** ({overall['rating']})",
            "",
            f"- Deficiencias críticas: {overall['critical_flaws']}",
            f"- Deficiencias no críticas: {overall['non_critical_flaws']}",
            "",
            f"> {overall['recommendation']}"
        ])
        
        return "\n".join(lines)


def auto_evaluate_from_pipeline(
    has_protocol: bool = False,
    search_databases: int = 0,
    double_screening: bool = False,
    double_extraction: bool = False,
    rob_assessment: bool = False,
    meta_analysis_method: Optional[str] = None,
    heterogeneity_investigation: bool = False,
    publication_bias_test: bool = False,
    funding_reported: bool = False,
    conflicts_reported: bool = False
) -> AMSTAR2Assessment:
    """
    Auto-evalúa AMSTAR 2 basado en parámetros del pipeline.
    
    Uso:
        amstar = auto_evaluate_from_pipeline(
            has_protocol=True,
            search_databases=4,  # PubMed, Cochrane, EMBASE, CT.gov
            double_screening=True,
            double_extraction=True,
            ...
        )
    """
    amstar = AMSTAR2Assessment()
    
    # C1: Pregunta apropiada (siempre "yes" si se usó PICO)
    amstar.evaluate_criterion("C1", "yes", "Pregunta estructurada con PICO")
    
    # C2: Protocolo
    amstar.evaluate_criterion(
        "C2", 
        "yes" if has_protocol else "no",
        "Protocolo registrado en PROSPERO" if has_protocol else "No se registró protocolo"
    )
    
    # C3: Justificación exclusiones (evaluado manualmente)
    amstar.evaluate_criterion("C3", "partial", "Requiere revisión manual de justificaciones")
    
    # C4: Búsqueda exhaustiva
    if search_databases >= 4:
        amstar.evaluate_criterion("C4", "yes", f"Búsqueda en {search_databases} bases/incluyendo registros de trials")
    elif search_databases >= 2:
        amstar.evaluate_criterion("C4", "partial", f"Búsqueda en {search_databases} bases, podría ampliarse")
    else:
        amstar.evaluate_criterion("C4", "no", f"Solo {search_databases} base(s), insuficiente")
    
    # C5: Selección duplicada
    amstar.evaluate_criterion(
        "C5",
        "yes" if double_screening else "no",
        "Screening doble ciego con κ" if double_screening else "Screening simple"
    )
    
    # C6: Características estudios (evaluado manualmente)
    amstar.evaluate_criterion("C6", "partial", "Tabla de características generada, requiere revisión")
    
    # C7: Extracción duplicada
    amstar.evaluate_criterion(
        "C7",
        "yes" if double_extraction else "no",
        "Extracción doble con ICC" if double_extraction else "Extracción simple"
    )
    
    # C8: Métodos de síntesis
    if meta_analysis_method in ["DL", "REML", "HS", "SJ", "ML", "Bayesian"]:
        amstar.evaluate_criterion("C8", "yes", f"Meta-análisis con modelo {meta_analysis_method}")
    else:
        amstar.evaluate_criterion("C8", "partial", "Método de síntesis no especificado o no estándar")
    
    # C9: RoB evaluado
    amstar.evaluate_criterion(
        "C9",
        "yes" if rob_assessment else "no",
        "RoB 2.0 / ROBINS-I aplicado" if rob_assessment else "Sin evaluación de riesgo de sesgo"
    )
    
    # C10: Financiamiento
    amstar.evaluate_criterion(
        "C10",
        "yes" if funding_reported else "partial",
        "Fuentes de financiamiento reportadas" if funding_reported else "Parcialmente reportado"
    )
    
    # C11: Meta-análisis apropiado
    if meta_analysis_method in ["DL", "REML", "HS", "SJ", "Bayesian"]:
        amstar.evaluate_criterion("C11", "yes", f"Método robusto: {meta_analysis_method}")
    elif meta_analysis_method:
        amstar.evaluate_criterion("C11", "partial", f"Método: {meta_analysis_method}, podría mejorar")
    else:
        amstar.evaluate_criterion("C11", "no", "Sin meta-análisis")
    
    # C12: RoB en interpretación
    amstar.evaluate_criterion(
        "C12",
        "yes" if rob_assessment else "no",
        "Considerado en discusión" if rob_assessment else "No considerado"
    )
    
    # C13: Heterogeneidad
    amstar.evaluate_criterion(
        "C13",
        "yes" if heterogeneity_investigation else "no",
        "Subgrupos y meta-regresión explorados" if heterogeneity_investigation else "Sin exploración de heterogeneidad"
    )
    
    # C14: Moderación resultados
    amstar.evaluate_criterion("C14", "partial", "Limitaciones y generalizabilidad discutidas")
    
    # C15: Sesgo de publicación
    amstar.evaluate_criterion(
        "C15",
        "yes" if publication_bias_test else "no",
        "Egger/PET-PEESE/trim-fill aplicados" if publication_bias_test else "Sin test de sesgo"
    )
    
    # C16: Conflictos de interés
    amstar.evaluate_criterion(
        "C16",
        "yes" if conflicts_reported else "no",
        "Conflictos reportados" if conflicts_reported else "No reportados"
    )
    
    return amstar


# ── test / demo ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== AMSTAR 2 Demo ===\n")
    
    # Demo 1: Evaluación manual
    amstar = AMSTAR2Assessment()
    amstar.evaluate_criterion("C2", "yes", "Protocolo PROSPERO CRD420256789")
    amstar.evaluate_criterion("C4", "yes", "PubMed, Cochrane, EMBASE, CT.gov")
    amstar.evaluate_criterion("C7", "yes", "Extracción doble con ICC=0.91")
    amstar.evaluate_criterion("C9", "yes", "RoB 2.0 aplicado")
    amstar.evaluate_criterion("C11", "yes", "DL random effects")
    amstar.evaluate_criterion("C13", "yes", "Subgrupos por dosis y población")
    amstar.evaluate_criterion("C15", "yes", "Egger p=0.12, no sesgo")
    
    # Algunos no críticos como no
    amstar.evaluate_criterion("C10", "no", "Financiamiento no reportado en todos los estudios")
    amstar.evaluate_criterion("C16", "no", "Conflictos no reportados")
    
    overall = amstar.get_overall_rating()
    print(f"Calidad global: {overall['rating_display']} ({overall['rating']})")
    print(f"Deficiencias críticas: {overall['critical_flaws']}")
    print(f"Deficiencias no críticas: {overall['non_critical_flaws']}")
    print(f"\n{overall['recommendation']}\n")
    
    # Demo 2: Auto-evaluación desde pipeline
    print("\n=== Auto-evaluación desde Pipeline ===\n")
    amstar2 = auto_evaluate_from_pipeline(
        has_protocol=True,
        search_databases=4,
        double_screening=True,
        double_extraction=True,
        rob_assessment=True,
        meta_analysis_method="DL",
        heterogeneity_investigation=True,
        publication_bias_test=True,
        funding_reported=True,
        conflicts_reported=False
    )
    
    overall2 = amstar2.get_overall_rating()
    print(f"Calidad global: {overall2['rating_display']}")
    print(f"\nTabla Markdown:\n")
    print(amstar2.generate_markdown_table())
