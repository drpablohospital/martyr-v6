#!/usr/bin/env python3
"""
dual_screening.py — Screening doble ciego con κ de Cohen.

Implementa el proceso de screening de estudios por título y abstract
con dos investigadores independientes, cálculo de concordancia (κ),
y resolución de conflictos.

Uso:
    from screening.dual_screening import DualScreening, ScreeningDecision
    ds = DualScreening(investigator1="Alice", investigator2="Bob")
    ds.add_screening("PMID123", "Alice", ScreeningDecision.INCLUDE)
    ds.add_screening("PMID123", "Bob", ScreeningDecision.INCLUDE)
    kappa = ds.calculate_kappa()
    conflicts = ds.get_conflicts()
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ScreeningDecision(str, Enum):
    """Decisiones posibles de screening."""
    INCLUDE = "include"      # Incluir
    EXCLUDE = "exclude"      # Excluir
    MAYBE = "maybe"          # Revisar (conflicto potencial)


@dataclass
class ScreeningRecord:
    """Registro de screening de un estudio por un investigador."""
    pmid: str
    investigator: str
    decision: ScreeningDecision
    reason: str = ""          # Razón de exclusión
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass  
class ScreeningResult:
    """Resultado consolidado de un estudio."""
    pmid: str
    title: str = ""
    abstract: str = ""
    final_decision: Optional[ScreeningDecision] = None
    investigators: List[str] = field(default_factory=list)
    decisions: Dict[str, ScreeningDecision] = field(default_factory=dict)
    is_conflict: bool = False
    resolved_by: Optional[str] = None
    resolution_note: str = ""


class DualScreening:
    """
    Gestiona el screening doble ciego con κ de Cohen.
    
    Flujo:
    1. Cada investigador screenea independientemente
    2. Se calcula κ de Cohen entre ambos
    3. Se identifican conflictos (discrepancias)
    4. Se resuelven conflictos con un tercer evaluador o consenso
    """
    
    def __init__(self, investigator1: str, investigator2: str, 
                 output_dir: str = "screening_output"):
        self.investigator1 = investigator1
        self.investigator2 = investigator2
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Almacenar todos los screenings
        self._screenings: List[ScreeningRecord] = []
        self._results: Dict[str, ScreeningResult] = {}
        
    def add_screening(self, pmid: str, investigator: str, 
                     decision: ScreeningDecision, reason: str = "") -> None:
        """Agrega una decisión de screening."""
        if investigator not in (self.investigator1, self.investigator2):
            raise ValueError(f"Investigador '{investigator}' no registrado")
            
        record = ScreeningRecord(
            pmid=pmid,
            investigator=investigator,
            decision=decision,
            reason=reason
        )
        self._screenings.append(record)
        
        # Actualizar resultado consolidado
        if pmid not in self._results:
            self._results[pmid] = ScreeningResult(pmid=pmid)
        self._results[pmid].investigators.append(investigator)
        self._results[pmid].decisions[investigator] = decision
        
    def calculate_kappa(self) -> Dict[str, float]:
        """
        Calcula κ de Cohen entre los dos investigadores.
        
        Returns
        -------
        dict con kappa, acuerdo observado, acuerdo esperado,
        interpretación (Landis & Koch 1977)
        """
        # Construir matriz de confusión 2x2 (include vs exclude)
        # Ignorar "maybe" para κ (se consideran conflictos)
        both_include = 0
        both_exclude = 0
        i1_include_i2_exclude = 0
        i1_exclude_i2_include = 0
        maybes = 0
        
        for pmid, result in self._results.items():
            if len(result.decisions) != 2:
                continue  # Solo estudios evaluados por ambos
                
            d1 = result.decisions[self.investigator1]
            d2 = result.decisions[self.investigator2]
            
            if d1 == ScreeningDecision.MAYBE or d2 == ScreeningDecision.MAYBE:
                maybes += 1
                continue
                
            if d1 == ScreeningDecision.INCLUDE and d2 == ScreeningDecision.INCLUDE:
                both_include += 1
            elif d1 == ScreeningDecision.EXCLUDE and d2 == ScreeningDecision.EXCLUDE:
                both_exclude += 1
            elif d1 == ScreeningDecision.INCLUDE and d2 == ScreeningDecision.EXCLUDE:
                i1_include_i2_exclude += 1
            else:
                i1_exclude_i2_include += 1
        
        total = both_include + both_exclude + i1_include_i2_exclude + i1_exclude_i2_include
        
        if total == 0:
            return {"kappa": None, "error": "No hay estudios evaluados por ambos"}
        
        # Acuerdo observado (Po)
        po = (both_include + both_exclude) / total
        
        # Probabilidades marginales
        p_i1_include = (both_include + i1_include_i2_exclude) / total
        p_i1_exclude = (both_exclude + i1_exclude_i2_include) / total
        p_i2_include = (both_include + i1_exclude_i2_include) / total
        p_i2_exclude = (both_exclude + i1_include_i2_exclude) / total
        
        # Acuerdo esperado (Pe)
        pe = (p_i1_include * p_i2_include) + (p_i1_exclude * p_i2_exclude)
        
        if pe == 1:
            kappa = 1.0 if po == 1 else 0.0
        else:
            kappa = (po - pe) / (1 - pe)
        
        # Interpretación Landis & Koch (1977)
        if kappa < 0:
            interpretation = "Poor (<0)"
        elif kappa < 0.20:
            interpretation = "Slight (0.00-0.20)"
        elif kappa < 0.40:
            interpretation = "Fair (0.21-0.40)"
        elif kappa < 0.60:
            interpretation = "Moderate (0.41-0.60)"
        elif kappa < 0.80:
            interpretation = "Substantial (0.61-0.80)"
        else:
            interpretation = "Almost perfect (0.81-1.00)"
            
        return {
            "kappa": round(kappa, 4),
            "observed_agreement": round(po, 4),
            "expected_agreement": round(pe, 4),
            "total_evaluated": total,
            "both_include": both_include,
            "both_exclude": both_exclude,
            "conflict_include_exclude": i1_include_i2_exclude + i1_exclude_i2_include,
            "maybes": maybes,
            "interpretation": interpretation,
            "acceptable": kappa >= 0.60  # Umbral mínimo PRISMA
        }
    
    def get_conflicts(self) -> List[ScreeningResult]:
        """Devuelve estudios con conflictos entre investigadores."""
        conflicts = []
        for pmid, result in self._results.items():
            if len(result.decisions) == 2:
                d1 = result.decisions[self.investigator1]
                d2 = result.decisions[self.investigator2]
                if d1 != d2:
                    result.is_conflict = True
                    conflicts.append(result)
        return conflicts
    
    def resolve_conflict(self, pmid: str, resolver: str, 
                        decision: ScreeningDecision, note: str = "") -> None:
        """Resuelve un conflicto con decisión de un tercer evaluador/consenso."""
        if pmid not in self._results:
            raise ValueError(f"PMID {pmid} no encontrado")
        self._results[pmid].final_decision = decision
        self._results[pmid].resolved_by = resolver
        self._results[pmid].resolution_note = note
        self._results[pmid].is_conflict = False
        
    def export_screening_report(self) -> str:
        """Genera reporte CSV del screening."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"screening_report_{timestamp}.csv"
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'PMID', 'Title', 'Investigator1', 'Decision1', 
                'Investigator2', 'Decision2', 'Conflict', 
                'Final_Decision', 'Resolved_By', 'Note'
            ])
            
            for pmid, result in sorted(self._results.items()):
                d1 = result.decisions.get(self.investigator1, '')
                d2 = result.decisions.get(self.investigator2, '')
                writer.writerow([
                    pmid,
                    result.title,
                    self.investigator1,
                    d1.value if d1 else '',
                    self.investigator2,
                    d2.value if d2 else '',
                    'YES' if result.is_conflict else 'NO',
                    result.final_decision.value if result.final_decision else '',
                    result.resolved_by or '',
                    result.resolution_note
                ])
                
        return str(filepath)
    
    def export_summary(self) -> Dict:
        """Genera resumen JSON del proceso de screening."""
        kappa_results = self.calculate_kappa()
        conflicts = self.get_conflicts()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "investigators": [self.investigator1, self.investigator2],
            "total_studies": len(self._results),
            "kappa": kappa_results,
            "conflicts": len(conflicts),
            "resolved": sum(1 for c in conflicts if c.final_decision is not None),
            "pending": sum(1 for c in conflicts if c.final_decision is None),
        }
        
        # Contar finales
        included = sum(1 for r in self._results.values() 
                      if r.final_decision == ScreeningDecision.INCLUDE)
        excluded = sum(1 for r in self._results.values()
                      if r.final_decision == ScreeningDecision.EXCLUDE)
        summary["final_included"] = included
        summary["final_excluded"] = excluded
        
        filepath = self.output_dir / f"screening_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary, str(filepath)


