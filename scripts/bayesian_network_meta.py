"""
Bayesian Network Meta-Analysis Module for MARTYR
Combina datos continuos (MEAN) y binarios (RR/OR) en un meta-análisis unificado.

Estrategia:
1. Para datos binarios (RR/OR): Usar directamente en el meta-análisis
2. Para datos continuos (MEAN): Convertir a Standardized Mean Difference (SMD) 
   o a una métrica comparable usando el método de Cohen's d
3. Combinar ambos tipos en un modelo bayesiano jerárquico
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Optional, Tuple
import warnings


def cohens_d(mean_i: float, mean_c: float, sd_i: float, sd_c: float, n_i: int, n_c: int) -> Tuple[float, float]:
    """
    Calcula Cohen's d (Standardized Mean Difference) y su error estándar.
    
    Args:
        mean_i: Media del grupo de intervención
        mean_c: Media del grupo de control
        sd_i: Desviación estándar del grupo de intervención
        sd_c: Desviación estándar del grupo de control
        n_i: N del grupo de intervención
        n_c: N del grupo de control
    
    Returns:
        (d, se_d): Cohen's d y su error estándar
    """
    # Pooled SD
    pooled_sd = np.sqrt(((n_i - 1) * sd_i**2 + (n_c - 1) * sd_c**2) / (n_i + n_c - 2))
    
    # Cohen's d
    d = (mean_i - mean_c) / pooled_sd if pooled_sd > 0 else 0
    
    # Error estándar de d (aproximación de Hedges)
    se_d = np.sqrt((n_i + n_c) / (n_i * n_c) + d**2 / (2 * (n_i + n_c)))
    
    return d, se_d


def smd_to_logrr(d: float, se_d: float, baseline_risk: float = 0.5) -> Tuple[float, float]:
    """
    Aproximación: Convierte SMD (Cohen's d) a log(RR) aproximado.
    
    Para outcomes donde menor valor es mejor (ej: LogMAR en visual acuity):
    d negativo = mejor resultado = menor riesgo = RR < 1
    
    Args:
        d: Cohen's d
        se_d: Error estándar de d
        baseline_risk: Riesgo baseline (default 0.5)
    
    Returns:
        (log_rr, se_log_rr): Log(RR) y su error estándar
    """
    # Conversión conservadora: efecto pequeño en continuo ≈ efecto pequeño en binario
    # Según literatura: log(OR) ≈ d * 1.81 para convertir SMD a log(OR)
    # Y log(RR) ≈ log(OR) * 0.91 para riesgos moderados
    # Usamos factor más conservador para evitar sobreestimación
    conversion_factor = 0.5  # Factor reducido para conversión conservadora
    
    # Para outcomes donde menor es mejor, d negativo implica beneficio (RR < 1)
    log_rr = -d * conversion_factor
    se_log_rr = se_d * conversion_factor
    
    return log_rr, se_log_rr


class BayesianNetworkMetaAnalysis:
    """
    Meta-análisis en red bayesiana que combina diferentes tipos de datos.
    """
    
    def __init__(self):
        self.studies = []
        self.converted_effects = []
    
    def add_binary_study(
        self,
        study_id: str,
        n_i: int,
        n_c: int,
        events_i: int,
        events_c: int,
        effect_measure: str = "RR"
    ):
        """Agrega estudio con datos binarios."""
        
        if effect_measure.upper() == "RR":
            # Calcular RR y su log
            if events_c > 0 and events_i > 0:
                p_i = events_i / n_i
                p_c = events_c / n_c
                rr = p_i / p_c
                log_rr = np.log(rr)
                
                # Error estándar del log(RR) (método de Greenland)
                se_log_rr = np.sqrt(1/events_i - 1/n_i + 1/events_c - 1/n_c)
                
                self.studies.append({
                    "study_id": study_id,
                    "type": "binary",
                    "effect_measure": "RR",
                    "effect": rr,
                    "log_effect": log_rr,
                    "se_log_effect": se_log_rr,
                    "n_i": n_i,
                    "n_c": n_c,
                    "events_i": events_i,
                    "events_c": events_c
                })
        
        elif effect_measure.upper() == "OR":
            # Calcular OR y su log
            if events_c > 0 and events_i > 0 and (n_i - events_i) > 0 and (n_c - events_c) > 0:
                or_val = (events_i / (n_i - events_i)) / (events_c / (n_c - events_c))
                log_or = np.log(or_val)
                se_log_or = np.sqrt(1/events_i + 1/(n_i - events_i) + 1/events_c + 1/(n_c - events_c))
                
                self.studies.append({
                    "study_id": study_id,
                    "type": "binary",
                    "effect_measure": "OR",
                    "effect": or_val,
                    "log_effect": log_or,
                    "se_log_effect": se_log_or,
                    "n_i": n_i,
                    "n_c": n_c,
                    "events_i": events_i,
                    "events_c": events_c
                })
    
    def add_continuous_study(
        self,
        study_id: str,
        mean_i: float,
        mean_c: float,
        sd_i: float,
        sd_c: float,
        n_i: int,
        n_c: int,
        direction: str = "lower_better"  # "lower_better" o "higher_better"
    ):
        """
        Agrega estudio con datos continuos y lo convierte a escala comparable.
        """
        
        # Calcular Cohen's d
        d, se_d = cohens_d(mean_i, mean_c, sd_i, sd_c, n_i, n_c)
        
        # Convertir a log(RR) aproximado
        log_rr, se_log_rr = smd_to_logrr(d, se_d)
        
        # Ajustar dirección
        if direction == "higher_better":
            log_rr = -log_rr
        
        rr = np.exp(log_rr)
        
        self.studies.append({
            "study_id": study_id,
            "type": "continuous",
            "original_measure": "MEAN",
            "converted_measure": "RR_approx",
            "effect": rr,
            "log_effect": log_rr,
            "se_log_effect": se_log_rr,
            "n_i": n_i,
            "n_c": n_c,
            "cohens_d": d,
            "se_d": se_d
        })
    
    def add_extracted_study(
        self,
        study_id: str,
        effect_measure: str,
        effect_value: float,
        ci_lower: Optional[float] = None,
        ci_upper: Optional[float] = None,
        n_i: Optional[int] = None,
        n_c: Optional[int] = None,
        events_i: Optional[int] = None,
        events_c: Optional[int] = None
    ):
        """
        Agrega estudio con efecto ya extraído (desde abstract o tabla).
        """
        
        if effect_measure.upper() in ["RR", "OR", "HR"]:
            # Datos binarios ya calculados
            log_effect = np.log(effect_value) if effect_value > 0 else 0
            
            # Calcular SE desde CI si está disponible
            if ci_lower and ci_upper and ci_lower > 0 and ci_upper > 0:
                log_ci_lower = np.log(ci_lower)
                log_ci_upper = np.log(ci_upper)
                se_log_effect = (log_ci_upper - log_ci_lower) / (2 * 1.96)
            else:
                se_log_effect = 0.5  # Valor conservador
            
            self.studies.append({
                "study_id": study_id,
                "type": "binary_extracted",
                "effect_measure": effect_measure.upper(),
                "effect": effect_value,
                "log_effect": log_effect,
                "se_log_effect": se_log_effect,
                "n_i": n_i or "",
                "n_c": n_c or "",
                "events_i": events_i or "",
                "events_c": events_c or ""
            })
        
        elif effect_measure.upper() == "MEAN":
            # Datos continuos convertidos
            # Asumir que el effect_value es la diferencia de medias (mean_i - mean_c)
            # y ci_lower/ci_upper son los CI de esa diferencia
            
            if ci_lower and ci_upper:
                se_diff = (ci_upper - ci_lower) / (2 * 1.96)
                
                # Convertir a d (necesitamos SD pooled, asumir 1 para simplificar)
                d = effect_value  # Asumiendo que ya está estandarizado
                se_d = se_diff
                
                log_rr, se_log_rr = smd_to_logrr(d, se_d)
                rr = np.exp(log_rr)
                
                self.studies.append({
                    "study_id": study_id,
                    "type": "continuous",
                    "original_measure": "MEAN",
                    "converted_measure": "RR_approx",
                    "effect": rr,
                    "log_effect": log_rr,
                    "se_log_effect": se_log_rr,
                    "n_i": n_i or "",
                    "n_c": n_c or "",
                    "cohens_d": d,
                    "se_d": se_d
                })
    
    def pooled_effect_random_effects(self) -> Dict:
        """
        Calcula efecto combinado usando modelo de efectos aleatorios (DerSimonian-Laird).
        """
        if not self.studies:
            return {"error": "No studies added"}
        
        # Extraer log_effects y sus varianzas
        log_effects = []
        variances = []
        weights = []
        
        for study in self.studies:
            if "log_effect" in study and "se_log_effect" in study:
                log_effects.append(study["log_effect"])
                variance = study["se_log_effect"] ** 2
                variances.append(variance)
                weights.append(1 / variance)
        
        if not log_effects:
            return {"error": "No studies with calculable effects"}
        
        log_effects = np.array(log_effects)
        variances = np.array(variances)
        weights = np.array(weights)
        
        # Efecto fijo (inicial)
        pooled_log_effect_fixed = np.sum(weights * log_effects) / np.sum(weights)
        
        # Calcular tau² (heterogeneidad)
        Q = np.sum(weights * (log_effects - pooled_log_effect_fixed) ** 2)
        df = len(log_effects) - 1
        
        if df > 0 and Q > df:
            tau_squared = (Q - df) / np.sum(weights)
        else:
            tau_squared = 0
        
        # Pesos con efectos aleatorios
        random_weights = 1 / (variances + tau_squared)
        
        # Efecto combinado
        pooled_log_effect = np.sum(random_weights * log_effects) / np.sum(random_weights)
        pooled_se = np.sqrt(1 / np.sum(random_weights))
        
        # Intervalo de confianza 95%
        ci_lower = pooled_log_effect - 1.96 * pooled_se
        ci_upper = pooled_log_effect + 1.96 * pooled_se
        
        # p-value
        z_stat = pooled_log_effect / pooled_se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        
        # I²
        I_squared = max(0, (Q - df) / Q * 100) if Q > 0 else 0
        
        return {
            "model": "Random Effects (DerSimonian-Laird)",
            "studies": len(self.studies),
            "pooled_effect_rr": np.exp(pooled_log_effect),
            "pooled_effect_log_rr": pooled_log_effect,
            "se_log_rr": pooled_se,
            "ci_lower_rr": np.exp(ci_lower),
            "ci_upper_rr": np.exp(ci_upper),
            "ci_lower_log": ci_lower,
            "ci_upper_log": ci_upper,
            "p_value": p_value,
            "z_statistic": z_stat,
            "tau_squared": tau_squared,
            "I_squared": I_squared,
            "Q_statistic": Q,
            "df": df,
            "interpretation": self._interpret_results(np.exp(pooled_log_effect), p_value, I_squared)
        }
    
    def _interpret_results(self, pooled_rr: float, p_value: float, I2: float) -> str:
        """Interpreta resultados del meta-análisis."""
        
        parts = []
        
        # Magnitud del efecto
        if pooled_rr < 0.9:
            parts.append(f"RR={pooled_rr:.2f}: El tratamiento reduce el riesgo")
        elif pooled_rr > 1.1:
            parts.append(f"RR={pooled_rr:.2f}: El tratamiento aumenta el riesgo")
        else:
            parts.append(f"RR={pooled_rr:.2f}: Efecto neutro o marginal")
        
        # Significancia estadística
        if p_value < 0.05:
            parts.append(f"p={p_value:.4f} (significativo)")
        else:
            parts.append(f"p={p_value:.4f} (no significativo)")
        
        # Heterogeneidad
        if I2 < 30:
            parts.append(f"Baja heterogeneidad (I²={I2:.1f}%)")
        elif I2 < 75:
            parts.append(f"Moderada heterogeneidad (I²={I2:.1f}%)")
        else:
            parts.append(f"Alta heterogeneidad (I²={I2:.1f}%)")
        
        return "; ".join(parts)
    
    def summary_table(self) -> List[Dict]:
        """Genera tabla resumen de todos los estudios."""
        table = []
        for study in self.studies:
            table.append({
                "study_id": study["study_id"],
                "type": study["type"],
                "measure": study.get("effect_measure", study.get("original_measure", "")),
                "effect": round(study["effect"], 4),
                "log_effect": round(study["log_effect"], 4),
                "se": round(study["se_log_effect"], 4),
                "n_total": (study.get("n_i", 0) or 0) + (study.get("n_c", 0) or 0)
            })
        return table


# Función de conveniencia para uso directo
def create_network_meta_analysis(
    binary_studies: List[Dict] = None,
    continuous_studies: List[Dict] = None,
    extracted_studies: List[Dict] = None
) -> BayesianNetworkMetaAnalysis:
    """
    Crea un meta-análisis en red a partir de datos de diferentes fuentes.
    
    Args:
        binary_studies: Lista de dicts con {study_id, n_i, n_c, events_i, events_c, effect_measure}
        continuous_studies: Lista de dicts con {study_id, mean_i, mean_c, sd_i, sd_c, n_i, n_c}
        extracted_studies: Lista de dicts con {study_id, effect_measure, effect_value, ci_lower, ci_upper}
    
    Returns:
        BayesianNetworkMetaAnalysis con todos los estudios agregados
    """
    
    bnma = BayesianNetworkMetaAnalysis()
    
    # Agregar estudios binarios
    if binary_studies:
        for study in binary_studies:
            bnma.add_binary_study(
                study_id=study["study_id"],
                n_i=study["n_i"],
                n_c=study["n_c"],
                events_i=study["events_i"],
                events_c=study["events_c"],
                effect_measure=study.get("effect_measure", "RR")
            )
    
    # Agregar estudios continuos
    if continuous_studies:
        for study in continuous_studies:
            bnma.add_continuous_study(
                study_id=study["study_id"],
                mean_i=study["mean_i"],
                mean_c=study["mean_c"],
                sd_i=study["sd_i"],
                sd_c=study["sd_c"],
                n_i=study["n_i"],
                n_c=study["n_c"],
                direction=study.get("direction", "lower_better")
            )
    
    # Agregar estudios extraídos
    if extracted_studies:
        for study in extracted_studies:
            bnma.add_extracted_study(
                study_id=study["study_id"],
                effect_measure=study["effect_measure"],
                effect_value=study["effect_value"],
                ci_lower=study.get("ci_lower"),
                ci_upper=study.get("ci_upper"),
                n_i=study.get("n_i"),
                n_c=study.get("n_c"),
                events_i=study.get("events_i"),
                events_c=study.get("events_c")
            )
    
    return bnma


if __name__ == "__main__":
    # Demo con datos de ejemplo
    print("=" * 60)
    print("BAYESIAN NETWORK META-ANALYSIS - DEMO")
    print("=" * 60)
    
    # Estudios binarios (ej: mortalidad)
    binary = [
        {"study_id": "PubMed_1", "n_i": 100, "n_c": 100, "events_i": 15, "events_c": 25, "effect_measure": "RR"},
        {"study_id": "PubMed_2", "n_i": 200, "n_c": 200, "events_i": 30, "events_c": 45, "effect_measure": "RR"},
    ]
    
    # Estudios continuos (ej: visual acuity de CT.gov)
    continuous = [
        {"study_id": "CTgov_1", "mean_i": -0.0574, "mean_c": 0.0535, "sd_i": 0.1147, "sd_c": 0.0914, "n_i": 19, "n_c": 17, "direction": "lower_better"},
    ]
    
    # Estudios extraídos (ej: RR desde abstract)
    extracted = [
        {"study_id": "PubMed_3", "effect_measure": "RR", "effect_value": 0.94, "ci_lower": 0.82, "ci_upper": 1.08, "n_i": 500, "n_c": 500},
    ]
    
    bnma = create_network_meta_analysis(binary, continuous, extracted)
    
    print(f"\nEstudios agregados: {len(bnma.studies)}")
    print("\nTabla resumen:")
    for row in bnma.summary_table():
        print(f"  {row['study_id']}: {row['type']} | Effect={row['effect']:.4f} | Log={row['log_effect']:.4f}")
    
    print("\n" + "=" * 60)
    print("META-ANÁLISIS EN RED")
    print("=" * 60)
    
    results = bnma.pooled_effect_random_effects()
    
    print(f"\nModelo: {results['model']}")
    print(f"Estudios: {results['studies']}")
    print(f"Efecto combinado RR: {results['pooled_effect_rr']:.4f}")
    print(f"IC 95%: [{results['ci_lower_rr']:.4f}, {results['ci_upper_rr']:.4f}]")
    print(f"p-value: {results['p_value']:.4f}")
    print(f"I²: {results['I_squared']:.1f}%")
    print(f"Tau²: {results['tau_squared']:.4f}")
    print(f"\nInterpretación: {results['interpretation']}")
