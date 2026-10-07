#!/usr/bin/env python3
"""
Martyr v5.0 — Orquestador Principal de Meta-Análisis PRISMA 2020
=================================================================
Pipeline de 12 fases con 7 gates de aprobación obligatorios.
Python puro. Sin R.

Uso:
    python3 martyr.py --topic "timing RRT in AKI" --pico "P:ICU AKI;I:early RRT;C:late RRT;O:mortality" --full-prisma
    python3 martyr.py --data-file studies.csv --effect-type RR --random-effects
    python3 martyr.py --topic "sepsis bundle" --search-only
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Añadir scripts al path
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "stats"))

from stats.pooling import PoolingEngine, StudyData
from stats.effects import rr_to_log_scale, back_transform_log, back_transform_log_ci
from stats.heterogeneity import compute_het_stats
from gate_reporter import GateReporter, PreflightValidator, report_gate

# ── integración Martyria search ─────────────────────────────
SEARCH_SCRIPT_DIR = Path(__file__).parent / "scripts" / "search"
sys.path.insert(0, str(SEARCH_SCRIPT_DIR))

try:
    from search_parallel import ParallelSearcher
    _SEARCH_AVAILABLE = True
except ImportError as _e:
    ParallelSearcher = None
    _SEARCH_AVAILABLE = False
    _SEARCH_IMPORT_ERROR = str(_e)


# ── constantes ────────────────────────────────────────────────
VERSION = "5.0.0"
DEFAULT_OUTPUT_DIR = "output"


# ── parser de argumentos ────────────────────────────────────
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Martyr v{VERSION} — Meta-Análisis Médico PRISMA 2020",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  Pipeline completo PRISMA:
    %(prog)s --topic "timing RRT in AKI" --pico "P:ICU AKI;I:early RRT;C:late RRT;O:mortality" --full-prisma

  Meta-análisis directo desde CSV:
    %(prog)s --data-file studies.csv --effect-type RR --model DL

  Solo búsqueda:
    %(prog)s --topic "sepsis bundle" --search-only
        """,
    )
    
    # Argumentos principales
    parser.add_argument("--topic", "-t", type=str, help="Tema a investigar")
    parser.add_argument("--pico", "-p", type=str, help="PICO/PECO: P:...;I:...;C:...;O:...")
    parser.add_argument("--data-file", "-d", type=str, help="Archivo CSV con datos extraídos")
    parser.add_argument("--effect-type", "-e", type=str, default="RR",
                        choices=["RR", "OR", "RD", "MD", "SMD", "g"],
                        help="Tipo de medida de efecto (default: RR)")
    parser.add_argument("--model", "-m", type=str, default="DL",
                        choices=["FE", "DL", "REML", "HS", "SJ", "ML"],
                        help="Modelo de pooling (default: DL)")
    
    # Modos de operación
    parser.add_argument("--full-prisma", action="store_true",
                        help="Ejecutar pipeline PRISMA completo (L1-L12)")
    parser.add_argument("--search-only", action="store_true",
                        help="Solo búsqueda + deduplicación")
    parser.add_argument("--skip-gates", action="store_true",
                        help="Saltar validación de gates (solo para testing)")
    
    # Opciones de output
    parser.add_argument("--output-dir", "-o", type=str, default=DEFAULT_OUTPUT_DIR,
                        help="Directorio de salida")
    parser.add_argument("--format", "-f", type=str, default="png",
                        choices=["png", "svg", "pdf"],
                        help="Formato de gráficos")
    
    # Opciones de búsqueda
    parser.add_argument("--max-results", "-n", type=int, default=50,
                        help="Máximo de artículos por fuente")
    parser.add_argument("--years", "-y", type=int, default=10,
                        help="Años hacia atrás en búsqueda")
    parser.add_argument("--years-all", "-Y", action="store_true",
                        help="Buscar toda la literatura histórica")
    
    return parser


