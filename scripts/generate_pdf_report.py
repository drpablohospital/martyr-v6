#!/usr/bin/env python3
"""
Genera reporte de PMIDs para que el usuario aporte PDFs.
Este reporte se genera cuando los abstracts no tienen datos completos.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def generate_pdf_report(evidence_report_path: str, output_dir: str):
    """Genera reporte de PMIDs para descarga manual de PDFs."""
    
    with open(evidence_report_path, 'r') as f:
        data = json.load(f)
    
    report_lines = [
        "=" * 80,
        "REPORTE DE ARTICULOS PARA DESCARGA MANUAL DE PDFs",
        "=" * 80,
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Pregunta: {data.get('pico', {}).get('query_pubmed', 'N/A')}",
        "",
        "Los siguientes articulos podrian aportar datos completos para el meta-analisis.",
        "Por favor, descargue los PDFs y coloquelos en la carpeta indicada.",
        "",
        "=" * 80,
        "INSTRUCCIONES:",
        "=" * 80,
        "",
        "1. Descargue los PDFs de los articulos listados abajo",
        "2. Coloque los PDFs en: ~/.openclaw/workspace/skills/martyr/pdfs/",
        "3. Nombre los archivos como: PMID_{numero}.pdf",
        "4. Ejecute nuevamente el pipeline para incluir los datos extraidos de los PDFs",
        "",
        "Alternativamente, puede proporcionar los datos manualmente en el CSV generado.",
        "",
        "=" * 80,
        "ARTICULOS RECOMENDADOS:",
        "=" * 80,
        "",
    ]
    
    for i, article in enumerate(data.get('articles', [])[:10], 1):
        pmid = article.get('pmid', 'N/A')
        title = article.get('title', 'N/A')
        authors = ', '.join(article.get('authors', [])[:2]) if article.get('authors') else 'N/A'
        year = article.get('year', 'N/A')
        study_type = article.get('study_type', 'N/A')
        
        report_lines.extend([
            f"{i}. PMID: {pmid}",
            f"   Titulo: {title}",
            f"   Autores: {authors}",
            f"   Año: {year}",
            f"   Tipo: {study_type}",
            f"   URL PubMed: https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            f"   URL PDF (si disponible): https://pubmed.ncbi.nlm.nih.gov/{pmid}/?format=pub",
            "",
        ])
    
    report_lines.extend([
        "=" * 80,
        "NOTAS:",
        "=" * 80,
        "",
        "- Los articulos tipo 'Systematic Review' o 'Meta-analysis' suelen resumir datos de multiples RCTs",
        "- Los articulos tipo 'Randomized Controlled Trial' son los que aportan datos primarios",
        "- Si no tiene acceso al PDF completo, puede usar Sci-Hub o contactar a los autores",
        "- Para ClinicalTrials.gov, busque el NCT ID y descargue el protocolo y resultados",
        "",
        "=" * 80,
    ])
    
    report_text = '\n'.join(report_lines)
    
    # Guardar reporte
    output_path = Path(output_dir) / "PDF_DOWNLOAD_REPORT.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report_text)
    
    print(report_text)
    print(f"\nReporte guardado en: {output_path}")
    print(f"Carpeta para PDFs: ~/.openclaw/workspace/skills/martyr/pdfs/")
    
    return str(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python generate_pdf_report.py <evidence_report.json> <output_dir>")
        sys.exit(1)
    
    generate_pdf_report(sys.argv[1], sys.argv[2])
