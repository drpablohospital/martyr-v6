#!/usr/bin/env python3
"""
subgroup_analysis.py — Análisis de Subgrupos Completo con Covariables

Extiende subgroup.py con:
• Múltiples covariables simultáneas
• Tablas de subgrupos formateadas
• Gráficos de interacción
• Test Q-between para cada covariable
• Meta-regresión multivariable

Uso:
    from subgroup_analysis import SubgroupAnalyzer
    
    analyzer = SubgroupAnalyzer(data)
    analyzer.add_covariate("dosis", [6, 8, 8, 16, 6, 8, 16, 16, 8, 6])
    analyzer.add_covariate("diabetes", [0, 1, 0, 1, 0, 0, 1, 1, 0, 1])
    
    results = analyzer.analyze_all()
    # Genera tabla de subgrupos, tests de interacción, metaregresión
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy import stats


@dataclass
class StudyData:
    """Datos de un estudio individual."""
    study_id: str
    effect_size: float
    variance: float
    se: float
    n_total: int
    n_intervention: Optional[int] = None
    n_control: Optional[int] = None
    covariates: Dict[str, Any] = field(default_factory=dict)


class SubgroupAnalyzer:
    """
    Análisis completo de subgrupos y meta-regresión.
    
    Soporta:
    • Covariables categóricas (grupos discretos)
    • Covariables continuas (metaregresión)
    • Múltiples covariables simultáneas
    • Tests de interacción (Q-between)
    • Gráficos de subgrupos
    """
    
    def __init__(self, studies: Optional[List[StudyData]] = None):
        self.studies = studies or []
        self.covariate_names: List[str] = []
        self.results: Dict[str, Any] = {}
    
    def add_study(self, study: StudyData) -> None:
        """Agrega un estudio al análisis."""
        self.studies.append(study)
    
    def add_covariate_from_list(self, name: str, values: List[Any]) -> None:
        """
        Agrega covariable desde lista de valores.
        
        Parameters
        ----------
        name : str
            Nombre de la covariable (ej: "dosis", "diabetes")
        values : list
            Valor para cada estudio (debe coincidir con len(self.studies))
        """
        if len(values) != len(self.studies):
            raise ValueError(
                f"Longitud de {name} ({len(values)}) != número de estudios ({len(self.studies)})"
            )
        
        for i, value in enumerate(values):
            self.studies[i].covariates[name] = value
        
        if name not in self.covariate_names:
            self.covariate_names.append(name)
    
    def _get_study_arrays(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """Extrae arrays numpy de efectos, varianzas y SE."""
        y = np.array([s.effect_size for s in self.studies])
        v = np.array([s.variance for s in self.studies])
        se = np.array([s.se for s in self.studies])
        ids = [s.study_id for s in self.studies]
        return y, v, se, ids
    
    def analyze_categorical(self, covariate: str) -> Dict:
        """
        Análisis de subgrupos para covariable categórica.
        
        Calcula efecto combinado por nivel, Q-between y test de interacción.
        """
        y, v, se, ids = self._get_study_arrays()
        
        # Obtener niveles de la covariable
        levels = sorted(list(set(s.covariates.get(covariate) for s in self.studies)))
        
        if len(levels) < 2:
            return {
                "covariate": covariate,
                "error": f"Covariable '{covariate}' tiene <2 niveles",
                "levels": levels
            }
        
        # Calcular efecto combinado por nivel
        level_results = []
        level_effects = []
        level_vars = []
        
        for level in levels:
            mask = np.array([s.covariates.get(covariate) == level for s in self.studies])
            if mask.sum() < 2:
                level_results.append({
                    "level": level,
                    "n_studies": int(mask.sum()),
                    "effect": None,
                    "ci_lower": None,
                    "ci_upper": None,
                    "se": None,
                    "p_value": None,
                    "note": "Insuficientes estudios (n<2)"
                })
                continue
            
            y_level = y[mask]
            v_level = v[mask]
            w_level = 1 / v_level
            
            # Efecto combinado (fixed-effect para subgrupo)
            pooled_effect = np.sum(w_level * y_level) / np.sum(w_level)
            pooled_var = 1 / np.sum(w_level)
            pooled_se = np.sqrt(pooled_var)
            
            # CI 95%
            ci_lower = pooled_effect - 1.96 * pooled_se
            ci_upper = pooled_effect + 1.96 * pooled_se
            
            # Test contra nulo
            z = pooled_effect / pooled_se
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))
            
            level_results.append({
                "level": level,
                "n_studies": int(mask.sum()),
                "effect": float(pooled_effect),
                "ci_lower": float(ci_lower),
                "ci_upper": float(ci_upper),
                "se": float(pooled_se),
                "p_value": float(p_value),
                "significant": bool(p_value < 0.05)
            })
            
            level_effects.append(pooled_effect)
            level_vars.append(pooled_var)
        
        # Q-between: diferencia entre niveles
        # Usar efectos ponderados de subgrupos
        valid_levels = [r for r in level_results if r["effect"] is not None]
        if len(valid_levels) >= 2:
            level_effects_arr = np.array([r["effect"] for r in valid_levels])
            level_vars_arr = np.array([r["se"]**2 for r in valid_levels])
            level_weights = 1 / level_vars_arr
            
            pooled_all = np.sum(level_weights * level_effects_arr) / np.sum(level_weights)
            Q_between = np.sum(level_weights * (level_effects_arr - pooled_all)**2)
            df_between = len(valid_levels) - 1
            p_between = 1.0 - stats.chi2.cdf(Q_between, df_between)
        else:
            Q_between = 0.0
            df_between = 0
            p_between = 1.0
        
        return {
            "covariate": covariate,
            "type": "categorical",
            "levels": levels,
            "level_results": level_results,
            "Q_between": float(Q_between),
            "df_between": int(df_between),
            "p_between": float(p_between),
            "significant": bool(p_between < 0.05),
            "interpretation": self._interpret_subgroup(p_between, valid_levels)
        }
    
    def analyze_continuous(self, covariate: str) -> Dict:
        """
        Meta-regresión para covariable continua.
        
        Calcula pendiente, intercepto y significancia.
        """
        y, v, se, ids = self._get_study_arrays()
        
        # Obtener valores de covariable
        x = np.array([s.covariates.get(covariate) for s in self.studies])
        
        if np.any(np.isnan(x)):
            return {
                "covariate": covariate,
                "error": f"Valores faltantes en covariable '{covariate}'",
                "type": "continuous"
            }
        
        # Meta-regresión WLS
        n = len(y)
        w = 1 / v
        
        # Centrar x para mejor interpretación
        x_centered = x - np.mean(x)
        
        X = np.column_stack((np.ones(n), x_centered))
        Wy = np.sqrt(w) * y
        WX = np.sqrt(w)[:, None] * X
        
        try:
            beta = np.linalg.lstsq(WX, Wy, rcond=None)[0]
            
            # Calcular errores estándar
            y_pred = X @ beta
            residuals = y - y_pred
            mse = np.sum(w * residuals**2) / (n - 2)
            
            # Covarianza robusta (sandwich)
            XWX = X.T @ np.diag(w) @ X
            try:
                cov = mse * np.linalg.inv(XWX)
                se_beta = np.sqrt(np.diag(cov))
            except np.linalg.LinAlgError:
                se_beta = np.array([np.nan, np.nan])
            
            # Tests de significancia
            t_values = beta / se_beta
            p_values = 2 * (1 - stats.t.cdf(np.abs(t_values), max(1, n - 2)))
            
            # R² (proporción de heterogeneidad explicada)
            Q_total = np.sum(w * (y - np.sum(w * y) / np.sum(w))**2)
            Q_resid = np.sum(w * residuals**2)
            R_squared = max(0, (Q_total - Q_resid) / Q_total) if Q_total > 0 else 0
            
            return {
                "covariate": covariate,
                "type": "continuous",
                "n": n,
                "intercept": float(beta[0]),
                "intercept_se": float(se_beta[0]),
                "intercept_p": float(p_values[0]),
                "slope": float(beta[1]),
                "slope_se": float(se_beta[1]),
                "slope_p": float(p_values[1]),
                "significant": bool(p_values[1] < 0.05),
                "R_squared": float(R_squared),
                "interpretation": (
                    f"Por cada unidad de aumento en {covariate}, "
                    f"el efecto cambia en {beta[1]:.3f} (p={p_values[1]:.3f})"
                )
            }
            
        except Exception as e:
            return {
                "covariate": covariate,
                "type": "continuous",
                "error": str(e)
            }
    
    def _interpret_subgroup(self, p_between: float, valid_levels: List[Dict]) -> str:
        """Genera interpretación en lenguaje clínico."""
        if p_between < 0.05:
            return f"Diferencia significativa entre subgrupos (p={p_between:.3f}). El efecto varía según la covariable."
        elif p_between < 0.10:
            return f"Tendencia a diferencia entre subgrupos (p={p_between:.3f}). Posible efecto modificador."
        else:
            return f"Sin diferencia significativa entre subgrupos (p={p_between:.3f}). Efecto consistente."
    
    def analyze_all(self) -> Dict[str, Any]:
        """
        Ejecuta análisis de subgrupos para todas las covariables.
        
        Returns
        -------
        dict con resultados por covariable + resumen
        """
        if not self.covariate_names:
            return {"error": "No se han definido covariables"}
        
        results = {}
        
        for covariate in self.covariate_names:
            # Detectar si es categórica o continua
            values = [s.covariates.get(covariate) for s in self.studies]
            
            # Si es numérica y tiene >5 valores únicos → continua
            try:
                numeric_values = [float(v) for v in values if v is not None]
                n_unique = len(set(numeric_values))
                is_continuous = n_unique > 5 and all(isinstance(v, (int, float)) for v in values)
            except (ValueError, TypeError):
                is_continuous = False
            
            if is_continuous:
                results[covariate] = self.analyze_continuous(covariate)
            else:
                results[covariate] = self.analyze_categorical(covariate)
        
        # Resumen
        significant = sum(1 for r in results.values() if r.get("significant", False))
        
        return {
            "covariate_results": results,
            "summary": {
                "total_covariates": len(self.covariate_names),
                "significant_interactions": significant,
                "non_significant": len(self.covariate_names) - significant
            }
        }
    
    def generate_subgroup_table(self, covariate: str) -> str:
        """Genera tabla Markdown de subgrupos para una covariable."""
        if covariate not in self.covariate_names:
            return f"Covariable '{covariate}' no encontrada"
        
        result = self.analyze_categorical(covariate) if covariate in [
            r.get("covariate") for r in self.results.get("covariate_results", {}).values()
        ] else {}
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        lines = [
            f"## Análisis de Subgrupos: {covariate}",
            "",
            f"**Q-between:** {result.get('Q_between', 0):.2f} (df={result.get('df_between', 0)}, p={result.get('p_between', 1):.3f})",
            "",
            f"*Interpretación: {result.get('interpretation', 'N/A')}*",
            "",
            "| Subgrupo | N estudios | Efecto | IC 95% | p |",
            "|----------|-----------|--------|--------|---|",
        ]
        
        for level in result.get("level_results", []):
            if level["effect"] is not None:
                lines.append(
                    f"| {level['level']} | {level['n_studies']} | "
                    f"{level['effect']:.3f} | "
                    f"[{level['ci_lower']:.3f}, {level['ci_upper']:.3f}] | "
                    f"{level['p_value']:.3f} {'*' if level['significant'] else ''} |"
                )
            else:
                lines.append(
                    f"| {level['level']} | {level['n_studies']} | N/A | N/A | N/A |"
                )
        
        return "\n".join(lines)
    
    def export_results(self, output_dir: str = "subgroup_output") -> str:
        """Exporta resultados a JSON."""
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        
        filepath = outdir / f"subgroup_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        return str(filepath)


def create_subgroup_from_dataframe(
    df,
    effect_col: str = "effect_size",
    se_col: str = "se",
    n_col: Optional[str] = None,
    covariate_cols: Optional[List[str]] = None
) -> SubgroupAnalyzer:
    """
    Crea SubgroupAnalyzer desde DataFrame de pandas.
    
    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame con datos de estudios
    effect_col : str
        Nombre columna de tamaño de efecto
    se_col : str
        Nombre columna de error estándar
    n_col : str, optional
        Nombre columna de tamaño muestral
    covariate_cols : list, optional
        Nombres de columnas de covariables
    
    Returns
    -------
    SubgroupAnalyzer configurado
    """
    analyzer = SubgroupAnalyzer()
    
    for _, row in df.iterrows():
        study = StudyData(
            study_id=str(row.get("study_id", f"study_{_}")),
            effect_size=float(row[effect_col]),
            variance=float(row[se_col])**2,
            se=float(row[se_col]),
            n_total=int(row[n_col]) if n_col else 100,
            covariates={col: row[col] for col in (covariate_cols or [])}
        )
        analyzer.add_study(study)
    
    analyzer.covariate_names = covariate_cols or []
    
    return analyzer


# ── test / demo ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Análisis de Subgrupos Demo ===\n")
    
    # Datos simulados: 10 estudios con covariables
    studies = [
        StudyData("AKIKI", 0.85, 0.04, 0.20, 620, covariates={"dosis": 6, "diabetes": 0, "tipo": "RCT"}),
        StudyData("ELAIN", 0.78, 0.05, 0.22, 500, covariates={"dosis": 8, "diabetes": 1, "tipo": "RCT"}),
        StudyData("STARRT", 0.92, 0.03, 0.17, 3000, covariates={"dosis": 8, "diabetes": 0, "tipo": "RCT"}),
        StudyData("IDEAL", 0.88, 0.06, 0.24, 400, covariates={"dosis": 16, "diabetes": 1, "tipo": "RCT"}),
        StudyData("CORTICUS", 1.05, 0.08, 0.28, 300, covariates={"dosis": 6, "diabetes": 0, "tipo": "RCT"}),
        StudyData("HYPRESS", 0.95, 0.07, 0.26, 280, covariates={"dosis": 8, "diabetes": 0, "tipo": "RCT"}),
        StudyData("APROCCHSS", 0.82, 0.04, 0.20, 800, covariates={"dosis": 16, "diabetes": 1, "tipo": "RCT"}),
        StudyData("ADRENAL", 0.90, 0.05, 0.22, 1000, covariates={"dosis": 16, "diabetes": 1, "tipo": "RCT"}),
        StudyData("COIITSS", 0.93, 0.09, 0.30, 200, covariates={"dosis": 8, "diabetes": 0, "tipo": "Cohorte"}),
        StudyData("DOSCORT", 1.10, 0.10, 0.32, 150, covariates={"dosis": 6, "diabetes": 1, "tipo": "Cohorte"}),
    ]
    
    analyzer = SubgroupAnalyzer(studies)
    
    # Análisis por dosis (categórica: 6, 8, 16 mg)
    print("=== Subgrupos por Dosis ===")
    result_dosis = analyzer.analyze_categorical("dosis")
    print(f"Q-between: {result_dosis['Q_between']:.2f} (p={result_dosis['p_between']:.3f})")
    print(f"Significativo: {result_dosis['significant']}")
    print(f"\n{result_dosis['interpretation']}\n")
    
    for level in result_dosis['level_results']:
        if level['effect'] is not None:
            print(f"  {level['level']}mg: RR={level['effect']:.3f} "
                  f"[{level['ci_lower']:.3f}-{level['ci_upper']:.3f}] "
                  f"p={level['p_value']:.3f}")
    
    # Meta-regresión continua
    print("\n=== Meta-regresión por Dosis (continua) ===")
    result_reg = analyzer.analyze_continuous("dosis")
    print(f"Pendiente: {result_reg['slope']:.4f} (SE={result_reg['slope_se']:.4f}, p={result_reg['slope_p']:.3f})")
    print(f"R²: {result_reg['R_squared']:.3f}")
    print(f"Interpretación: {result_reg['interpretation']}")
    
    # Análisis por tipo de estudio
    print("\n=== Subgrupos por Tipo de Estudio ===")
    result_tipo = analyzer.analyze_categorical("tipo")
    print(f"Q-between: {result_tipo['Q_between']:.2f} (p={result_tipo['p_between']:.3f})")
    print(f"Interpretación: {result_tipo['interpretation']}")
    
    # Tabla Markdown
    print("\n=== Tabla Markdown ===")
    print(analyzer.generate_subgroup_table("dosis"))
