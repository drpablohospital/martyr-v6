#!/usr/bin/env python3
"""
Martyr v5.0 — Conversión de Medidas de Efecto
================================================
Funciones para convertir entre OR, RR, RD, Cohen's d, Hedges' g,
y calcular varianzas desde CI, SE, o datos brutos (n+events).
"""

from __future__ import annotations

import math
from typing import Optional, Tuple


# ── conversiones básicas ──────────────────────────────────────
def or_to_rr(or_val: float, p_c: float) -> float:
    """Convierte OR a RR dado la proporción del grupo control.
    Formula: RR = OR / (1 - p_c + p_c * OR)
    """
    if p_c <= 0 or p_c >= 1:
        return or_val  # No se puede convertir
    return or_val / (1.0 - p_c + p_c * or_val)


def rr_to_or(rr_val: float, p_c: float) -> float:
    """Convierte RR a OR dado la proporción del grupo control."""
    if p_c <= 0 or p_c >= 1:
        return rr_val
    p_i = p_c * rr_val
    return (p_i / (1.0 - p_i)) / (p_c / (1.0 - p_c))


def rr_to_rd(rr_val: float, p_c: float) -> float:
    """Convierte RR a Risk Difference: RD = p_c * (RR - 1)."""
    return p_c * (rr_val - 1.0)


# ── cálculo de varianzas ──────────────────────────────────────
def var_logrr_from_ci(rr: float, ci_lower: float, ci_upper: float) -> float:
    """Estima varianza de log(RR) desde IC 95%.
    SE = (log(upper) - log(lower)) / 3.92
    var = SE²
    """
    se = (math.log(ci_upper) - math.log(ci_lower)) / 3.92
    return se ** 2


def var_logor_from_ci(or_val: float, ci_lower: float, ci_upper: float) -> float:
    """Estima varianza de log(OR) desde IC 95%."""
    return var_logrr_from_ci(or_val, ci_lower, ci_upper)


def var_logrr_from_events(n_i: int, n_c: int, events_i: int, events_c: int) -> float:
    """Varianza exacta de log(RR) desde tabla 2×2.
    Formula: 1/a - 1/n_i + 1/c - 1/n_c donde a=events_i, c=events_c
    Con corrección de continuidad para eventos cero.
    """
    a = max(events_i, 0.5)  # Corrección de continuidad
    c = max(events_c, 0.5)
    return (1.0 / a - 1.0 / n_i) + (1.0 / c - 1.0 / n_c)


def var_logor_from_events(n_i: int, n_c: int, events_i: int, events_c: int) -> float:
    """Varianza exacta de log(OR) desde tabla 2×2.
    Formula: 1/a + 1/b + 1/c + 1/d donde a=events_i, b=n_i-events_i, etc.
    """
    a = max(events_i, 0.5)
    b = max(n_i - events_i, 0.5)
    c = max(events_c, 0.5)
    d = max(n_c - events_c, 0.5)
    return 1.0 / a + 1.0 / b + 1.0 / c + 1.0 / d


def cohens_d_from_means(m1: float, m2: float, sd1: float, sd2: float,
                        n1: int, n2: int) -> Tuple[float, float]:
    """Cohen's d y su varianza desde medias y DE.
    Usa pooled SD.
    """
    pooled_sd = math.sqrt(((n1 - 1) * sd1**2 + (n2 - 1) * sd2**2) / (n1 + n2 - 2))
    d = (m1 - m2) / pooled_sd
    se = math.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
    return d, se ** 2


def hedges_g(d: float, n: int) -> float:
    """Corrige Cohen's d a Hedges' g.
    J = 1 - 3/(4n - 9)
    """
    if n < 4:
        return d
    J = 1.0 - 3.0 / (4.0 * n - 9.0)
    return d * J


# ── funciones de conveniencia ─────────────────────────────────
def rr_to_log_scale(rr: float, ci_lower: float, ci_upper: float) -> Tuple[float, float]:
    """Convierte RR e IC a escala logarítmica.
    Returns: (logRR, var_logRR)
    """
    log_rr = math.log(rr)
    var_log = var_logrr_from_ci(rr, ci_lower, ci_upper)
    return log_rr, var_log


def or_to_log_scale(or_val: float, ci_lower: float, ci_upper: float) -> Tuple[float, float]:
    """Convierte OR e IC a escala logarítmica.
    Returns: (logOR, var_logOR)
    """
    log_or = math.log(or_val)
    var_log = var_logor_from_ci(or_val, ci_lower, ci_upper)
    return log_or, var_log


def back_transform_log(value: float) -> float:
    """Convierte log(RR) o log(OR) de vuelta a escala original."""
    return math.exp(value)


def back_transform_log_ci(ci_lower: float, ci_upper: float) -> Tuple[float, float]:
    """Convierte IC en escala log a escala original."""
    return math.exp(ci_lower), math.exp(ci_upper)


# ── funciones específicas por tipo de estudio ─────────────────
def compute_effect_from_2x2(events_i: int, n_i: int, events_c: int, n_c: int,
                               measure: str = "RR") -> Tuple[float, float, float, float]:
    """Calcula medida de efecto y varianza desde tabla 2×2.
    
    Returns
    -------
    effect, ci_lower, ci_upper, variance
    """
    if measure.upper() == "RR":
        rr = (events_i / n_i) / (events_c / n_c)
        var = var_logrr_from_events(n_i, n_c, events_i, events_c)
        se = math.sqrt(var)
        log_rr = math.log(rr)
        ci_l, ci_u = math.exp(log_rr - 1.96 * se), math.exp(log_rr + 1.96 * se)
        return rr, ci_l, ci_u, var
    elif measure.upper() == "OR":
        or_val = (events_i * (n_c - events_c)) / (events_c * (n_i - events_i))
        var = var_logor_from_events(n_i, n_c, events_i, events_c)
        se = math.sqrt(var)
        log_or = math.log(or_val)
        ci_l, ci_u = math.exp(log_or - 1.96 * se), math.exp(log_or + 1.96 * se)
        return or_val, ci_l, ci_u, var
    elif measure.upper() == "RD":
        rd = (events_i / n_i) - (events_c / n_c)
        var = (events_i * (n_i - events_i)) / (n_i**3) + (events_c * (n_c - events_c)) / (n_c**3)
        se = math.sqrt(var)
        ci_l, ci_u = rd - 1.96 * se, rd + 1.96 * se
        return rd, ci_l, ci_u, var
    else:
        raise ValueError(f"Medida no soportada: {measure}")


# ── demo ──────────────────────────────────────────────────────
if __name__ == "__main__":
    # Demo: AKIKI 2016
    # early RRT: 150/311, late RRT: 153/308
    rr, ci_l, ci_u, var = compute_effect_from_2x2(150, 311, 153, 308, "RR")
    print(f"AKIKI 2016: RR={rr:.2f} [{ci_l:.2f}-{ci_u:.2f}], var(logRR)={var:.4f}")
    
    # ELAIN 2016
    rr, ci_l, ci_u, var = compute_effect_from_2x2(44, 112, 65, 119, "RR")
    print(f"ELAIN 2016: RR={rr:.2f} [{ci_l:.2f}-{ci_u:.2f}], var(logRR)={var:.4f}")
