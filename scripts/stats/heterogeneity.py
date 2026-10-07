#!/usr/bin/env python3
"""
Martyr v5.0 — Análisis de Heterogeneidad
=========================================
I², τ², Q, H, intervalos de predicción, e interpretación clínica.
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from typing import Tuple, Dict, List


def interpret_i2(i2: float) -> str:
    """Interpretación clínica de I² según Higgins et al."""
    if i2 <= 25:
        return "Baja heterogeneidad (0-25%)"
    elif i2 <= 50:
        return "Moderada heterogeneidad (25-50%)"
    elif i2 <= 75:
        return "Alta heterogeneidad (50-75%)"
    else:
        return "Muy alta heterogeneidad (75%+)"


def compute_het_stats(y: np.ndarray, v: np.ndarray, pooled: float) -> Dict:
    """Calcula todas las estadísticas de heterogeneidad.
    
    Returns
    -------
    dict con Q, df, p_Q, I2, H, tau2_DL
    """
    w = 1.0 / v
    Q = np.sum(w * (y - pooled) ** 2)
    df = len(y) - 1
    p_Q = 1.0 - stats.chi2.cdf(Q, df) if df > 0 else 1.0
    I2 = max(0.0, (Q - df) / Q * 100.0) if Q > 0 else 0.0
    H = np.sqrt(Q / df) if df > 0 else 1.0
    
    # DerSimonian-Laird tau²
    C = np.sum(w) - np.sum(w**2) / np.sum(w)
    tau2_DL = max(0.0, (Q - df) / C) if C > 0 else 0.0
    
    return {
        "Q": float(Q),
        "df": df,
        "p_Q": float(p_Q),
        "I2": float(I2),
        "H": float(H),
        "tau2_DL": float(tau2_DL),
        "interpretation": interpret_i2(float(I2)),
    }


def compute_prediction_interval(pooled: float, se: float, tau2: float) -> Tuple[float, float]:
    """Calcula 95% prediction interval.
    PI = pooled_effect ± 1.96 * sqrt(se² + tau²)
    """
    pi_se = np.sqrt(se**2 + tau2)
    return float(pooled - 1.96 * pi_se), float(pooled + 1.96 * pi_se)


def compute_q_between(y: np.ndarray, v: np.ndarray, subgroups: List[str]) -> Dict:
    """Q-between para análisis de subgrupos.
    
    Parameters
    ----------
    y : array de efectos
    v : array de varianzas
    subgroups : lista de etiquetas de subgrupo
    
    Returns
    -------
    dict con Q_between, df, p_value, I2_within, I2_between
    """
    unique_groups = list(set(subgroups))
    k = len(y)
    
    # Q total (con modelo de efectos fijos)
    w = 1.0 / v
    pooled_total = np.sum(w * y) / np.sum(w)
    Q_total = np.sum(w * (y - pooled_total) ** 2)
    
    # Q within (suma de Q dentro de cada subgrupo)
    Q_within = 0.0
    df_within = 0
    for g in unique_groups:
        mask = np.array([s == g for s in subgroups])
        if mask.sum() < 2:
            continue
        y_g = y[mask]
        v_g = v[mask]
        w_g = 1.0 / v_g
        pooled_g = np.sum(w_g * y_g) / np.sum(w_g)
        Q_g = np.sum(w_g * (y_g - pooled_g) ** 2)
        Q_within += Q_g
        df_within += mask.sum() - 1
    
    # Q between
    Q_between = Q_total - Q_within
    df_between = len(unique_groups) - 1
    p_between = 1.0 - stats.chi2.cdf(Q_between, df_between) if df_between > 0 else 1.0
    
    return {
        "Q_between": float(Q_between),
        "df_between": df_between,
        "p_between": float(p_between),
        "Q_within": float(Q_within),
        "df_within": df_within,
        "Q_total": float(Q_total),
        "df_total": k - 1,
    }


if __name__ == "__main__":
    import math
    y = np.array([math.log(0.98), math.log(0.72), math.log(1.00), math.log(1.01)])
    v = np.array([0.0148, 0.0342, 0.0034, 0.0065])
    
    het = compute_het_stats(y, v, np.mean(y))
    print(f"I²: {het['I2']:.1f}% — {het['interpretation']}")
    print(f"τ² (DL): {het['tau2_DL']:.4f}")
    print(f"Q: {het['Q']:.2f} (p={het['p_Q']:.3f})")
