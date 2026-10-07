#!/usr/bin/env python3
"""
risk_of_bias.py — Evaluación de Riesgo de Sesgo (RoB 2.0 / ROBINS-I) + GRADE.

Implementa:
• RoB 2.0 para RCTs (5 dominios)
• ROBINS-I para estudios observacionales (7 dominios)
• Sistema GRADE para certeza de evidencia

Uso:
    from stats.risk_of_bias import RoB2Assessment, ROBINSIAssessment, GRADEAssessment
    rob = RoB2Assessment()
    rob.evaluate_domain("randomization", "low", "Sequence generation described")
    overall = rob.get_overall_judgment()
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class RoBDomain(str, Enum):
    """Dominios de RoB 2.0 para RCTs."""
    RANDOMIZATION = "randomization"
    DEVIATIONS = "deviations"
    MISSING_OUTCOME = "missing_outcome"
    OUTCOME_MEASUREMENT = "outcome_measurement"
    SELECTIVE_REPORTING = "selective_reporting"


class ROBINSDomain(str, Enum):
    """Dominios de ROBINS-I para estudios observacionales."""
    CONFUSING = "confounding"
    SELECTION = "selection"
    CLASSIFICATION = "classification"
    DEVIATIONS = "deviations"
    MISSING_DATA = "missing_data"
    MEASUREMENT = "measurement"
    REPORTING = "reporting"


class Judgment(str, Enum):
    """Juicios de riesgo de sesgo."""
    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"
    CRITICAL = "critical"
    NO_INFO = "no_information"


class GRADERating(str, Enum):
    """Niveles de certeza GRADE."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class DomainEvaluation:
    """Evaluación de un dominio específico."""
    domain: str
    judgment: Judgment
    notes: str = ""
    citations: str = ""


@dataclass
class StudyRoB:
    """Evaluación completa de RoB para un estudio."""
    pmid: str
    study_type: str  # "RCT" o "observational"
    domains: List[DomainEvaluation] = field(default_factory=list)
    overall: Optional[Judgment] = None
    
    def add_domain(self, domain: str, judgment: Judgment, notes: str = ""):
        self.domains.append(DomainEvaluation(domain, judgment, notes))
        self._calculate_overall()
    
    def _calculate_overall(self):
        """Calcula juicio global basado en dominios."""
        if not self.domains:
            self.overall = Judgment.NO_INFO
            return
            
        judgments = [d.judgment for d in self.domains]
        
        if any(j == Judgment.HIGH for j in judgments):
            self.overall = Judgment.HIGH
        elif any(j == Judgment.SOME_CONCERNS for j in judgments):
            self.overall = Judgment.SOME_CONCERNS
        elif all(j == Judgment.LOW for j in judgments):
            self.overall = Judgment.LOW
        else:
            self.overall = Judgment.NO_INFO


class RoB2Assessment:
    """
    Evaluación RoB 2.0 para ensayos clínicos aleatorizados.
    
    5 dominios:
    1. Proceso de aleatorización
    2. Desviaciones del protocolo previstas
    3. Datos de resultado faltantes
    4. Medición del resultado
    5. Selección de resultados reportados
    """
    
    DOMAINS = [
        RoBDomain.RANDOMIZATION,
        RoBDomain.DEVIATIONS,
        RoBDomain.MISSING_OUTCOME,
        RoBDomain.OUTCOME_MEASUREMENT,
        RoBDomain.SELECTIVE_REPORTING,
    ]
    
    def __init__(self):
        self.studies: Dict[str, StudyRoB] = {}
    
    def add_study(self, pmid: str) -> StudyRoB:
        """Agrega un nuevo estudio para evaluar."""
        study = StudyRoB(pmid=pmid, study_type="RCT")
        self.studies[pmid] = study
        return study
    
    def evaluate_study(self, pmid: str, domain: str, judgment: Judgment, 
                    notes: str = "") -> None:
        """Evalúa un dominio específico de un estudio."""
        if pmid not in self.studies:
            self.add_study(pmid)
        self.studies[pmid].add_domain(domain, judgment, notes)
    
    def get_traffic_light_summary(self) -> Dict:
        """
        Genera resumen de semáforo para visualización.
        
        Returns
        -------
        dict con conteos por juicio
        """
        summary = {
            "low": 0,
            "some_concerns": 0,
            "high": 0,
            "critical": 0,
            "no_information": 0,
        }
        
        for study in self.studies.values():
            for domain in study.domains:
                summary[domain.judgment.value] += 1
        
        return summary
    
    def export_visualization_data(self, output_dir: str = "rob_output") -> str:
        """Exporta datos para visualización de semáforo."""
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        
        # Datos para heatmap
        data = []
        for pmid, study in sorted(self.studies.items()):
            row = {"pmid": pmid}
            for domain in self.DOMAINS:
                # Buscar evaluación de este dominio
                eval_found = next(
                    (d for d in study.domains if d.domain == domain.value), 
                    None
                )
                row[domain.value] = eval_found.judgment.value if eval_found else "no_information"
            row["overall"] = study.overall.value if study.overall else "no_information"
            data.append(row)
        
        filepath = outdir / f"rob_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return str(filepath)


