#!/usr/bin/env python3
"""
Martyr v5.0 — Motor de Pooling Meta-Analítico en Python Puro
===============================================================
Sin R. Sin metafor. Solo scipy + numpy.

Métodos soportados:
  • FE: Fixed-effects (inverse variance)
  • DL: DerSimonian-Laird (default)
  • REML: Restricted Maximum Likelihood
  • HS: Hunter-Schmidt
  • SJ: Sidik-Jonkman
  • ML: Maximum Likelihood

Ejemplo:
    from stats.pooling import PoolingEngine, StudyData
    studies = [
        StudyData("AKIKI2016", "Gaudry", 2016, log(0.98), var_logrr(0.98, 0.83, 1.16), 311, 308),
        StudyData("ELAIN2016", "Zarbock", 2016, log(0.72), var_logrr(0.72, 0.55, 0.95), 112, 119),
    ]
    engine = PoolingEngine(method="DL")
    result = engine.fit(studies)
    print(f"Pooled RR: {exp(result.pooled_effect):.3f} [{exp(result.ci_lower):.3f}-{exp(result.ci_upper):.3f}]")
    print(f"I²: {result.I2:.1f}%")
"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

import numpy as np
from scipy import optimize, stats


# ── utilidades ────────────────────────────────────────────────
def _jnum(x: Optional[float]) -> Optional[float]:
    """Seguridad JSON: convierte NaN/Inf/None → None."""
    if x is None or not np.isfinite(x):
        return None
    return float(x)


def _jround(x: Optional[float], digits: int = 4) -> Optional[float]:
    """Redondeo seguro con preservación de None."""
    v = _jnum(x)
    return round(v, digits) if v is not None else None


# ── clases de datos ────────────────────────────────────────────
@dataclass
class StudyData:
    """Datos de un estudio individual."""
    study_id: str
    author: str
    year: int
    yi: float          # Efecto en escala transformada (logRR, logOR, Cohen's d)
    vi: float          # Varianza del efecto
    n_i: Optional[int] = None   # Grupo intervención
    n_c: Optional[int] = None   # Grupo control
    subgroup: Optional[str] = None
    events_i: Optional[int] = None
    events_c: Optional[int] = None
    effect_measure: str = "RR"   # RR, OR, RD, MD, SMD, g


@dataclass
class MetaAnalysisResult:
    """Resultado completo de meta-análisis."""
    k: int = 0
    model: str = ""
    
    # Efecto agrupado
    pooled_effect: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    se: float = 0.0
    z_value: float = 0.0
    p_value: float = 0.0
    
    # Heterogeneidad
    Q: float = 0.0
    df_Q: int = 0
    p_Q: float = 0.0
    I2: float = 0.0
    tau2: float = 0.0
    H: float = 0.0
    pi_lower: float = 0.0
    pi_upper: float = 0.0
    
    # Por estudio
    weights: np.ndarray = field(default_factory=lambda: np.array([]))
    study_effects: List[StudyData] = field(default_factory=list)
    
    # Flags de auditoría
    flags: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Exporta resultado como dict JSON-safe."""
        return {
            "k": self.k,
            "model": self.model,
            "pooled_effect": _jround(self.pooled_effect),
            "ci_95": [_jround(self.ci_lower), _jround(self.ci_upper)],
            "se": _jround(self.se),
            "z_value": _jround(self.z_value),
            "p_value": _jround(self.p_value),
            "heterogeneity": {
                "Q": _jround(self.Q),
                "df": self.df_Q,
                "p_Q": _jround(self.p_Q),
                "I2": _jround(self.I2),
                "tau2": _jround(self.tau2),
                "H": _jround(self.H),
                "prediction_interval_95": [_jround(self.pi_lower), _jround(self.pi_upper)],
            },
            "weights": {s.study_id: _jround(w) for s, w in zip(self.study_effects, self.weights)},
            "flags": self.flags,
        }