# ── funciones de utilidad ────────────────────────────────────
def ensure_output_dir(topic: str, output_dir: str) -> Path:
    """Crea directorio de salida con timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(c if c.isalnum() else "_" for c in topic)[:30]
    path = Path(output_dir) / f"{timestamp}_{safe_topic}"
    path.mkdir(parents=True, exist_ok=True)
    (path / "plots").mkdir(exist_ok=True)
    (path / "tables").mkdir(exist_ok=True)
    return path


def parse_pico(pico_str: str) -> Dict[str, str]:
    """Parsea string PICO en componentes."""
    parts = {}
    for part in pico_str.split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            parts[key.strip().upper()] = value.strip()
    return parts


def load_studies_from_csv(filepath: str) -> List[StudyData]:
    """Carga estudios desde CSV con datos extraídos."""
    studies = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Determinar escala según tipo de efecto
            effect_measure = row.get("effect_measure", "RR").upper()
            
            if effect_measure in ("RR", "OR"):
                # Usar log-scale si ya existe, o calcular desde RR
                if "yi" in row and "vi" in row:
                    yi = float(row["yi"])
                    vi = float(row["vi"])
                else:
                    rr = float(row.get("rr", row.get("or", 1.0)))
                    ci_lower = float(row.get("rr_ci_lower", row.get("or_ci_lower", 0.8)))
                    ci_upper = float(row.get("rr_ci_upper", row.get("or_ci_upper", 1.2)))
                    yi, vi = rr_to_log_scale(rr, ci_lower, ci_upper)
            else:
                yi = float(row.get("yi", 0.0))
                vi = float(row.get("vi", 0.01))
            
            study = StudyData(
                study_id=row.get("study_id", "unknown"),
                author=row.get("author", "Unknown"),
                year=int(row.get("year", 2020)),
                yi=yi,
                vi=vi,
                n_i=int(row.get("n_i", 0)) if row.get("n_i") else None,
                n_c=int(row.get("n_c", 0)) if row.get("n_c") else None,
                subgroup=row.get("subgroup") or None,
                events_i=int(row.get("events_i", 0)) if row.get("events_i") else None,
                events_c=int(row.get("events_c", 0)) if row.get("events_c") else None,
                effect_measure=effect_measure,
            )
            studies.append(study)
    
    return studies


# ── fases del pipeline ────────────────────────────────────────
class MartyrPipeline:
    """Pipeline de 12 fases PRISMA con 7 gates."""
    
    def __init__(self, args):
        self.args = args
        self.reporter = GateReporter()
        self.validator = PreflightValidator()
        self.output_dir: Optional[Path] = None
        self.studies: List[StudyData] = []
        self.result = None
    
    def run(self) -> int:
        """Ejecuta pipeline según modo seleccionado."""
        print(f"\n{'='*60}")
        print(f"  MARTYR v{VERSION} — Meta-Análisis Médico PRISMA 2020")
        print(f"{'='*60}\n")
        
        if self.args.data_file:
            # Modo directo: meta-análisis desde CSV
            return self._run_direct_meta()
        elif self.args.search_only:
            # Modo búsqueda solo
            return self._run_search_only()
        elif self.args.full_prisma:
            # Pipeline completo PRISMA
            return self._run_full_prisma()
        else:
            print("❌ Error: Especifica --data-file, --search-only, o --full-prisma")
            return 1
    
    def _run_direct_meta(self) -> int:
        """Meta-análisis directo desde archivo CSV (L8-L10)."""
        print("📊 Modo: Meta-análisis directo desde CSV\n")
        
        # Validar gate 4 (datos verificados) si no se salta
        if not self.args.skip_gates:
            if not self.validator.validate(4):
                print("\n⚠️  Gate 4 no aprobado. Usa --skip-gates para testing.")
                return 1
        
        # Cargar datos
        print(f"Cargando datos desde: {self.args.data_file}")
        try:
            self.studies = load_studies_from_csv(self.args.data_file)
        except FileNotFoundError:
            print(f"❌ Archivo no encontrado: {self.args.data_file}")
            return 1
        except Exception as e:
            print(f"❌ Error cargando CSV: {e}")
            return 1
        
        print(f"✅ {len(self.studies)} estudios cargados")
        
        # Crear output
        topic = Path(self.args.data_file).stem
        self.output_dir = ensure_output_dir(topic, self.args.output_dir)
        
        # Ejecutar meta-análisis
        return self._execute_meta_analysis()
    
    def _execute_meta_analysis(self) -> int:
        """Ejecuta análisis estadístico y genera outputs."""
        print(f"\n{'─'*60}")
        print("FASE 8-10: Meta-Análisis Estadístico")
        print(f"{'─'*60}\n")
        
        # Pooling
        print(f"Modelo: {self.args.model}")
        print(f"Medida de efecto: {self.args.effect_type}")
        print(f"Estudios: {len(self.studies)}")
        print("")
        
        engine = PoolingEngine(method=self.args.model)
        self.result = engine.fit(self.studies)
        
        # Reportar resultados
        self._print_results()
        
        # Guardar resultados
        self._save_results()
        
        # Generar plots (si matplotlib disponible)
        self._generate_plots()
        
        print(f"\n✅ Análisis completo. Resultados guardados en: {self.output_dir}")
        return 0
    
    def _print_results(self):
        """Imprime resultados en consola."""
        r = self.result
        
        print("━" * 60)
        print("RESULTADOS DEL META-ANÁLISIS")
        print("━" * 60)
        
        # Efecto agrupado (back-transform si es log-scale)
        if self.args.effect_type in ("RR", "OR"):
            pooled = math.exp(r.pooled_effect)
            ci_l = math.exp(r.ci_lower)
            ci_u = math.exp(r.ci_upper)
            pi_l = math.exp(r.pi_lower)
            pi_u = math.exp(r.pi_upper)
            print(f"\nPooled {self.args.effect_type}: {pooled:.3f} [{ci_l:.3f}-{ci_u:.3f}]")
            print(f"95% Prediction Interval: {pi_l:.3f}-{pi_u:.3f}")
        else:
            print(f"\nPooled Effect: {r.pooled_effect:.3f} [{r.ci_lower:.3f}-{r.ci_upper:.3f}]")
        
        print(f"p-value: {r.p_value:.4f}")
        print(f"z-value: {r.z_value:.2f}")
        
        # Heterogeneidad
        print(f"\nHETEROGENEIDAD:")
        print(f"  I²: {r.I2:.1f}%")
        print(f"  τ²: {r.tau2:.4f}")
        print(f"  Q: {r.Q:.2f} (df={r.df_Q}, p={r.p_Q:.4f})")
        print(f"  H: {r.H:.2f}")
        
        # Pesos
        print(f"\nPESOS POR ESTUDIO:")
        for s, w in zip(r.study_effects, r.weights):
            print(f"  {s.study_id}: {w:.1f}%")
        
        # Flags
        if r.flags:
            print(f"\n⚠️  FLAGS DE AUDITORÍA:")
            for flag in r.flags:
                emoji = "🔴" if flag["level"] == "red" else "🟡" if flag["level"] == "yellow" else "🟢"
                print(f"  {emoji} [{flag['id']}] {flag['action']}")
        else:
            print(f"\n✅ Sin flags de auditoría")
        
        print("━" * 60)
    
    def _save_results(self):
        """Guarda resultados en archivos."""
        if self.output_dir is None:
            return
        
        # JSON
        json_path = self.output_dir / "meta_analysis_results.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, indent=2, ensure_ascii=False)
        
        # CSV de datos
        csv_path = self.output_dir / "tables" / "studies_data.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["study_id", "author", "year", "yi", "vi", "weight_%", "subgroup"])
            for s, w in zip(self.result.study_effects, self.result.weights):
                writer.writerow([s.study_id, s.author, s.year, s.yi, s.vi, f"{w:.2f}", s.subgroup or ""])
        
        print(f"\n💾 Resultados guardados:")
        print(f"   JSON: {json_path}")
        print(f"   CSV: {csv_path}")
    
    def _generate_plots(self):
        """Genera gráficos con matplotlib."""
        try:
            import matplotlib
            matplotlib.use("Agg")  # Non-interactive backend
            
            # Importar forest plot
            from plots.forest_plot import generate_forest_plot, StudyData as PlotStudy, MetaAnalysisResult as PlotMeta
            
            studies_plot = [
                PlotStudy(
                    id=s.study_id,
                    label=f"{s.author} {s.year}",
                    effect=math.exp(s.yi) if self.args.effect_type in ("RR", "OR") else s.yi,
                    lower_ci=math.exp(s.yi - 1.96 * math.sqrt(s.vi)) if self.args.effect_type in ("RR", "OR") else s.yi - 1.96 * math.sqrt(s.vi),
                    upper_ci=math.exp(s.yi + 1.96 * math.sqrt(s.vi)) if self.args.effect_type in ("RR", "OR") else s.yi + 1.96 * math.sqrt(s.vi),
                    weight_pct=w,
                    n_total=(s.n_i or 0) + (s.n_c or 0),
                )
                for s, w in zip(self.result.study_effects, self.result.weights)
            ]
            
            meta_plot = PlotMeta(
                pooled_effect=math.exp(self.result.pooled_effect) if self.args.effect_type in ("RR", "OR") else self.result.pooled_effect,
                pooled_lower=math.exp(self.result.ci_lower) if self.args.effect_type in ("RR", "OR") else self.result.ci_lower,
                pooled_upper=math.exp(self.result.ci_upper) if self.args.effect_type in ("RR", "OR") else self.result.ci_upper,
                i2=self.result.I2,
                tau2=self.result.tau2,
                p_value=self.result.p_Q,
                model=self.result.model[:2],
            )
            
            # Crear directorio de plots en el output correcto
            plots_dir = self.output_dir / "plots"
            plots_dir.mkdir(parents=True, exist_ok=True)
            
            plot_path = generate_forest_plot(
                studies_plot, meta_plot,
                effect_type=self.args.effect_type,
                outfile="forest_plot",
                outdir=str(plots_dir),
                fmt=self.args.format,
                title=f"Forest Plot: {self.args.topic or 'Meta-Analysis'}",
            )
            print(f"\n📊 Forest plot generado: {plot_path}")
            
        except ImportError as e:
            print(f"\n⚠️  No se pudo generar plots: {e}")
        except Exception as e:
            print(f"\n⚠️  Error generando plots: {e}")
    
    def _run_search_only(self) -> int:
        """Ejecuta solo búsqueda + deduplicación."""
        print("🔍 Modo: Solo búsqueda\n")
        
        if not self.args.topic:
            print("❌ Error: --topic requerido para búsqueda")
            return 1
        
        # Placeholder: aquí se integraría search_parallel.py
        print(f"Tema: {self.args.topic}")
        print("Buscando en PubMed, Cochrane, ClinicalTrials.gov, Semantic Scholar...")
        print("(Integración con Martyria search_parallel.py pendiente)")
        
        self.output_dir = ensure_output_dir(self.args.topic, self.args.output_dir)
        print(f"\n📁 Resultados de búsqueda se guardarían en: {self.output_dir}")
        
        return 0
    
    def _run_full_prisma(self) -> int:
        """Pipeline completo PRISMA (placeholder)."""
        print("📋 Modo: Pipeline PRISMA completo\n")
        
        if not self.args.topic or not self.args.pico:
            print("❌ Error: --topic y --pico requeridos para pipeline completo")
            return 1
        
        pico = parse_pico(self.args.pico)
        print(f"Tema: {self.args.topic}")
        print(f"PICO: {json.dumps(pico, indent=2, ensure_ascii=False)}")
        
        self.output_dir = ensure_output_dir(self.args.topic, self.args.output_dir)
        
        # L1: Protocolo (Gate 1)
        print(f"\n{'─'*60}")
        print("L1: Protocolo PROSPERO")
        print(f"{'─'*60}")
        print(report_gate(1,
            "PICO definido, estrategia de búsqueda propuesta",
            f"{self.output_dir}/protocol.md",
            [f"P: {pico.get('P', 'N/A')}",
             f"I: {pico.get('I', 'N/A')}",
             f"C: {pico.get('C', 'N/A')}",
             f"O: {pico.get('O', 'N/A')}"],
            "Revisar PICO y confirmar términos de búsqueda"
        ))
        
        print("\n⚠️  Pipeline bloqueado en Gate 1. Aprueba el gate para continuar.")
        print("   Usa: python3 scripts/gate_reporter.py")
        
        return 0


# ── entry point ──────────────────────────────────────────────
def main():
    parser = create_parser()
    args = parser.parse_args()
    
    pipeline = MartyrPipeline(args)
    sys.exit(pipeline.run())


if __name__ == "__main__":
    main()
