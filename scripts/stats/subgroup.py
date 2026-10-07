#!/usr/bin/env python3
"""Martyr v5.1 - Analisis de Subgrupos y Metaregresion"""
import numpy as np
from scipy import stats
import math

def meta_regression(y, v, moderator):
    """Metaregresion simple con WLS."""
    n = len(y)
    w = 1 / v
    X = np.column_stack((np.ones(n), moderator))
    Wy = np.sqrt(w) * y
    WX = np.sqrt(w)[:, None] * X
    try:
        beta = np.linalg.lstsq(WX, Wy, rcond=None)[0]
        residuals = Wy - WX @ beta
        mse = np.sum(residuals**2) / (n - 2)
        cov = mse * np.linalg.inv(X.T @ np.diag(w) @ X)
        se_beta = np.sqrt(np.diag(cov))
        t = beta / se_beta
        p = 2 * (1 - stats.t.cdf(np.abs(t), n - 2))
        return {"intercept": float(beta[0]), "slope": float(beta[1]),
                "se_slope": float(se_beta[1]), "p_slope": float(p[1]),
                "significant": p[1] < 0.05}
    except:
        return {"intercept": 0.0, "slope": 0.0, "p_slope": 1.0, "significant": False}

def subgroup_analysis(y, v, subgroups):
    """Analisis de subgrupos con Q-between."""
    unique = list(set(subgroups))
    w = 1 / v
    pooled_total = np.sum(w * y) / np.sum(w)
    Q_total = np.sum(w * (y - pooled_total)**2)
    Q_within = 0.0
    for g in unique:
        mask = np.array([s == g for s in subgroups])
        if mask.sum() < 2:
            continue
        yg, vg = y[mask], v[mask]
        wg = 1 / vg
        pg = np.sum(wg * yg) / np.sum(wg)
        Q_within += np.sum(wg * (yg - pg)**2)
    Q_between = Q_total - Q_within
    df_between = len(unique) - 1
    p_between = 1.0 - stats.chi2.cdf(Q_between, df_between) if df_between > 0 else 1.0
    return {"Q_between": float(Q_between), "df_between": df_between,
            "p_between": float(p_between), "significant": p_between < 0.05}

def interaction_test(effects1, effects2):
    """Test de diferencia entre dos subgrupos."""
    m1, m2 = np.mean(effects1), np.mean(effects2)
    se1 = np.std(effects1, ddof=1) / np.sqrt(len(effects1))
    se2 = np.std(effects2, ddof=1) / np.sqrt(len(effects2))
    se_diff = np.sqrt(se1**2 + se2**2)
    if se_diff < 1e-10:
        return {"difference": 0.0, "p_value": 1.0, "significant": False}
    t = (m1 - m2) / se_diff
    df = len(effects1) + len(effects2) - 2
    p = 2 * (1 - stats.t.cdf(abs(t), max(1, df)))
    return {"difference": float(m1 - m2), "p_value": float(p), "significant": p < 0.05}