# ── motor principal ────────────────────────────────────────────
class PoolingEngine:
    """Motor de pooling meta-analítico: FE + RE (5 estimadores de τ²)."""
    
    METHODS = {"FE", "DL", "REML", "HS", "SJ", "ML"}
    
    def __init__(self, method: Literal["FE", "DL", "REML", "HS", "SJ", "ML"] = "DL"):
        if method not in self.METHODS:
            raise ValueError(f"Método '{method}' no soportado. Use: {self.METHODS}")
        self.method = method
        self.result = MetaAnalysisResult()
    
    def fit(self, studies: List[StudyData]) -> MetaAnalysisResult:
        """Ajusta modelo meta-analítico.
        
        Parameters
        ----------
        studies : list[StudyData]
            Lista de estudios con yi (efecto) y vi (varianza).
        
        Returns
        -------
        MetaAnalysisResult
            Resultado completo con flags de auditoría.
        """
        if len(studies) < 2:
            raise ValueError("Se requieren al menos 2 estudios para meta-análisis.")
        
        self.result.k = len(studies)
        self.result.study_effects = studies
        
        if self.method == "FE":
            return self._fit_fixed_effects(studies)
        else:
            return self._fit_random_effects(studies, self.method)
    
    # ── efectos fijos ─────────────────────────────────────────
    def _fit_fixed_effects(self, studies: List[StudyData]) -> MetaAnalysisResult:
        y = np.array([s.yi for s in studies])
        v = np.array([s.vi for s in studies])
        w = 1.0 / v
        
        pooled = np.sum(w * y) / np.sum(w)
        se = np.sqrt(1.0 / np.sum(w))
        ci_lower, ci_upper = pooled - 1.96 * se, pooled + 1.96 * se
        z = pooled / se
        p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
        
        # Q (diagnóstico en FE)
        Q, df, p_Q = cochrans_q(y, v)
        I2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0
        
        self.result.model = "FE"
        self.result.pooled_effect = float(pooled)
        self.result.ci_lower = float(ci_lower)
        self.result.ci_upper = float(ci_upper)
        self.result.se = float(se)
        self.result.z_value = float(z)
        self.result.p_value = float(p)
        self.result.Q = float(Q)
        self.result.df_Q = df
        self.result.p_Q = float(p_Q)
        self.result.I2 = float(I2)
        self.result.tau2 = 0.0
        self.result.weights = (w / np.sum(w)) * 100.0
        
        self._generate_flags()
        return self.result
    
    # ── efectos aleatorios ────────────────────────────────────
    def _fit_random_effects(self, studies: List[StudyData],
                            method: str) -> MetaAnalysisResult:
        y = np.array([s.yi for s in studies])
        v = np.array([s.vi for s in studies])
        k = len(studies)
        
        # 1. Estimar τ²
        tau2 = self._estimate_tau2(y, v, method)
        
        # 2. Pesos con varianza total
        w = 1.0 / (v + tau2)
        
        # 3. Efecto agrupado
        pooled = np.sum(w * y) / np.sum(w)
        se = np.sqrt(1.0 / np.sum(w))
        ci_lower, ci_upper = pooled - 1.96 * se, pooled + 1.96 * se
        z = pooled / se
        p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
        
        # 4. Heterogeneidad (Q con pesos FE)
        w_fe = 1.0 / v
        pooled_fe = np.sum(w_fe * y) / np.sum(w_fe)
        Q = np.sum(w_fe * (y - pooled_fe) ** 2)
        df = max(0, k - 1)
        p_Q = 1.0 - stats.chi2.cdf(Q, df) if df > 0 else 1.0
        I2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0
        H = np.sqrt(Q / df) if df > 0 else 1.0
        
        # 5. Prediction interval (Higgins et al.)
        pi_se = np.sqrt(se**2 + tau2)
        pi_lower = pooled - 1.96 * pi_se
        pi_upper = pooled + 1.96 * pi_se
        
        # Guardar
        self.result.model = f"RE-{method}"
        self.result.pooled_effect = float(pooled)
        self.result.ci_lower = float(ci_lower)
        self.result.ci_upper = float(ci_upper)
        self.result.se = float(se)
        self.result.z_value = float(z)
        self.result.p_value = float(p)
        self.result.Q = float(Q)
        self.result.df_Q = df
        self.result.p_Q = float(p_Q)
        self.result.I2 = float(I2)
        self.result.tau2 = float(tau2)
        self.result.H = float(H)
        self.result.pi_lower = float(pi_lower)
        self.result.pi_upper = float(pi_upper)
        self.result.weights = (w / np.sum(w)) * 100.0
        
        self._generate_flags()
        return self.result
    
    # ── estimadores de τ² ─────────────────────────────────────
    def _estimate_tau2(self, y: np.ndarray, v: np.ndarray, method: str) -> float:
        k = len(y)
        w_fe = 1.0 / v
        pooled_fe = np.sum(w_fe * y) / np.sum(w_fe)
        Q = np.sum(w_fe * (y - pooled_fe) ** 2)
        df = max(0, k - 1)
        
        if method == "DL":  # DerSimonian-Laird (default)
            C = np.sum(w_fe) - np.sum(w_fe**2) / np.sum(w_fe)
            tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
        elif method == "HS":  # Hunter-Schmidt
            tau2 = max(0.0, np.var(y, ddof=1) - np.mean(v))
        elif method == "SJ":  # Sidik-Jonkman
            Q_p = Q / df if df > 0 else Q
            tau2 = max(0.0, Q_p * np.mean(v) - np.mean(v))
        elif method in ("ML", "REML"):
            tau2 = self._estimate_tau2_ml(y, v, method == "REML")
        else:
            raise ValueError(f"Método desconocido: {method}")
        
        return float(tau2)
    
    def _estimate_tau2_ml(self, y: np.ndarray, v: np.ndarray, reml: bool = False) -> float:
        """ML/REML via optimización escalar."""
        def neg_ll(tau2: float) -> float:
            if tau2 < 0:
                return 1e10
            w = 1.0 / (v + tau2)
            pooled = np.sum(w * y) / np.sum(w)
            residuals = (y - pooled) ** 2
            ll = 0.5 * np.sum(np.log(v + tau2) + residuals / (v + tau2))
            if reml:
                ll += 0.5 * np.log(np.sum(w))
            return ll
        
        result = optimize.minimize_scalar(neg_ll, bounds=(0.0, 10.0), method="bounded")
        return max(0.0, float(result.x))
    
    # ── flags de auditoría ────────────────────────────────────
    def _generate_flags(self) -> None:
        r = self.result
        
        # I² crítico (>90%)
        if r.I2 > 90:
            r.flags.append({
                "id": "I2_CRITICAL",
                "level": "red",
                "value": _jround(r.I2),
                "rule": "I² > 90%",
                "action": "NO reportar pooled effect como definitivo; explorar subgrupos; reconsiderar si MA es apropiado",
            })
        elif r.I2 > 75:
            r.flags.append({
                "id": "I2_HIGH",
                "level": "yellow",
                "value": _jround(r.I2),
                "rule": "I² > 75%",
                "action": "Reportar subgrupos y sensibilidad; usar REML o RVE",
            })
        elif r.I2 > 50:
            r.flags.append({
                "id": "I2_MODERATE",
                "level": "yellow",
                "value": _jround(r.I2),
                "rule": "I² > 50%",
                "action": "Reportar junto con resultados; explorar moderadores",
            })
        
        # Dominancia de peso (>30%)
        if len(r.weights) > 0:
            max_weight = float(np.max(r.weights))
            if max_weight > 30:
                max_idx = int(np.argmax(r.weights))
                max_study = r.study_effects[max_idx].study_id if max_idx < len(r.study_effects) else "?"
                r.flags.append({
                    "id": "WEIGHT_DOMINANCE",
                    "level": "yellow",
                    "value": _jround(max_weight),
                    "rule": "Un estudio > 30% del peso",
                    "action": f"Verificar sensibilidad sin {max_study}; reportar como limitación",
                })
        
        # Prediction interval cruza nulo
        if r.pi_lower is not None and r.pi_upper is not None:
            # Para escala log: nulo = 0. Para escala nativa: depende
            if r.pi_lower < 0 and r.pi_upper > 0:
                r.flags.append({
                    "id": "PI_CROSSES_NULL",
                    "level": "yellow",
                    "value": f"{_jround(r.pi_lower)} to {_jround(r.pi_upper)}",
                    "rule": "95% PI cruza valor nulo",
                    "action": "Reportar PI explícitamente; el efecto no es generalizable",
                })
        
        # Tau² grande
        if r.tau2 > 0.1:
            r.flags.append({
                "id": "TAU2_LARGE",
                "level": "yellow",
                "value": _jround(r.tau2),
                "rule": "τ² > 0.1",
                "action": "Considerar si los estudios miden el mismo constructo",
            })
        
        # No significante pero con lenguaje fuerte (placeholder para capa superior)
        if r.p_value > 0.05 and r.p_value < 0.10:
            r.flags.append({
                "id": "TREND_ONLY",
                "level": "yellow",
                "value": _jround(r.p_value),
                "rule": "0.05 < p < 0.10",
                "action": "Reportar como tendencia, no como significativo; evitar lenguaje fuerte",
            })


