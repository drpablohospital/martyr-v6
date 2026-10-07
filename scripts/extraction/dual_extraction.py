#!/usr/bin/env python3
"""
dual_extraction.py — Extracción doble de datos con ICC (Intraclass Correlation Coefficient).

Implementa extracción de datos por dos investigadores independientes,
cálculo de ICC para concordancia, y resolución de discrepancias.

Uso:
    from extraction.dual_extraction import DualExtraction, ExtractedData
    de = DualExtraction(investigator1="Alice", investigator2="Bob")
    de.add_extraction("PMID1", "Alice", ExtractedData(n_intervention=100, n_control=100, ...))
    de.add_extraction("PMID1", "Bob", ExtractedData(n_intervention=100, n_control=100, ...))
    icc = de.calculate_icc()
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class ExtractedData:
    """Datos extraídos de un estudio."""
    # Datos básicos
    n_intervention: Optional[int] = None
    n_control: Optional[int] = None
    events_intervention: Optional[int] = None
    events_control: Optional[int] = None
    mean_intervention: Optional[float] = None
    mean_control: Optional[float] = None
    sd_intervention: Optional[float] = None
    sd_control: Optional[float] = None
    
    # Efectos reportados
    reported_effect: Optional[float] = None
    reported_ci_lower: Optional[float] = None
    reported_ci_upper: Optional[float] = None
    reported_se: Optional[float] = None
    p_value: Optional[float] = None
    
    # Características del estudio
    study_design: str = ""  # "RCT", "cohort", "case-control"
    follow_up_months: Optional[float] = None
    
    # Campos extra (cualquier otro dato)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Resultado consolidado de extracción de un estudio."""
    pmid: str
    investigator1: str
    investigator2: str
    data1: Optional[ExtractedData] = None
    data2: Optional[ExtractedData] = None
    final_data: Optional[ExtractedData] = None
    discrepancies: List[str] = field(default_factory=list)
    resolved: bool = False
    resolver: str = ""


