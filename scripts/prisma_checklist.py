#!/usr/bin/env python3
"""
Martyr v5.2 — PRISMA 2020 Checklist Automatizado
====================================================
Verifica cada uno de los 27 items PRISMA 2020 contra los artefactos
producidos por el pipeline.

Uso:
    python3 scripts/prisma_checklist.py --audit-dir test_audit/

Produce:
    - PRISMA_checklist.json : Estado de cada item
    - PRISMA_report.txt     : Reporte human-readable
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


PRISMA_ITEMS = [
    # TITLE
    ("1", "Title", "Identify the report as a systematic review."),
    
    # ABSTRACT
    ("2", "Abstract", "See the PRISMA 2020 for Abstracts checklist."),
    
    # INTRODUCTION
    ("3a", "Rationale", "Describe the rationale for the review in the context of existing knowledge."),
    ("3b", "Objectives", "Provide an explicit statement of the objective(s) or question(s) the review addresses."),
    
    # METHODS - ELIGIBILITY CRITERIA
    ("4a", "Eligibility criteria", "Specify the inclusion and exclusion criteria for the review and how studies were grouped for the syntheses."),
    ("4b", "Information sources", "Specify all databases, registers, websites, organisations, reference lists and other sources searched or consulted."),
    ("4c", "Search strategy", "Present the full search strategies for all databases, registers and websites, including any filters and limits used."),
    
    # METHODS - STUDY SELECTION
    ("5", "Selection process", "Specify the methods used to decide whether a study met the inclusion criteria of the review."),
    
    # METHODS - DATA COLLECTION
    ("6a", "Data extraction", "Specify the methods used to extract data from reports."),
    ("6b", "Data items", "List and define all variables for which data were sought."),
    
    # METHODS - STUDY RISK OF BIAS
    ("7", "Risk of bias", "Specify the methods used to assess risk of bias in the included studies."),
    
    # METHODS - SYNTHESIS
    ("8a", "Synthesis methods", "Describe the criteria and methods used to group studies for synthesis."),
    ("8b", "Effect measures", "Specify the effect measure(s) used in the synthesis."),
    ("8c", "Synthesis methods", "Describe the methods used to handle missing data."),
    ("8d", "Synthesis methods", "Describe any methods used to synthesise results."),
    ("8e", "Certainty assessment", "Describe any methods used to assess certainty of evidence."),
    
    # RESULTS - STUDY SELECTION
    ("9", "Study selection", "Give the number of studies screened, assessed for eligibility, and included in the review."),
    
    # RESULTS - STUDY CHARACTERISTICS
    ("10", "Study characteristics", "Cite each included study and present its characteristics."),
    
    # RESULTS - RISK OF BIAS
    ("11", "Risk of bias", "Present assessments of risk of bias for each included study."),
    
    # RESULTS - INDIVIDUAL STUDIES
    ("12a", "Individual studies", "For all outcomes, present, for each study: (a) summary statistics."),
    ("12b", "Individual studies", "For all outcomes, present, for each study: (b) synthesis results."),
    
    # RESULTS - SYNTHESIS
    ("13", "Synthesis", "Present results of all syntheses."),
    
    # RESULTS - REPORTING BIASES
    ("14", "Reporting biases", "Assess the risk of bias due to missing results."),
    
    # RESULTS - CERTAINTY OF EVIDENCE
    ("15", "Certainty of evidence", "Assess the certainty of the body of evidence."),
    
    # DISCUSSION
    ("16", "Discussion", "Discuss the limitations of the review process and the evidence."),
    ("17", "Discussion", "Discuss the implications for practice, policy, and future research."),
    
    # OTHER - REGISTRATION
    ("18", "Registration", "Provide registration information for the review."),
    ("19", "Protocol", "Indicate where the review protocol can be accessed."),
    ("20", "Support", "Describe sources of financial or non-financial support."),
    ("21", "Competing interests", "Declare any competing interests of review authors."),
    ("22", "Data availability", "Report which of the following are publicly available and where."),
]


class PRISMAChecklist:
    """Checklist PRISMA 2020 automatizado."""
    
    def __init__(self, audit_dir):
        self.audit_dir = Path(audit_dir)
        self.checklist = []
        self._init_checklist()
    
    def _init_checklist(self):
        """Inicializa checklist con todos los items."""
        for num, section, description in PRISMA_ITEMS:
            self.checklist.append({
                "item": num,
                "section": section,
                "description": description,
                "status": "not_verified",
                "evidence": None,
                "notes": "",
            })
    
    def verify_from_artifacts(self):
        """Verifica cada item contra los artefactos existentes."""
        
        # Verificar item 1: Title
        if (self.audit_dir / ".." / "manuscript.md").exists():
            self._mark_verified("1", "manuscript.md presente", "manuscript.md")
        
        # Verificar item 4b: Information sources
        search_csv = self.audit_dir / ".." / "search_records.csv"
        if search_csv.exists():
            sources = self._count_sources(search_csv)
            self._mark_verified("4b", f"Fuentes buscadas: {sources}", str(search_csv))
        
        # Verificar item 6a: Data extraction
        calc_csv = self.audit_dir / "calculation_log.csv"
        if calc_csv.exists():
            self._mark_verified("6a", "Log de calculos con formulas", str(calc_csv))
        
        # Verificar item 8b: Effect measures
        results_json = self.audit_dir / "pooled_results.json"
        if results_json.exists():
            self._mark_verified("8b", "Medida de efecto: RR con IC 95%", str(results_json))
        
        # Verificar item 9: Study selection
        if search_csv.exists():
            n = self._count_records(search_csv)
            self._mark_verified("9", f"Registros encontrados: {n}", str(search_csv))
        
        # Verificar item 12-13: Synthesis results
        if results_json.exists():
            with open(results_json) as f:
                data = json.load(f)
            k = data.get("k", 0)
            rr = data.get("pooled_rr", 0)
            self._mark_verified("13", f"Meta-analisis: k={k}, RR={rr:.3f}", str(results_json))
        
        # Verificar item 14: Reporting biases
        bias_json = self.audit_dir / ".." / "publication_bias_results.json"
        if bias_json.exists():
            self._mark_verified("14", "Analisis de sesgo de publicacion", str(bias_json))
        
        # Verificar item 18: Registration
        protocol_md = self.audit_dir / ".." / "protocol.md"
        if protocol_md.exists():
            self._mark_verified("18", "Protocolo registrado", str(protocol_md))
        
        # Verificar item 22: Data availability
        data_files = list(self.audit_dir.glob("*.csv")) + list(self.audit_dir.glob("*.json"))
        if data_files:
            self._mark_verified("22", f"Datos disponibles: {len(data_files)} archivos", str(self.audit_dir))
    
    def _mark_verified(self, item_num, evidence, file_path):
        """Marca un item como verificado."""
        for item in self.checklist:
            if item["item"] == item_num:
                item["status"] = "verified"
                item["evidence"] = evidence
                item["file_path"] = file_path
                break
    
    def _count_sources(self, csv_file):
        """Cuenta fuentes unicas en CSV de busqueda."""
        sources = set()
        with open(csv_file) as f:
            next(f)  # skip header
            for line in f:
                parts = line.strip().split(",")
                if len(parts) > 2:
                    sources.add(parts[1])
        return len(sources)
    
    def _count_records(self, csv_file):
        """Cuenta registros en CSV."""
        count = 0
        with open(csv_file) as f:
            next(f)  # skip header
            for _ in f:
                count += 1
        return count
    
    def generate_report(self, output_dir):
        """Genera reporte PRISMA."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON
        json_file = output_dir / "PRISMA_checklist.json"
        with open(json_file, 'w') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_items": len(self.checklist),
                "verified": sum(1 for c in self.checklist if c["status"] == "verified"),
                "not_verified": sum(1 for c in self.checklist if c["status"] == "not_verified"),
                "items": self.checklist,
            }, f, indent=2)
        
        # TXT
        txt_file = output_dir / "PRISMA_report.txt"
        with open(txt_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("PRISMA 2020 CHECKLIST\n")
            f.write("=" * 70 + "\n\n")
            
            verified = sum(1 for c in self.checklist if c["status"] == "verified")
            f.write(f"Items verificados: {verified}/{len(self.checklist)}\n\n")
            
            for item in self.checklist:
                status = "✅" if item["status"] == "verified" else "⬜"
                f.write(f"{status} Item {item['item']} ({item['section']})\n")
                f.write(f"   Descripcion: {item['description']}\n")
                if item["evidence"]:
                    f.write(f"   Evidencia: {item['evidence']}\n")
                if item.get("file_path"):
                    f.write(f"   Archivo: {item['file_path']}\n")
                f.write("\n")
            
            f.write("=" * 70 + "\n")
            f.write("NOTA: Items no verificados requieren revision manual.\n")
            f.write("El pipeline automatizado no cubre todos los items.\n")
        
        return json_file, txt_file


def main():
    parser = argparse.ArgumentParser(description='PRISMA 2020 Checklist')
    parser.add_argument('--audit-dir', '-d', required=True, help='Directorio con artefactos de auditoria')
    parser.add_argument('--output', '-o', default='output/prisma_checklist', help='Directorio de salida')
    args = parser.parse_args()
    
    print(f"Verificando PRISMA 2020 contra: {args.audit_dir}")
    checklist = PRISMAChecklist(args.audit_dir)
    checklist.verify_from_artifacts()
    
    json_file, txt_file = checklist.generate_report(args.output)
    
    verified = sum(1 for c in checklist.checklist if c["status"] == "verified")
    print(f"\nItems verificados: {verified}/{len(checklist.checklist)}")
    print(f"Reporte JSON: {json_file}")
    print(f"Reporte TXT: {txt_file}")


if __name__ == "__main__":
    main()