# ── función standalone ───────────────────────────────────────
def cochrans_q(y: np.ndarray, v: np.ndarray) -> Tuple[float, int, float]:
    """Test Q de Cochran para heterogeneidad.
    
    Returns
    -------
    Q : float
        Estadístico Q
    df : int
        Grados de libertad
    p : float
        Valor p asociado
    """
    w = 1.0 / v
    pooled = np.sum(w * y) / np.sum(w)
    Q = np.sum(w * (y - pooled) ** 2)
    df = len(y) - 1
    p = 1.0 - stats.chi2.cdf(Q, df) if df > 0 else 1.0
    return float(Q), max(0, df), float(p)


# ── demo ───────────────────────────────────────────────────────
if __name__ == "__main__":
    # Datos: Timing of RRT in AKI (4 RCTs seminales)
    # logRR y varianza calculados desde RR e IC 95%
    studies = [
        StudyData("AKIKI2016", "Gaudry", 2016, math.log(0.98), 0.0148, 311, 308, events_i=150, events_c=153),
        StudyData("ELAIN2016", "Zarbock", 2016, math.log(0.72), 0.0342, 112, 119, events_i=44, events_c=65),
        StudyData("STARRT2019", "STARRT-AKI", 2019, math.log(1.00), 0.0034, 1465, 1462, events_i=643, events_c=639),
        StudyData("IDEAL2020", "IDEAL-ICU", 2020, math.log(1.01), 0.0065, 488, 492, events_i=239, events_c=238),
    ]
    
    engine = PoolingEngine(method="DL")
    result = engine.fit(studies)
    
    print("=" * 60)
    print("DEMO: Timing of RRT in AKI — 4 RCTs")
    print("=" * 60)
    print(f"Modelo: {result.model}")
    print(f"Estudios: {result.k}")
    print(f"Pooled RR: {math.exp(result.pooled_effect):.3f} "
          f"[{math.exp(result.ci_lower):.3f}-{math.exp(result.ci_upper):.3f}]")
    print(f"p-value: {result.p_value:.4f}")
    print(f"I²: {result.I2:.1f}%")
    print(f"τ²: {result.tau2:.4f}")
    print(f"Q: {result.Q:.2f} (df={result.df_Q}, p={result.p_Q:.4f})")
    print(f"95% Prediction Interval: {math.exp(result.pi_lower):.3f}-{math.exp(result.pi_upper):.3f}")
    print("\nFlags:")
    for flag in result.flags:
        print(f"  [{flag['level'].upper()}] {flag['id']}: {flag['action']}")
    print("\nJSON export:")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