# ── test / demo ────────────────────────────────────────────────
if __name__ == "__main__":
    ds = DualScreening("Alice", "Bob")
    
    # Simular screening de 10 estudios
    test_data = [
        ("PMID1", "Alice", ScreeningDecision.INCLUDE, "Bob", ScreeningDecision.INCLUDE),
        ("PMID2", "Alice", ScreeningDecision.INCLUDE, "Bob", ScreeningDecision.EXCLUDE),
        ("PMID3", "Alice", ScreeningDecision.EXCLUDE, "Bob", ScreeningDecision.EXCLUDE),
        ("PMID4", "Alice", ScreeningDecision.INCLUDE, "Bob", ScreeningDecision.INCLUDE),
        ("PMID5", "Alice", ScreeningDecision.EXCLUDE, "Bob", ScreeningDecision.EXCLUDE),
        ("PMID6", "Alice", ScreeningDecision.INCLUDE, "Bob", ScreeningDecision.INCLUDE),
        ("PMID7", "Alice", ScreeningDecision.EXCLUDE, "Bob", ScreeningDecision.INCLUDE),
        ("PMID8", "Alice", ScreeningDecision.INCLUDE, "Bob", ScreeningDecision.INCLUDE),
        ("PMID9", "Alice", ScreeningDecision.EXCLUDE, "Bob", ScreeningDecision.EXCLUDE),
        ("PMID10", "Alice", ScreeningDecision.INCLUDE, "Bob", ScreeningDecision.INCLUDE),
    ]
    
    for pmid, inv1, dec1, inv2, dec2 in test_data:
        ds.add_screening(pmid, inv1, dec1)
        ds.add_screening(pmid, inv2, dec2)
    
    kappa = ds.calculate_kappa()
    print(f"κ de Cohen: {kappa['kappa']}")
    print(f"Interpretación: {kappa['interpretation']}")
    print(f"Aceptable (≥0.60): {kappa['acceptable']}")
    
    conflicts = ds.get_conflicts()
    print(f"Conflictos: {len(conflicts)}")
    
    # Resolver conflictos
    for c in conflicts:
        ds.resolve_conflict(c.pmid, "Charlie (arbitrator)", 
                           ScreeningDecision.INCLUDE, "Consensus discussion")
    
    summary, path = ds.export_summary()
    print(f"\nResumen exportado a: {path}")
    print(json.dumps(summary, indent=2))
