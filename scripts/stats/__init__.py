"""
Martyr v5.1 — Modulo estadistico de meta-analisis en Python puro.
"""

from .pooling import PoolingEngine, StudyData, MetaAnalysisResult, cochrans_q
from .effects import (
    or_to_rr, rr_to_or, rr_to_rd,
    var_logrr_from_ci, var_logor_from_ci,
    var_logrr_from_events, var_logor_from_events,
    cohens_d_from_means, hedges_g,
    rr_to_log_scale, or_to_log_scale,
    back_transform_log, back_transform_log_ci,
    compute_effect_from_2x2,
)
from .heterogeneity import (
    interpret_i2, compute_het_stats,
    compute_prediction_interval, compute_q_between,
)
from .publication_bias import (
    egger_test, pet_peese, trim_and_fill,
    fail_safe_n_rosenthal, comprehensive_bias_assessment,
)
from .subgroup import (
    meta_regression, subgroup_analysis, interaction_test,
)

__all__ = [
    "PoolingEngine", "StudyData", "MetaAnalysisResult", "cochrans_q",
    "or_to_rr", "rr_to_or", "rr_to_rd",
    "var_logrr_from_ci", "var_logor_from_ci",
    "var_logrr_from_events", "var_logor_from_events",
    "cohens_d_from_means", "hedges_g",
    "rr_to_log_scale", "or_to_log_scale",
    "back_transform_log", "back_transform_log_ci",
    "compute_effect_from_2x2",
    "interpret_i2", "compute_het_stats",
    "compute_prediction_interval", "compute_q_between",
    "egger_test", "pet_peese", "trim_and_fill",
    "fail_safe_n_rosenthal", "comprehensive_bias_assessment",
    "meta_regression", "subgroup_analysis", "interaction_test",
]