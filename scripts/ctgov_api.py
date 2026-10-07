"""
ClinicalTrials.gov API v2 Integration for MARTYR
Busca trials y extrae datos estructurados de resultados.

API Docs: https://clinicaltrials.gov/data-api/api
"""

import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

class ClinicalTrialsAPI:
    """Cliente para ClinicalTrials.gov API v2"""
    
    BASE_URL = "https://clinicaltrials.gov/api/v2"
    
    def __init__(self):
        self.session = requests.Session()
    
    def search_trials(
        self,
        query: str,
        status: Optional[str] = None,
        has_results: Optional[bool] = None,
        page_size: int = 20
    ) -> List[Dict]:
        """
        Busca trials por query.
        
        Args:
            query: Términos de búsqueda
            status: Filtrar por estado (COMPLETED, RECRUITING, etc.)
            has_results: True para trials con resultados publicados
            page_size: Número de resultados
        """
        params = {
            "query.term": query,
            "pageSize": page_size
        }
        
        if status:
            params["filter.overallStatus"] = status
        # NOTA: filter.hasResults no es soportado por CT.gov API v2
        # Los resultados se detectan por presencia de resultsSection
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/studies",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("studies", [])
        except Exception as e:
            print(f"Error buscando trials: {e}")
            return []
    
    def get_trial_details(self, nct_id: str) -> Optional[Dict]:
        """Obtiene detalles completos de un trial por NCT ID."""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/studies/{nct_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error obteniendo trial {nct_id}: {e}")
            return None
    
    def extract_outcome_data(self, trial: Dict) -> Dict:
        """
        Extrae datos de outcomes de un trial.
        Busca en resultsSection si está disponible.
        """
        result = {
            "nct_id": trial.get("protocolSection", {}).get("identificationModule", {}).get("nctId"),
            "title": trial.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle"),
            "has_results": False,
            "outcomes": [],
            "enrollment": None,
            "arms": [],
            "interventions": []
        }
        
        # Información básica
        status_module = trial.get("protocolSection", {}).get("statusModule", {})
        result["status"] = status_module.get("overallStatus")
        result["completion_date"] = status_module.get("completionDateStruct", {}).get("date")
        
        # Enrollment
        enrollment = trial.get("protocolSection", {}).get("designModule", {}).get("enrollmentInfo", {})
        result["enrollment"] = enrollment.get("count")
        
        # Arms/Intervenciones
        arms = trial.get("protocolSection", {}).get("armsInterventionsModule", {}).get("armGroups", [])
        result["arms"] = [
            {
                "label": arm.get("label"),
                "type": arm.get("type"),
                "description": arm.get("description"),
                "intervention_names": arm.get("interventionNames", [])
            }
            for arm in arms
        ]
        
        # Outcomes primarios
        outcomes = trial.get("protocolSection", {}).get("outcomesModule", {}).get("primaryOutcomes", [])
        result["outcomes"] = [
            {
                "measure": outcome.get("measure"),
                "description": outcome.get("description"),
                "time_frame": outcome.get("timeFrame")
            }
            for outcome in outcomes
        ]
        
        # RESULTADOS (si disponibles)
        results_section = trial.get("resultsSection", {})
        if results_section:
            result["has_results"] = True
            
            # Baseline characteristics
            baseline = results_section.get("baselineCharacteristicsModule", {})
            result["baseline"] = self._extract_baseline(baseline)
            
            # Outcome results
            outcome_results = results_section.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
            result["outcome_results"] = self._extract_outcome_results(outcome_results)
            
            # Adverse events
            adverse_events = results_section.get("adverseEventsModule", {})
            result["adverse_events"] = self._extract_adverse_events(adverse_events)
        
        return result
    
    def _extract_baseline(self, baseline: Dict) -> Dict:
        """Extrae características basales."""
        result = {}
        
        # N por grupo
        groups = baseline.get("groups", [])
        result["groups"] = [
            {
                "id": group.get("id"),
                "title": group.get("title"),
                "description": group.get("description"),
                "participants": group.get("participants")
            }
            for group in groups
        ]
        
        # Medidas demográficas
        measures = baseline.get("measures", [])
        result["demographics"] = [
            {
                "title": measure.get("title"),
                "unit": measure.get("unitOfMeasure"),
                "groups": [
                    {
                        "group_id": value.get("groupId"),
                        "value": value.get("value"),
                        "spread": value.get("spread")
                    }
                    for value in measure.get("classes", [{}])[0].get("categories", [{}])[0].get("measurements", [])
                ]
            }
            for measure in measures[:5]  # Limitar a primeras 5
        ]
        
        return result
    
    def _extract_outcome_results(self, outcomes: List[Dict]) -> List[Dict]:
        """Extrae resultados de outcomes con estructura CT.gov correcta."""
        result = []
        
        for outcome in outcomes:
            outcome_data = {
                "title": outcome.get("title"),
                "description": outcome.get("description"),
                "type": outcome.get("type"),
                "time_frame": outcome.get("timeFrame"),
                "param_type": outcome.get("paramType"),
                "dispersion_type": outcome.get("dispersionType"),
                "unit": outcome.get("unitOfMeasure"),
                "groups": []
            }
            
            # Extraer N de denoms
            n_by_group = {}
            for denom in outcome.get("denoms", []):
                for count in denom.get("counts", []):
                    group_id = count.get("groupId")
                    value = count.get("value")
                    if group_id and value:
                        try:
                            n_by_group[group_id] = int(value)
                        except:
                            n_by_group[group_id] = value
            
            # Extraer valores de classes -> categories -> measurements
            for cls in outcome.get("classes", []):
                for category in cls.get("categories", []):
                    for measurement in category.get("measurements", []):
                        group_id = measurement.get("groupId")
                        meas_data = {
                            "group_id": group_id,
                            "value": measurement.get("value"),
                            "spread": measurement.get("spread"),
                            "n": n_by_group.get(group_id)
                        }
                        outcome_data["groups"].append(meas_data)
            
            # Estadísticas (si disponibles)
            stats = outcome.get("analyses", [])
            if stats:
                stat = stats[0]
                outcome_data["statistics"] = {
                    "p_value": stat.get("pValue"),
                    "statistical_method": stat.get("statisticalMethod"),
                    "non_inferiority": stat.get("nonInferiority")
                }
            
            result.append(outcome_data)
        
        return result
    
    def _extract_adverse_events(self, adverse: Dict) -> Dict:
        """Extrae datos de eventos adversos."""
        result = {
            "summary": adverse.get("eventGroups", []),
            "serious_events": []
        }
        
        # Eventos graves
        serious = adverse.get("seriousEvents", [])
        result["serious_events"] = [
            {
                "term": event.get("term"),
                "organ_system": event.get("organSystem"),
                "assessed": event.get("assessed")
            }
            for event in serious[:10]
        ]
        
        return result
    
    def format_for_meta_analysis(self, trial_data: Dict) -> Optional[Dict]:
        """
        Formatea datos de CT.gov para el meta-análisis de MARTYR.
        Extrae N, eventos, efectos cuando están disponibles.
        """
        if not trial_data.get("has_results"):
            return None
        
        result = {
            "study_id": trial_data["nct_id"],
            "title": trial_data["title"],
            "year": self._extract_year(trial_data.get("completion_date")),
            "n_i": None,
            "n_c": None,
            "events_i": None,
            "events_c": None,
            "effect_measure": None,
            "effect_value": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "outcomes": []
        }
        
        # Extraer datos del primer outcome con medidas
        for outcome in trial_data.get("outcome_results", []):
            groups = outcome.get("groups", [])
            if len(groups) >= 2:
                # Asumir primer grupo = intervención, segundo = control
                g_i = groups[0]
                g_c = groups[1]
                
                result["n_i"] = g_i.get("n")
                result["n_c"] = g_c.get("n")
                result["effect_measure"] = outcome.get("param_type", "MEAN")
                
                # Para outcomes de tipo MEAN, guardar valores como efecto
                try:
                    val_i = float(g_i.get("value", 0)) if g_i.get("value") else None
                    val_c = float(g_c.get("value", 0)) if g_c.get("value") else None
                    if val_i is not None and val_c is not None:
                        # Diferencia entre grupos
                        result["effect_value"] = round(val_i - val_c, 4)
                        
                        # Calcular SD combinada para CI aproximado
                        spread_i = float(g_i.get("spread", 0)) if g_i.get("spread") else 0
                        spread_c = float(g_c.get("spread", 0)) if g_c.get("spread") else 0
                        n_i = g_i.get("n", 1) or 1
                        n_c = g_c.get("n", 1) or 1
                        
                        pooled_sd = ((spread_i**2 + spread_c**2) / 2) ** 0.5
                        se_diff = pooled_sd * ((1/n_i + 1/n_c) ** 0.5)
                        result["ci_lower"] = round((val_i - val_c) - 1.96 * se_diff, 4)
                        result["ci_upper"] = round((val_i - val_c) + 1.96 * se_diff, 4)
                except (ValueError, TypeError):
                    pass
                
                result["p_value"] = outcome.get("statistics", {}).get("p_value")
                break  # Usar solo el primer outcome válido
        
        return result
    
    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        """Extrae año de fecha."""
        if not date_str:
            return None
        try:
            return int(date_str.split("-")[0])
        except:
            return None


def search_and_extract(
    query: str,
    status: str = "COMPLETED",
    has_results: bool = True,  # Ahora filtramos manualmente después
    page_size: int = 10
) -> List[Dict]:
    """
    Función de alto nivel: busca trials y extrae datos formateados.
    """
    api = ClinicalTrialsAPI()
    
    print(f"Buscando trials en ClinicalTrials.gov: '{query}'...")
    trials = api.search_trials(
        query=query,
        status=status,
        has_results=has_results,
        page_size=page_size
    )
    
    print(f"Encontrados {len(trials)} trials")
    
    results = []
    for trial in trials:
        # Extraer datos estructurados
        trial_data = api.extract_outcome_data(trial)
        
        # Formatear para meta-análisis
        meta_data = api.format_for_meta_analysis(trial_data)
        
        results.append({
            "nct_id": trial_data["nct_id"],
            "title": trial_data["title"],
            "status": trial_data["status"],
            "enrollment": trial_data["enrollment"],
            "has_results": trial_data["has_results"],
            "outcomes_count": len(trial_data["outcomes"]),
            "meta_data": meta_data,
            "raw_data": trial_data
        })
    
    return results


if __name__ == "__main__":
    # Demo
    import sys
    
    query = sys.argv[1] if len(sys.argv) > 1 else "citicoline stroke"
    
    results = search_and_extract(query, page_size=5)
    
    print("\n" + "=" * 80)
    print("RESULTADOS DE CLINICALTRIALS.GOV")
    print("=" * 80)
    
    for r in results:
        print(f"\n📋 {r['nct_id']}")
        print(f"   Título: {r['title'][:70]}...")
        print(f"   Estado: {r['status']}")
        print(f"   Pacientes: {r['enrollment']}")
        print(f"   Resultados: {'Sí ✅' if r['has_results'] else 'No ❌'}")
        print(f"   Outcomes: {r['outcomes_count']}")
        
        if r['meta_data']:
            print(f"   N (I): {r['meta_data']['n_i']}")
            print(f"   N (C): {r['meta_data']['n_c']}")
            print(f"   Outcomes: {len(r['meta_data']['outcomes'])}")
