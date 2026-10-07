#!/usr/bin/env python3
"""
Martyr v5.0 — Sistema de 7 Gates Obligatorios
==============================================
Implementa el protocolo de verificación con checkpoints reales.
Cada gate bloquea el pipeline hasta recibir aprobación explícita.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# Directorio base
BASE_DIR = Path(__file__).parent.parent
DECISIONS_DIR = BASE_DIR / "decisions"
SIGNOFFS_DIR = BASE_DIR / "signoffs"
ARTEFACTS_DIR = BASE_DIR / "artefacts"


# ── definición de gates ───────────────────────────────────────
@dataclass
class Gate:
    """Definición de un gate de verificación."""
    number: int
    name: str
    description: str
    artefact_type: str
    blockers: List[str]  # Qué fallos bloquean el gate
    is_mandatory: bool = True


GATES: List[Gate] = [
    Gate(1, "Congelamiento de la Estrategia de Búsqueda",
         "PICO/PECO + términos MeSH + operadores booleanos + bases de datos",
         "strategy.md", ["PICO no aprobado", "Términos no congelados"]),
    Gate(2, "Consistencia del Cribado",
         "Screening por título/abstract + κ de Cohen + discrepancias",
         "screening.csv", ["κ < 0.60", "Conflictos sin resolver"]),
    Gate(3, "Calibración de Extracción",
         "3 estudios piloto extraídos + formato confirmado",
         "pilot_extraction.csv", ["Formato no aprobado", "Criterios incorrectos"]),
    Gate(4, "Verificación Numérica",
         "Matriz de datos consolidada + script + parámetros",
         "data_matrix.csv", ["Números no verificados", "Unidades inconsistentes"]),
    Gate(5, "Modelo y Heterogeneidad",
         "Efecto agrupado + IC + I² + τ² + forest plot",
         "model_results.json", ["I² > 90% sin plan", "Modelo no defendible"]),
    Gate(6, "Sesgo de Publicación y Certeza",
         "Funnel plot + Egger + trim-fill + GRADE",
         "bias_assessment.md", ["Egger p<0.10 sin corrección", "GRADE no validado"]),
    Gate(7, "Cierre e Interpretación",
         "Manuscrito completo PRISMA 2020 + 27 ítems + limitaciones",
         "manuscript.md", ["PRISMA incompleto", "Citas sin verificar"]),
]


# ── reportero de gates ────────────────────────────────────────
class GateReporter:
    """Genera reportes de gates y solicita aprobación."""
    
    def __init__(self):
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Crea directorios necesarios."""
        for d in [DECISIONS_DIR, SIGNOFFS_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        for g in GATES:
            (ARTEFACTS_DIR / f"gate_{g.number}").mkdir(parents=True, exist_ok=True)
    
    def report_gate(self, gate_num: int, estado: str, artefacto: str,
                    hallazgos: List[str], accion: str) -> str:
        """Genera el formato obligatorio de reporte de gate.
        
        Returns
        -------
        str : Reporte formateado listo para mostrar al usuario
        """
        gate = next((g for g in GATES if g.number == gate_num), None)
        if gate is None:
            raise ValueError(f"Gate {gate_num} no existe")
        
        lines = [
            "",
            "━" * 60,
            f"━━━ GATE {gate.number}: {gate.name.upper()} ━━━",
            "━" * 60,
            f"Estado: {estado}",
            f"Artefacto: {artefacto}",
            "",
            "Hallazgos clave:",
        ]
        for h in hallazgos:
            lines.append(f"  • {h}")
        lines.extend([
            "",
            f"⚠️  Acción requerida: {accion}",
            "",
            "¿Apruebas y continúo? (sí / no / ajustar)",
            "",
        ])
        
        return "\n".join(lines)
    
    def save_decision(self, gate_num: int, approved: bool, notes: str = "",
                      user: str = "user") -> Path:
        """Guarda la decisión del gate en archivo markdown.
        
        Parameters
        ----------
        gate_num : int
        approved : bool
            True = aprobado, False = rechazado
        notes : str
            Notas adicionales
        user : str
            Quién firmó
        
        Returns
        -------
        Path : Ruta al archivo de decisión
        """
        gate = next((g for g in GATES if g.number == gate_num), None)
        if gate is None:
            raise ValueError(f"Gate {gate_num} no existe")
        
        timestamp = datetime.now().isoformat()
        status = "APROBADO" if approved else "RECHAZADO"
        
        content = f"""---
gate: {gate.number}
name: "{gate.name}"
timestamp: "{timestamp}"
approved: {str(approved).lower()}
user: "{user}"
---

# GATE {gate.number}: {gate.name}

**Estado:** {status}
**Timestamp:** {timestamp}
**Usuario:** {user}

## Notas

{notes if notes else "_Sin notas adicionales_"}

## Registro de Bloqueos

{chr(10).join(f"- [ ] {b}" for b in gate.blockers)}

---

*Este archivo es obligatorio. Sin él, el pipeline no puede continuar.*
"""
        
        path = DECISIONS_DIR / f"gate_{gate.number:02d}_{gate.name.lower().replace(' ', '_')}.md"
        path.write_text(content, encoding="utf-8")
        
        # Guardar signoff separado
        if approved:
            sig_path = SIGNOFFS_DIR / f"gate_{gate.number:02d}.sig"
            sig_path.write_text(f"{timestamp}\n{user}\nAPPROVED\n", encoding="utf-8")
        
        return path
    
    def check_gate_status(self, gate_num: int) -> Dict:
        """Verifica si un gate tiene signoff.
        
        Returns
        -------
        dict con 'approved', 'path', 'timestamp'
        """
        sig_path = SIGNOFFS_DIR / f"gate_{gate_num:02d}.sig"
        if not sig_path.exists():
            return {"approved": False, "path": None, "timestamp": None}
        
        lines = sig_path.read_text(encoding="utf-8").strip().split("\n")
        return {
            "approved": len(lines) >= 3 and lines[2] == "APPROVED",
            "path": str(sig_path),
            "timestamp": lines[0] if lines else None,
        }
    
    def check_all_gates(self) -> List[Dict]:
        """Verifica estado de todos los gates.
        
        Returns
        -------
        list de dicts con número, nombre, aprobado
        """
        return [
            {
                "number": g.number,
                "name": g.name,
                **self.check_gate_status(g.number),
            }
            for g in GATES
        ]
    
    def get_pending_gates(self) -> List[Gate]:
        """Devuelve gates que aún no tienen aprobación."""
        return [g for g in GATES if not self.check_gate_status(g.number)["approved"]]


# ── preflight validator ───────────────────────────────────────
class PreflightValidator:
    """Valida que todos los gates previos estén aprobados antes de continuar."""
    
    def __init__(self):
        self.reporter = GateReporter()
    
    def validate(self, current_gate: int) -> bool:
        """Valida que todos los gates anteriores estén aprobados.
        
        Parameters
        ----------
        current_gate : int
            Gate que se intenta ejecutar
        
        Returns
        -------
        bool : True si puede continuar, False si está bloqueado
        """
        pending = []
        for g in GATES:
            if g.number >= current_gate:
                break
            status = self.reporter.check_gate_status(g.number)
            if not status["approved"]:
                pending.append(g)
        
        if pending:
            print(f"❌ BLOQUEADO: Gate {current_gate} no puede ejecutarse.")
            print(f"   Gates pendientes: {', '.join(f'G{p.number}' for p in pending)}")
            print(f"   Ejecuta gate_reporter.py para completar los gates pendientes.")
            return False
        
        return True
    
    def require_approval(self, gate_num: int) -> None:
        """Fuerza aprobación del gate o termina el programa.
        
        Uso: llamar al inicio de cada fase del pipeline.
        """
        status = self.reporter.check_gate_status(gate_num)
        if not status["approved"]:
            print(f"\n❌ GATE {gate_num}: Sin aprobación.")
            print("   El pipeline está bloqueado.")
            print("   Usa GateReporter.report_gate() para generar el reporte")
            print("   y GateReporter.save_decision() para guardar la aprobación.")
            sys.exit(1)


# ── funciones de conveniencia ────────────────────────────────
def report_gate(gate_num: int, estado: str, artefacto: str,
                hallazgos: List[str], accion: str) -> str:
    """Genera reporte de gate (función de conveniencia)."""
    reporter = GateReporter()
    return reporter.report_gate(gate_num, estado, artefacto, hallazgos, accion)


def approve_gate(gate_num: int, notes: str = "", user: str = "user") -> Path:
    """Aprueba un gate (función de conveniencia)."""
    reporter = GateReporter()
    return reporter.save_decision(gate_num, True, notes, user)


def reject_gate(gate_num: int, notes: str = "", user: str = "user") -> Path:
    """Rechaza un gate (función de conveniencia)."""
    reporter = GateReporter()
    return reporter.save_decision(gate_num, False, notes, user)


# ── demo ──────────────────────────────────────────────────────
if __name__ == "__main__":
    reporter = GateReporter()
    
    # Demo: Gate 1 - Estrategia de búsqueda
    report = reporter.report_gate(
        gate_num=1,
        estado="PICO definido, términos MeSH seleccionados, bases: PubMed + Cochrane + S2",
        artefacto="decisions/gate_01_search_strategy.md",
        hallazgos=[
            "P: Pacientes ICU con AKI KDIGO stage 3",
            "I: RRT temprana (dentro de 12h de KDIGO 3)",
            "C: RRT tardía (estándar de cuidado o complicaciones)",
            "O: Mortalidad a 90 días",
            "Términos: 'acute kidney injury', 'renal replacement therapy', 'timing'",
            "Bases: PubMed, Cochrane Library, ClinicalTrials.gov, Semantic Scholar",
        ],
        accion="Revisar PICO y confirmar que los términos capturan todos los RCTs seminales (AKIKI, ELAIN, STARRT-AKI, IDEAL-ICU)",
    )
    print(report)
    
    # Simular aprobación
    path = reporter.save_decision(1, True, "PICO validado contra estudios seminales", "Dr_Pablo")
    print(f"\n✅ Gate 1 aprobado y guardado en: {path}")
    
    # Verificar estado
    all_gates = reporter.check_all_gates()
    print("\nEstado de todos los gates:")
    for g in all_gates:
        status = "✅" if g["approved"] else "⏳"
        print(f"  {status} Gate {g['number']}: {g['name']}")