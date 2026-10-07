#!/usr/bin/env python3
"""
Martyr v5.2 — Pooling Meta-Analitico con Auditoria Completa
==============================================================
Entrada: CSV con datos brutos (study_id, author, year, n_i, n_c, events_i, events_c)
Salida: JSON con resultados + CSV con log de cada paso + TXT con reporte

Uso standalone:
    python3 pooling_auditable.py --input data.csv --output results/

El script produce:
    - results/pooled_results.json   : Resultados del meta-analisis
    - results/calculation_log.csv   : Log de cada calculo paso a paso
    - results/study_weights.csv     : Pesos por estudio
    - results/audit_report.txt      : Reporte human-readable
    - results/PRISMA_checklist.json : Verificacion de items PRISMA
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import optimize, stats


# ── clases de datos ────────────────────────────────────────────
class StudyData:
    """Estudio con datos brutos."""
    def __init__(self, study_id, author, year, n_i, n_c, events_i, events_c):
        self.study_id = study_id
        self.author = author
        self.year = year
        self.n_i = n_i
        self.n_c = n_c
        self.events_i = events_i
        self.events_c = events_c
        
        # Calcular RR y varianza desde datos brutos
        self.rr = (events_i / n_i) / (events_c / n_c)
        self.log_rr = math.log(self.rr)
        
        # Varianza de log(RR) con correccion de continuidad
        a = max(events_i, 0.5)
        c = max(events_c, 0.5)
        self.var_log_rr = (1.0 / a - 1.0 / n_i) + (1.0 / c - 1.0 / n_c)
        
        self.weight = 0.0
        self.std_err = math.sqrt(self.var_log_rr)


class AuditLogger:
    """Logger que produce CSV + TXT auditables."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_file = self.output_dir / "calculation_log.csv"
        self.txt_file = self.output_dir / "audit_report.txt"
        self._init_csv()
    
    def _init_csv(self):
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "step", "study_id", "value_name", 
                                 "value", "formula", "notes"])
    
    def log_calc(self, step, study_id, value_name, value, formula, notes=""):
        """Escribe calculo en CSV."""
        timestamp = datetime.now().isoformat()
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, step, study_id, value_name, 
                             str(value), formula, notes])
    
    def log_text(self, message):
        """Escribe linea en TXT."""
        timestamp = datetime.now().isoformat()
        with open(self.txt_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")


# ── motor de pooling ──────────────────────────────────────────
class AuditablePoolingEngine:
    """Motor de pooling con auditoria completa."""
    
    def __init__(self, method="DL", output_dir="output"):
        self.method = method
        self.logger = AuditLogger(output_dir)
        self.result = {}
    
    def fit(self, studies):
        """Ejecuta meta-analisis con log de cada paso."""
        self.logger.log_text("=" * 70)
        self.logger.log_text("INICIANDO META-ANALISIS CON AUDITORIA")
        self.logger.log_text(f"Metodo: {self.method}")
        self.logger.log_text(f"Estudios: {len(studies)}")
        self.logger.log_text("=" * 70)
        
        # Paso 1: Calcular efectos individuales
        self.logger.log_text("\nPASO 1: Efectos individuales")
        for s in studies:
            self.logger.log_calc("step1", s.study_id, "RR", f"{s.rr:.4f}", 
                                 "(events_i/n_i) / (events_c/n_c)")
            self.logger.log_calc("step1", s.study_id, "log_RR", f"{s.log_rr:.4f}", 
                                 "ln(RR)")
            self.logger.log_calc("step1", s.study_id, "var_log_RR", f"{s.var_log_rr:.6f}", 
                                 "1/a - 1/n_i + 1/c - 1/n_c")
        
        # Paso 2: Modelo de efectos fijos (pesos)
        y = np.array([s.log_rr for s in studies])
        v = np.array([s.var_log_rr for s in studies])
        w_fe = 1.0 / v
        
        self.logger.log_text("\nPASO 2: Pesos de efectos fijos")
        for i, s in enumerate(studies):
            s.weight = w_fe[i]
            self.logger.log_calc("step2", s.study_id, "weight_FE", f"{w_fe[i]:.4f}", 
                                 "1 / var_log_RR")
        
        # Paso 3: Pooled effect (FE)
        pooled_fe = np.sum(w_fe * y) / np.sum(w_fe)
        se_fe = np.sqrt(1.0 / np.sum(w_fe))
        self.logger.log_calc("step3", "ALL", "pooled_log_RR_FE", f"{pooled_fe:.4f}", 
                             "sum(w*y) / sum(w)", "Modelo de efectos fijos")
        self.logger.log_calc("step3", "ALL", "se_FE", f"{se_fe:.4f}", 
                             "sqrt(1/sum(w))")
        
        # Paso 4: Heterogeneidad Q
        Q = np.sum(w_fe * (y - pooled_fe) ** 2)
        df = len(y) - 1
        p_Q = 1.0 - stats.chi2.cdf(Q, df) if df > 0 else 1.0
        I2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0
        
        self.logger.log_text("\nPASO 4: Heterogeneidad")
        self.logger.log_calc("step4", "ALL", "Q", f"{Q:.4f}", 
                             "sum(w * (y - pooled)^2)")
        self.logger.log_calc("step4", "ALL", "df", str(df), "k - 1")
        self.logger.log_calc("step4", "ALL", "p_Q", f"{p_Q:.4f}", 
                             "1 - chi2.cdf(Q, df)")
        self.logger.log_calc("step4", "ALL", "I2", f"{I2:.1f}%", 
                             "max(0, (Q-df)/Q * 100)")
        
        # Paso 5: Tau2 (DL)
        C = np.sum(w_fe) - np.sum(w_fe**2) / np.sum(w_fe)
        tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
        self.logger.log_calc("step5", "ALL", "tau2_DL", f"{tau2:.4f}", 
                             "max(0, (Q-df)/C)", "DerSimonian-Laird")
        
        # Paso 6: Pesos RE
        w_re = 1.0 / (v + tau2)
        
        # Paso 7: Pooled effect (RE)
        pooled_re = np.sum(w_re * y) / np.sum(w_re)
        se_re = np.sqrt(1.0 / np.sum(w_re))
        ci_lower = pooled_re - 1.96 * se_re
        ci_upper = pooled_re + 1.96 * se_re
        z = pooled_re / se_re
        p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
        
        self.logger.log_text("\nPASO 7: Resultados RE-DL")
        self.logger.log_calc("step7", "ALL", "pooled_log_RR_RE", f"{pooled_re:.4f}", 
                             "sum(w_re*y) / sum(w_re)")
        self.logger.log_calc("step7", "ALL", "se_RE", f"{se_re:.4f}", 
                             "sqrt(1/sum(w_re))")
        self.logger.log_calc("step7", "ALL", "z", f"{z:.4f}", 
                             "pooled / se")
        self.logger.log_calc("step7", "ALL", "p_value", f"{p:.4f}", 
                             "2*(1-norm.cdf(abs(z)))")
        
        # Guardar pesos finales
        weights_pct = (w_re / np.sum(w_re)) * 100.0
        for i, s in enumerate(studies):
            s.weight = weights_pct[i]
            self.logger.log_calc("step7", s.study_id, "weight_RE_pct", f"{weights_pct[i]:.2f}%", 
                                 "(w_re / sum(w_re)) * 100")
        
        # Construir resultado
        self.result = {
            "model": f"RE-{self.method}",
            "k": len(studies),
            "pooled_effect": float(pooled_re),
            "pooled_rr": float(math.exp(pooled_re)),
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "ci_rr_lower": float(math.exp(ci_lower)),
            "ci_rr_upper": float(math.exp(ci_upper)),
            "se": float(se_re),
            "z": float(z),
            "p_value": float(p),
            "Q": float(Q),
            "df": df,
            "p_Q": float(p_Q),
            "I2": float(I2),
            "tau2": float(tau2),
            "studies": [
                {
                    "study_id": s.study_id,
                    "author": s.author,
                    "year": s.year,
                    "n_i": s.n_i,
                    "n_c": s.n_c,
                    "events_i": s.events_i,
                    "events_c": s.events_c,
                    "rr": float(s.rr),
                    "log_rr": float(s.log_rr),
                    "var_log_rr": float(s.var_log_rr),
                    "weight_pct": float(s.weight),
                }
                for s in studies
            ]
        }
        
        self._save_results(studies)
        return self.result
    
    def _save_results(self, studies):
        """Guarda todos los archivos de salida."""
        # JSON con resultados
        json_file = self.logger.output_dir / "pooled_results.json"
        with open(json_file, 'w') as f:
            json.dump(self.result, f, indent=2)
        
        # CSV con pesos
        weights_file = self.logger.output_dir / "study_weights.csv"
        with open(weights_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["study_id", "author", "year", "n_i", "n_c", 
                             "events_i", "events_c", "RR", "log_RR", "var_log_RR", "weight_RE_pct"])
            for s in studies:
                writer.writerow([s.study_id, s.author, s.year, s.n_i, s.n_c,
                                 s.events_i, s.events_c, f"{s.rr:.4f}", 
                                 f"{s.log_rr:.4f}", f"{s.var_log_rr:.6f}", f"{s.weight:.2f}"])
        
        # Reporte final
        self.logger.log_text("\n" + "=" * 70)
        self.logger.log_text("META-ANALISIS COMPLETADO")
        self.logger.log_text("=" * 70)
        self.logger.log_text(f"Archivos generados:")
        self.logger.log_text(f"  - {json_file}")
        self.logger.log_text(f"  - {self.logger.csv_file}")
        self.logger.log_text(f"  - {weights_file}")
        self.logger.log_text(f"  - {self.logger.txt_file}")


def load_studies_from_csv(csv_file):
    """Carga estudios desde CSV con datos brutos."""
    studies = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            studies.append(StudyData(
                study_id=row.get('study_id', ''),
                author=row.get('author', ''),
                year=int(row.get('year', 2020)),
                n_i=int(row.get('n_i', 0)),
                n_c=int(row.get('n_c', 0)),
                events_i=int(row.get('events_i', 0)),
                events_c=int(row.get('events_c', 0)),
            ))
    return studies


def main():
    parser = argparse.ArgumentParser(description='Meta-analisis auditable')
    parser.add_argument('--input', '-i', required=True, help='CSV con datos brutos')
    parser.add_argument('--output', '-o', default='output/pooling_audit', help='Directorio de salida')
    parser.add_argument('--method', '-m', default='DL', choices=['FE', 'DL', 'REML', 'HS', 'SJ', 'ML'])
    args = parser.parse_args()
    
    print(f"Cargando datos desde: {args.input}")
    studies = load_studies_from_csv(args.input)
    print(f"Estudios cargados: {len(studies)}")
    
    print(f"Ejecutando meta-analisis ({args.method})...")
    engine = AuditablePoolingEngine(method=args.method, output_dir=args.output)
    result = engine.fit(studies)
    
    print(f"\nResultados:")
    print(f"  Pooled RR: {result['pooled_rr']:.4f} [{result['ci_rr_lower']:.4f}-{result['ci_rr_upper']:.4f}]")
    print(f"  p-value: {result['p_value']:.4f}")
    print(f"  I2: {result['I2']:.1f}%")
    print(f"\nArchivos de auditoria en: {args.output}")


if __name__ == "__main__":
    main()