class ROBINSIAssessment:
    """
    Evaluación ROBINS-I para estudios observacionales.
    
    7 dominios:
    1. Confusión
    2. Selección de participantes
    3. Clasificación de intervenciones
    4. Desviaciones de intervenciones previstas
    5. Datos faltantes
    6. Medición de resultados
    7. Selección de resultados reportados
    """
    
    DOMAINS = [
        ROBINSDomain.CONFUSING,
        ROBINSDomain.SELECTION,
        ROBINSDomain.CLASSIFICATION,
        ROBINSDomain.DEVIATIONS,
        ROBINSDomain.MISSING_DATA,
        ROBINSDomain.MEASUREMENT,
        ROBINSDomain.REPORTING,
    ]
    
    def __init__(self):
        self.studies: Dict[str, StudyRoB] = {}
    
    def add_study(self, pmid: str) -> StudyRoB:
        study = StudyRoB(pmid=pmid, study_type="observational")
        self.studies[pmid] = study
        return study
    
    def evaluate_study(self, pmid: str, domain: str, judgment: Judgment, 
                    notes: str = "") -> None:
        if pmid not in self.studies:
            self.add_study(pmid)
        self.studies[pmid].add_domain(domain, judgment, notes)
    
    def get_risk_summary(self) -> Dict:
        """Resumen de nivel de riesgo global."""
        risk_levels = {
            "low": 0,
            "moderate": 0,
            "serious": 0,
            "critical": 0,
            "no_information": 0,
        }
        
        for study in self.studies.values():
            if study.overall:
                # Mapear juicios a niveles de riesgo
                mapping = {
                    Judgment.LOW: "low",
                    Judgment.SOME_CONCERNS: "moderate",
                    Judgment.HIGH: "serious",
                    Judgment.CRITICAL: "critical",
                    Judgment.NO_INFO: "no_information",
                }
                risk_levels[mapping.get(study.overall, "no_information")] += 1
        
        return risk_levels


