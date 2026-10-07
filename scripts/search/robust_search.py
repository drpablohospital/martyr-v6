#!/usr/bin/env python3
"""
Martyr v5.2 — Motor de Busqueda Robusta con Retry
===================================================
- Maneja rate-limits con backoff exponencial
- Guarda progreso incremental (no repite lo ya encontrado)
- Produce logs auditables en CSV + TXT
- Timestamp de cada operacion
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

class AuditLogger:
    """Logger de auditoria para cada operacion."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.output_dir / "audit_log.txt"
        self.csv_file = self.output_dir / "search_records.csv"
        self._init_csv()
    
    def _init_csv(self):
        """Inicializa CSV con headers si no existe."""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w') as f:
                f.write("timestamp,source,query,pmid,nct_id,title,authors,year,journal,doi,status,attempt\n")
    
    def log(self, message, level="INFO"):
        """Escribe linea en log TXT."""
        timestamp = datetime.now().isoformat()
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    
    def log_record(self, source, query, record, status="found", attempt=1):
        """Escribe registro en CSV."""
        timestamp = datetime.now().isoformat()
        pmid = record.get('pmid', '')
        nct_id = record.get('nct_id', '')
        title = record.get('title', '').replace(',', ';').replace('"', "'")[:200]
        authors = '|'.join(record.get('authors', [])[:3]).replace(',', ';')
        year = record.get('year', '')
        journal = record.get('journal', '').replace(',', ';')[:100]
        doi = record.get('doi', '')
        
        with open(self.csv_file, 'a') as f:
            f.write(f"{timestamp},{source},{query},{pmid},{nct_id},{title},{authors},{year},{journal},{doi},{status},{attempt}\n")


class RobustSearcher:
    """Buscador robusto con retry y backoff exponencial."""
    
    def __init__(self, email="drpablo.hospita@gmail.com", output_dir="output/search_audit"):
        self.email = email
        self.logger = AuditLogger(output_dir)
        self.seen_pmids = set()
        self.seen_ncts = set()
        self.max_retries = 10
        self.base_delay = 10  # segundos
        self.max_delay = 600  # 5 minutos maximo
    
    def _already_seen(self, record):
        """Verifica si el registro ya fue encontrado."""
        pmid = record.get('pmid')
        nct = record.get('nct_id')
        if pmid and pmid in self.seen_pmids:
            return True
        if nct and nct in self.seen_ncts:
            return True
        return False
    
    def _mark_seen(self, record):
        """Marca registro como visto."""
        if record.get('pmid'):
            self.seen_pmids.add(record['pmid'])
        if record.get('nct_id'):
            self.seen_ncts.add(record['nct_id'])
    
    def _search_with_retry(self, search_func, query, source_name):
        """Ejecuta busqueda con retry y backoff."""
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.log(f"Intento {attempt}/{self.max_retries}: {source_name} - '{query}'")
                results = search_func(query)
                
                new_results = []
                for r in results:
                    if not self._already_seen(r):
                        self._mark_seen(r)
                        new_results.append(r)
                        self.logger.log_record(source_name, query, r, "found", attempt)
                
                self.logger.log(f"EXITO: {len(new_results)} nuevos de {source_name}")
                return new_results
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Too Many Requests" in error_msg or "Rate limit" in error_msg:
                    delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                    self.logger.log(f"RATE LIMIT {source_name}: esperando {delay}s antes de reintentar...", "WARN")
                    time.sleep(delay)
                else:
                    self.logger.log(f"ERROR {source_name}: {error_msg}", "ERROR")
                    return []
        
        self.logger.log(f"AGOTADO: {source_name} fallo despues de {self.max_retries} intentos", "ERROR")
        return []
    
    def search_all_robust(self, topic, max_results=50, years_back=10):
        """Busqueda robusta en todas las fuentes."""
        from search_parallel import ParallelSearcher
        
        self.logger.log(f"=" * 60)
        self.logger.log(f"INICIANDO BUSQUEDA ROBUSTA")
        self.logger.log(f"Topic: {topic}")
        self.logger.log(f"Max results: {max_results}")
        self.logger.log(f"Years back: {years_back}")
        self.logger.log(f"=" * 60)
        
        # Cargar IDs ya vistos de archivos previos
        self._load_existing_records()
        
        searcher = ParallelSearcher(email=self.email)
        all_results = []
        
        # PubMed (con retry)
        try:
            pm_results = self._search_with_retry(
                lambda q: self._extract_pubmed(searcher, q, max_results, years_back),
                topic,
                "PubMed"
            )
            all_results.extend(pm_results)
        except Exception as e:
            self.logger.log(f"PubMed completamente fallo: {e}", "ERROR")
        
        # ClinicalTrials (con retry)
        try:
            ct_results = self._search_with_retry(
                lambda q: self._extract_ct(searcher, q, max_results, years_back),
                topic,
                "ClinicalTrials"
            )
            all_results.extend(ct_results)
        except Exception as e:
            self.logger.log(f"ClinicalTrials completamente fallo: {e}", "ERROR")
        
        # Guardar resumen
        self._save_summary(topic, all_results)
        
        return all_results
    
    def _load_existing_records(self):
        """Carga IDs de busquedas previas."""
        if self.logger.csv_file.exists():
            with open(self.logger.csv_file, 'r') as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 5:
                        pmid = parts[3]
                        nct = parts[4]
                        if pmid:
                            self.seen_pmids.add(pmid)
                        if nct:
                            self.seen_ncts.add(nct)
    
    def _extract_pubmed(self, searcher, query, max_results, years_back):
        """Extrae resultados de PubMed."""
        results = searcher.search_all(query, max_results=max_results, years_back=years_back)
        unified = results.get('unified', [])
        return [u for u in unified if u.get('source') == 'pubmed']
    
    def _extract_ct(self, searcher, query, max_results, years_back):
        """Extrae resultados de ClinicalTrials."""
        results = searcher.search_all(query, max_results=max_results, years_back=years_back)
        unified = results.get('unified', [])
        return [u for u in unified if u.get('source') == 'clinicaltrials']
    
    def _save_summary(self, topic, results):
        """Guarda resumen de busqueda."""
        summary_file = self.logger.output_dir / "search_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(f"BUSQUEDA: {topic}\n")
            f.write(f"Fecha: {datetime.now().isoformat()}\n")
            f.write(f"Total articulos nuevos: {len(results)}\n")
            f.write(f"PMIDs unicos: {len(self.seen_pmids)}\n")
            f.write(f"NCT IDs unicos: {len(self.seen_ncts)}\n")
            f.write("\nArticulos encontrados:\n")
            for r in results[:50]:
                f.write(f"  - {r.get('title', 'N/A')[:80]}... (PMID:{r.get('pmid', 'N/A')})\n")


if __name__ == "__main__":
    # Demo
    searcher = RobustSearcher()
    results = searcher.search_all_robust("acute kidney injury renal replacement therapy timing", max_results=3)
    print(f"Total resultados nuevos: {len(results)}")
    print(f"Ver logs en: {searcher.logger.output_dir}")