class DualExtraction:
    """
    Gestiona extracción doble con cálculo de ICC.
    
    Flujo:
    1. Dos investigadores extraen datos independientemente
    2. Se calcula ICC para campos numéricos
    3. Se identifican discrepancias
    4. Se resuelven con consenso o tercer evaluador
    """
    
    def __init__(self, investigator1: str, investigator2: str,
                 output_dir: str = "extraction_output"):
        self.investigator1 = investigator1
        self.investigator2 = investigator2
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._extractions: Dict[str, Dict[str, ExtractedData]] = {}
        
    def add_extraction(self, pmid: str, investigator: str, 
                      data: ExtractedData) -> None:
        """Agrega datos extraídos por un investigador."""
        if investigator not in (self.investigator1, self.investigator2):
            raise ValueError(f"Investigador '{investigator}' no registrado")
            
        if pmid not in self._extractions:
            self._extractions[pmid] = {}
        self._extractions[pmid][investigator] = data
        
    def _get_numeric_fields(self, data: ExtractedData) -> Dict[str, float]:
        """Extrae campos numéricos de ExtractedData."""
        numeric = {}
        for field_name in ['n_intervention', 'n_control', 'events_intervention', 
                          'events_control', 'mean_intervention', 'mean_control',
                          'sd_intervention', 'sd_control', 'reported_effect',
                          'reported_ci_lower', 'reported_ci_upper', 'reported_se',
                          'p_value', 'follow_up_months']:
            value = getattr(data, field_name)
            if value is not None:
                numeric[field_name] = float(value)
        return numeric
    
    def calculate_icc(self, field: Optional[str] = None) -> Dict[str, Any]:
        """
        Calcula ICC (Intraclass Correlation Coefficient) usando ANOVA de un factor.
        
        ICC(2,1): Two-way random, single measure
        - Modelo de efectos aleatorios (ambos evaluadores son muestra de población)
        - Single measure (usamos una medición por sujeto)
        
        Parameters
        ----------
        field : str | None
            Campo específico para calcular ICC. Si None, calcula para todos.
            
        Returns
        -------
        dict con ICC, IC 95%, interpretación
        """
        # Preparar datos: solo estudios evaluados por ambos
        valid_studies = []
        for pmid, extractions in self._extractions.items():
            if self.investigator1 in extractions and self.investigator2 in extractions:
                valid_studies.append(pmid)
        
        if len(valid_studies) < 2:
            return {"error": "Se requieren al menos 2 estudios evaluados por ambos"}
        
        results = {}
        
        # Campos a evaluar
        fields_to_check = [field] if field else [
            'n_intervention', 'n_control', 'events_intervention', 'events_control',
            'mean_intervention', 'mean_control', 'sd_intervention', 'sd_control',
            'reported_effect', 'follow_up_months'
        ]
        
        for f in fields_to_check:
            # Recolectar pares de valores
            values1 = []  # Investigador 1
            values2 = []  # Investigador 2
            
            for pmid in valid_studies:
                data1 = self._extractions[pmid][self.investigator1]
                data2 = self._extractions[pmid][self.investigator2]
                
                v1 = getattr(data1, f)
                v2 = getattr(data2, f)
                
                if v1 is not None and v2 is not None:
                    values1.append(float(v1))
                    values2.append(float(v2))
            
            if len(values1) < 2:
                continue
                
            # Calcular ICC usando ANOVA simplificada
            # Modelo: MSB = entre sujetos, MSW = dentro de sujetos (entre evaluadores)
            n = len(values1)
            
            # Media general
            all_values = values1 + values2
            grand_mean = sum(all_values) / len(all_values)
            
            # Media por sujeto (estudio)
            subject_means = [(v1 + v2) / 2 for v1, v2 in zip(values1, values2)]
            
            # Suma de cuadrados entre sujetos (MSB)
            ss_between = sum((sm - grand_mean) ** 2 for sm in subject_means) * 2
            df_between = n - 1
            ms_between = ss_between / df_between
            
            # Suma de cuadrados dentro de sujetos (MSW)
            ss_within = sum((v1 - sm) ** 2 + (v2 - sm) ** 2 
                          for v1, v2, sm in zip(values1, values2, subject_means))
            df_within = n
            ms_within = ss_within / df_within
            
            # ICC(2,1)
            if ms_between + ms_within == 0:
                icc_value = 1.0
            else:
                icc_value = (ms_between - ms_within) / (ms_between + ms_within)
            
            # IC 95% aproximado (simplificado)
            se_icc = math.sqrt(2 * (1 - icc_value) ** 2 / ((n - 1) * (1 + icc_value) ** 2)) if n > 2 else 0.5
            ci_lower = max(-1, icc_value - 1.96 * se_icc)
            ci_upper = min(1, icc_value + 1.96 * se_icc)
            
            # Interpretación (Koo & Li 2016)
            if icc_value < 0.50:
                interpretation = "Poor (<0.50)"
            elif icc_value < 0.75:
                interpretation = "Moderate (0.50-0.75)"
            elif icc_value < 0.90:
                interpretation = "Good (0.75-0.90)"
            else:
                interpretation = "Excellent (≥0.90)"
            
            results[f] = {
                "icc": round(icc_value, 4),
                "ci_95": [round(ci_lower, 4), round(ci_upper, 4)],
                "n_pairs": len(values1),
                "interpretation": interpretation,
                "acceptable": icc_value >= 0.75  # Umbral para confiabilidad aceptable
            }
        
        return results
    
    def find_discrepancies(self, threshold_pct: float = 10.0) -> List[ExtractionResult]:
        """
        Identifica discrepancias entre extractores.
        
        Parameters
        ----------
        threshold_pct : float
            Umbral de diferencia porcentual para considerar discrepancia
            (e.g., 10% = valores que difieren en más de 10%)
        """
        discrepancies = []
        
        for pmid, extractions in self._extractions.items():
            if self.investigator1 not in extractions or self.investigator2 not in extractions:
                continue
                
            data1 = extractions[self.investigator1]
            data2 = extractions[self.investigator2]
            
            result = ExtractionResult(
                pmid=pmid,
                investigator1=self.investigator1,
                investigator2=self.investigator2,
                data1=data1,
                data2=data2
            )
            
            # Comparar campos numéricos
            numeric1 = self._get_numeric_fields(data1)
            numeric2 = self._get_numeric_fields(data2)
            
            all_fields = set(numeric1.keys()) | set(numeric2.keys())
            
            for field in all_fields:
                v1 = numeric1.get(field)
                v2 = numeric2.get(field)
                
                if v1 is None or v2 is None:
                    if v1 is not None or v2 is not None:
                        result.discrepancies.append(f"{field}: falta en un extractor")
                    continue
                
                # Calcular diferencia porcentual
                if v1 == 0 and v2 == 0:
                    diff_pct = 0
                elif v1 == 0 or v2 == 0:
                    diff_pct = 100
                else:
                    diff_pct = abs(v1 - v2) / ((v1 + v2) / 2) * 100
                
                if diff_pct > threshold_pct:
                    result.discrepancies.append(
                        f"{field}: {v1:.2f} vs {v2:.2f} ({diff_pct:.1f}% diff)"
                    )
            
            if result.discrepancies:
                discrepancies.append(result)
        
        return discrepancies
    
    def resolve_extraction(self, pmid: str, final_data: ExtractedData,
                          resolver: str = "consensus") -> None:
        """Resuelve discrepancias con datos finales consensuados."""
        if pmid not in self._extractions:
            raise ValueError(f"PMID {pmid} no encontrado")
        
        # Marcar como resuelto
        for result in self.find_discrepancies():
            if result.pmid == pmid:
                result.final_data = final_data
                result.resolved = True
                result.resolver = resolver
                
    def export_extractions(self) -> str:
        """Exporta todas las extracciones a CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"extractions_{timestamp}.csv"
        
        # Preparar headers
        base_fields = [
            'pmid', 'investigator', 'n_intervention', 'n_control',
            'events_intervention', 'events_control',
            'mean_intervention', 'mean_control',
            'sd_intervention', 'sd_control',
            'reported_effect', 'reported_ci_lower', 'reported_ci_upper',
            'p_value', 'study_design', 'follow_up_months'
        ]
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=base_fields)
            writer.writeheader()
            
            for pmid, extractions in sorted(self._extractions.items()):
                for investigator, data in extractions.items():
                    row = {'pmid': pmid, 'investigator': investigator}
                    for field in base_fields[2:]:
                        value = getattr(data, field)
                        row[field] = value if value is not None else ''
                    writer.writerow(row)
        
        return str(filepath)
    
    def export_summary(self) -> Tuple[Dict, str]:
        """Genera resumen de extracción con ICC."""
        icc_results = self.calculate_icc()
        discrepancies = self.find_discrepancies()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "investigators": [self.investigator1, self.investigator2],
            "total_studies": len(self._extractions),
            "studies_with_both": sum(1 for e in self._extractions.values() 
                                    if len(e) == 2),
            "icc": icc_results,
            "discrepancies_found": len(discrepancies),
            "fields_evaluated": list(icc_results.keys()) if isinstance(icc_results, dict) else [],
        }
        
        filepath = self.output_dir / f"extraction_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary, str(filepath)


# ── test / demo ────────────────────────────────────────────────
if __name__ == "__main__":
    de = DualExtraction("Alice", "Bob")
    
    # Simular extracción de 5 estudios
    extractions = [
        # PMID, investigador, datos
        ("PMID1", "Alice", ExtractedData(
            n_intervention=100, n_control=100, events_intervention=20, events_control=25,
            reported_effect=0.80, reported_ci_lower=0.50, reported_ci_upper=1.20,
            study_design="RCT", follow_up_months=12
        )),
        ("PMID1", "Bob", ExtractedData(
            n_intervention=100, n_control=100, events_intervention=21, events_control=24,
            reported_effect=0.82, reported_ci_lower=0.52, reported_ci_upper=1.22,
            study_design="RCT", follow_up_months=12
        )),
        ("PMID2", "Alice", ExtractedData(
            n_intervention=200, n_control=200, events_intervention=45, events_control=50,
            reported_effect=0.90, reported_ci_lower=0.70, reported_ci_upper=1.15,
            study_design="RCT", follow_up_months=6
        )),
        ("PMID2", "Bob", ExtractedData(
            n_intervention=200, n_control=200, events_intervention=44, events_control=51,
            reported_effect=0.89, reported_ci_lower=0.69, reported_ci_upper=1.14,
            study_design="RCT", follow_up_months=6
        )),
        ("PMID3", "Alice", ExtractedData(
            n_intervention=150, n_control=150, events_intervention=30, events_control=35,
            reported_effect=0.85, reported_ci_lower=0.60, reported_ci_upper=1.10,
            study_design="cohort", follow_up_months=24
        )),
        ("PMID3", "Bob", ExtractedData(
            n_intervention=150, n_control=150, events_intervention=32, events_control=36,
            reported_effect=0.88, reported_ci_lower=0.63, reported_ci_upper=1.13,
            study_design="cohort", follow_up_months=24
        )),
    ]
    
    for pmid, inv, data in extractions:
        de.add_extraction(pmid, inv, data)
    
    # Calcular ICC
    icc = de.calculate_icc()
    print("ICC por campo:")
    for field, result in icc.items():
        if "error" in result:
            print(f"  {field}: {result['error']}")
        else:
            print(f"  {field}: ICC={result['icc']}, {result['interpretation']}")
    
    # Encontrar discrepancias
    discrepancies = de.find_discrepancies(threshold_pct=10)
    print(f"\nDiscrepancias encontradas: {len(discrepancies)}")
    for d in discrepancies:
        print(f"  {d.pmid}: {d.discrepancies}")
    
    # Exportar resumen
    summary, path = de.export_summary()
    print(f"\nResumen exportado a: {path}")
    print(json.dumps(summary, indent=2))