class GRADEAssessment:
    """
    Sistema GRADE para evaluar certeza de evidencia.
    
    Comienza con certeza ALTA para RCTs o BAJA para observacionales,
    luego aplica factores de downgrade/upgrade.
    
    Factores de downgrade (-1 o -2 cada uno):
    • Riesgo de sesgo
    • Inconsistencia (I² > 50%, heterogeneidad)
    • Indirectitud (PICO diferente)
    • Imprecisión (intervalos amplios, pocos eventos)
    • Sesgo de publicación (funnel plot asimétrico, Egger p<0.10)
    
    Factores de upgrade (+1 o +2):
    • Magnitud grande del efecto
    • Dosis-respuesta
    • Confusión que reduciría el efecto
    """
    
    def __init__(self, study_design: str = "RCT"):
        self.study_design = study_design
        # Base: ALTA para RCT, BAJA para observacional
        self.base_rating = GRADERating.HIGH if study_design == "RCT" else GRADERating.LOW
        self.downgrades: List[str] = []
        self.upgrades: List[str] = []
        self.final_rating: Optional[GRADERating] = None
    
    def add_downgrade(self, factor: str, severity: int = 1, 
                     description: str = "") -> None:
        """Agrega factor de downgrade.
        
        Parameters
        ----------
        factor : str
            Tipo de factor ("risk_of_bias", "inconsistency", "indirectness", 
            "imprecision", "publication_bias")
        severity : int
            -1 o -2 niveles
        description : str
            Descripción del problema
        """
        self.downgrades.append({
            "factor": factor,
            "severity": severity,
            "description": description,
        })
    
    def add_upgrade(self, factor: str, magnitude: int = 1,
                   description: str = "") -> None:
        """Agrega factor de upgrade.
        
        Parameters
        ----------
        factor : str
            "large_effect", "dose_response", "residual_confounding"
        magnitude : int
            +1 o +2 niveles
        """
        self.upgrades.append({
            "factor": factor,
            "magnitude": magnitude,
            "description": description,
        })
    
    def calculate_rating(self) -> GRADERating:
        """Calcula rating GRADE final."""
        # Mapear a valores numéricos
        ratings_order = {
            GRADERating.HIGH: 4,
            GRADERating.MODERATE: 3,
            GRADERating.LOW: 2,
            GRADERating.VERY_LOW: 1,
        }
        
        base_value = ratings_order[self.base_rating]
        
        # Aplicar downgrades
        total_down = sum(d["severity"] for d in self.downgrades)
        total_up = sum(u["magnitude"] for u in self.upgrades)
        
        final_value = base_value - total_down + total_up
        final_value = max(1, min(4, final_value))  # Clamp a rango válido
        
        # Convertir de vuelta
        reverse_map = {v: k for k, v in ratings_order.items()}
        self.final_rating = reverse_map[final_value]
        
        return self.final_rating
    
    def get_summary(self) -> Dict:
        """Genera resumen completo de evaluación GRADE."""
        if self.final_rating is None:
            self.calculate_rating()
            
        return {
            "study_design": self.study_design,
            "base_rating": self.base_rating.value,
            "downgrades": self.downgrades,
            "upgrades": self.upgrades,
            "final_rating": self.final_rating.value if self.final_rating else None,
            "explanation": self._generate_explanation(),
        }
    
    def _generate_explanation(self) -> str:
        """Genera explicación textual de la calificación."""
        lines = [f"Diseño base: {self.study_design}",
                f"Certeza inicial: {self.base_rating.value}"]
        
        if self.downgrades:
            lines.append("\nFactores que reducen certeza:")
            for d in self.downgrades:
                lines.append(f"  - {d['factor']}: {d['description']} (-{d['severity']})")
        
        if self.upgrades:
            lines.append("\nFactores que aumentan certeza:")
            for u in self.upgrades:
                lines.append(f"  - {u['factor']}: {u['description']} (+{u['magnitude']})")
        
        lines.append(f"\nCerteza final: {self.final_rating.value}")
        
        return "\n".join(lines)
    
    def export_summary(self, output_dir: str = "grade_output") -> str:
        """Exporta resumen GRADE."""
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        
        summary = self.get_summary()
        filepath = outdir / f"grade_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return str(filepath)


# ── test / demo ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== RoB 2.0 Demo ===")
    rob = RoB2Assessment()
    
    # Evaluar 3 RCTs
    studies_rob = [
        ("PMID1", [
            ("randomization", Judgment.LOW, "Secuencia generada por computadora"),
            ("deviations", Judgment.LOW, "Sin desviaciones importantes"),
            ("missing_outcome", Judgment.SOME_CONCERNS, "5% datos faltantes"),
            ("outcome_measurement", Judgment.LOW, "Evaluadores cegados"),
            ("selective_reporting", Judgment.LOW, "Protocolo registrado"),
        ]),
        ("PMID2", [
            ("randomization", Judgment.LOW, "Aleatorización adecuada"),
            ("deviations", Judgment.HIGH, "Crossover significativo"),
            ("missing_outcome", Judgment.HIGH, "20% dropout"),
            ("outcome_measurement", Judgment.LOW, "Cegamiento adecuado"),
            ("selective_reporting", Judgment.SOME_CONCERNS, "No pre-registrado"),
        ]),
    ]
    
    for pmid, evaluations in studies_rob:
        for domain, judgment, notes in evaluations:
            rob.evaluate_study(pmid, domain, judgment, notes)
        overall = rob.studies[pmid].overall
        print(f"{pmid}: Overall = {overall.value}")
    
    traffic = rob.get_traffic_light_summary()
    print(f"\nResumen semáforo: {traffic}")
    
    print("\n=== GRADE Demo ===")
    grade = GRADEAssessment("RCT")
    
    # Aplicar factores de downgrade
    grade.add_downgrade("risk_of_bias", 1, "Algunos estudios con alto riesgo")
    grade.add_downgrade("inconsistency", 1, "I² = 43%, heterogeneidad moderada")
    grade.add_downgrade("imprecision", 1, "Intervalo amplio, cruza nulo")
    
    rating = grade.calculate_rating()
    print(f"Certeza GRADE final: {rating.value}")
    print(f"\n{grade._generate_explanation()}")
