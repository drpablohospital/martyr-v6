#!/usr/bin/env python3
"""Martyr v5.1 - Sesgo de Publicacion"""
import numpy as np
from scipy import stats
import math

def egger_test(y, v):
    se = np.sqrt(v)
    se = np.where(se < 1e-10, 1e-10, se)
    y_std = y / se
    precision = 1 / se
    n = len(y)
    mean_x = np.mean(precision)
    mean_y = np.mean(y_std)
    slope = np.sum((precision - mean_x) * (y_std - mean_y)) / np.sum((precision - mean_x) ** 2)
    intercept = mean_y - slope * mean_x
    residuals = y_std - (intercept + slope * precision)
    mse = np.sum(residuals ** 2) / (n - 2)
    se_intercept = math.sqrt(mse * (1 / n + mean_x ** 2 / np.sum((precision - mean_x) ** 2)))
    t_stat = intercept / se_intercept
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
    return {"method": "Egger", "intercept": float(intercept), "p_value": float(p_value), "significant": p_value < 0.10}

def pet_peese(y, v):
    se = np.sqrt(v)
    n = len(y)
    mean_se = np.mean(se)
    mean_y = np.mean(y)
    slope_pet = np.sum((se - mean_se) * (y - mean_y)) / np.sum((se - mean_se) ** 2)
    intercept_pet = mean_y - slope_pet * mean_se
    residuals_pet = y - (intercept_pet + slope_pet * se)
    mse_pet = np.sum(residuals_pet ** 2) / (n - 2)
    se_intercept_pet = math.sqrt(mse_pet * (1 / n + mean_se ** 2 / np.sum((se - mean_se) ** 2)))
    t_pet = intercept_pet / se_intercept_pet
    p_pet = 2 * (1 - stats.t.cdf(abs(t_pet), n - 2))
    se2 = se ** 2
    mean_se2 = np.mean(se2)
    slope_peese = np.sum((se2 - mean_se2) * (y - mean_y)) / np.sum((se2 - mean_se2) ** 2)
    intercept_peese = mean_y - slope_peese * mean_se2
    return {"method": "PET-PEESE", "PET_intercept": float(intercept_pet), "PET_p_value": float(p_pet), "PEESE_intercept": float(intercept_peese)}

def trim_and_fill(y, v, side="auto"):
    median_effect = np.median(y)
    left = np.sum(y < median_effect)
    right = np.sum(y > median_effect)
    if side == "auto":
        side = "left" if right > left else "right"
    n_missing = abs(right - left)
    w = 1 / v
    original_pooled = np.sum(w * y) / np.sum(w)
    return {"method": "Trim-and-fill", "n_missing": int(n_missing), "original": float(original_pooled)}

def fail_safe_n_rosenthal(y, v, target_p=0.05):
    n = len(y)
    w = 1 / v
    pooled = np.sum(w * y) / np.sum(w)
    se = np.sqrt(1 / np.sum(w))
    z = pooled / se
    z_target = stats.norm.ppf(1 - target_p)
    if abs(z) > z_target:
        n_additional = int((abs(z) - z_target) ** 2)
        n_fail_safe = n + n_additional
    else:
        n_fail_safe = 0
    return {"method": "Rosenthal", "fail_safe_n": n_fail_safe, "n_original": n}

def comprehensive_bias_assessment(y, v):
    return {"egger": egger_test(y, v), "pet_peese": pet_peese(y, v),
            "trim_fill": trim_and_fill(y, v), "fail_safe_n": fail_safe_n_rosenthal(y, v)}