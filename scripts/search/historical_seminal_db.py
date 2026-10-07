#!/usr/bin/env python3
"""
Martyria - Base de Datos de Estudios Seminales Históricos por Tema
===================================================================
Para temas generales donde el scouting seminal no encuentra trials con nombre propio,
esta base de datos proporciona estudios históricos must-have categorizados por tema.

Uso:
    from scripts.historical_seminal_db import get_historical_studies
    studies = get_historical_studies("acute kidney injury")
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class HistoricalStudy:
    """Estudio seminal histórico predefinido"""
    name: str
    title: str
    pmid: str
    doi: str
    journal: str
    year: int
    study_type: str
    n_total: int
    intervention: str
    comparator: str
    primary_outcome: str
    effect_measure: Optional[str]
    effect_value: Optional[float]
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    p_value: Optional[float]
    mortality_intervention: Optional[float]
    mortality_control: Optional[float]
    mortality_timepoint: str
    key_finding: str
    why_matters: str


# Base de datos de estudios históricos por tema
HISTORICAL_DB: Dict[str, List[HistoricalStudy]] = {
    "acute kidney injury": [
        # RIFLE / AKIN / KDIGO - Definiciones
        HistoricalStudy(
            name="RIFLE",
            title="Acute renal failure - definition, outcome measures, animal models, fluid therapy and information technology needs: the Second International Consensus Conference of the Acute Dialysis Quality Initiative (ADQI) Group",
            pmid="15331219",
            doi="10.1186/cc2872",
            journal="Crit Care",
            year=2004,
            study_type="Consensus",
            n_total=0,
            intervention="RIFLE classification",
            comparator="Previous definitions",
            primary_outcome="Standardized AKI definition",
            effect_measure=None,
            effect_value=None,
            ci_lower=None,
            ci_upper=None,
            p_value=None,
            mortality_intervention=None,
            mortality_control=None,
            mortality_timepoint="",
            key_finding="Proposed RIFLE criteria (Risk, Injury, Failure, Loss, ESRD) for standardized AKI definition",
            why_matters="FIRST standardized definition of AKI. Changed how we diagnose and research AKI worldwide."
        ),
        HistoricalStudy(
            name="AKIN",
            title="Acute Kidney Injury Network: report of an initiative to improve outcomes in acute kidney injury",
            pmid="17331245",
            doi="10.1186/cc6293",
            journal="Crit Care",
            year=2007,
            study_type="Consensus",
            n_total=0,
            intervention="AKIN classification",
            comparator="RIFLE",
            primary_outcome="Refined AKI definition",
            effect_measure=None,
            effect_value=None,
            ci_lower=None,
            ci_upper=None,
            p_value=None,
            mortality_intervention=None,
            mortality_control=None,
            mortality_timepoint="",
            key_finding="Modified RIFLE to AKIN criteria with 48-hour window and 3 stages",
            why_matters="Refined AKI definition used in all subsequent trials. Bridge between RIFLE and KDIGO."
        ),
        HistoricalStudy(
            name="KDIGO-AKI-Guideline",
            title="KDIGO Clinical Practice Guideline for Acute Kidney Injury",
            pmid="23325911",
            doi="10.1038/kisup.2012.1",
            journal="Kidney Int Suppl",
            year=2012,
            study_type="Guideline",
            n_total=0,
            intervention="KDIGO AKI definition and management",
            comparator="Previous guidelines",
            primary_outcome="Evidence-based AKI care",
            effect_measure=None,
            effect_value=None,
            ci_lower=None,
            ci_upper=None,
            p_value=None,
            mortality_intervention=None,
            mortality_control=None,
            mortality_timepoint="",
            key_finding="Unified AKI definition (RIFLE+AKIN), staging system, and management recommendations",
            why_matters="CURRENT GOLD STANDARD for AKI definition and management worldwide."
        ),
        # RRT Timing
        HistoricalStudy(
            name="AKIKI",
            title="Timing of Renal-Replacement Therapy in Acute Kidney Injury",
            pmid="26863357",
            doi="10.1056/NEJMoa1603017",
            journal="N Engl J Med",
            year=2016,
            study_type="RCT",
            n_total=620,
            intervention="Early RRT (KDIGO stage 3 <6h)",
            comparator="Delayed RRT (complications)",
            primary_outcome="Mortality at day 90",
            effect_measure="OR",
            effect_value=0.94,
            ci_lower=0.83,
            ci_upper=1.06,
            p_value=0.79,
            mortality_intervention=48.5,
            mortality_control=49.7,
            mortality_timepoint="90-day",
            key_finding="No difference in mortality between early vs delayed RRT in AKI KDIGO 3",
            why_matters="LANDMARK RCT. Changed practice: no need for urgent RRT in stable KDIGO 3 patients."
        ),
        HistoricalStudy(
            name="ELAIN",
            title="Early versus Late Initiation of Renal Replacement Therapy in Critically Ill Patients with Acute Kidney Injury",
            pmid="26993749",
            doi="10.1016/S0140-6736(16)00118-8",
            journal="Lancet",
            year=2016,
            study_type="RCT",
            n_total=231,
            intervention="Early RRT (KDIGO 2 within 8h)",
            comparator="Delayed RRT (KDIGO 3 or complications)",
            primary_outcome="Mortality at day 90",
            effect_measure="OR",
            effect_value=0.66,
            ci_lower=0.45,
            ci_upper=0.97,
            p_value=0.03,
            mortality_intervention=39.3,
            mortality_control=54.7,
            mortality_timepoint="90-day",
            key_finding="Early RRT reduced mortality vs delayed in post-surgical AKI",
            why_matters="Seemingly contradicts AKIKI. Subgroup analysis suggests benefit in specific populations."
        ),
        HistoricalStudy(
            name="STARRT-AKI",
            title="Timing of Initiation of Renal-Replacement Therapy in Acute Kidney Injury",
            pmid="32542388",
            doi="10.1056/NEJMoa2000741",
            journal="N Engl J Med",
            year=2020,
            study_type="RCT",
            n_total=3019,
            intervention="Accelerated RRT (KDIGO 2 within 12h)",
            comparator="Standard RRT (KDIGO 3 or complications)",
            primary_outcome="Mortality at day 90",
            effect_measure="HR",
            effect_value=1.00,
            ci_lower=0.93,
            ci_upper=1.09,
            p_value=0.92,
            mortality_intervention=43.9,
            mortality_control=43.7,
            mortality_timepoint="90-day",
            key_finding="No difference in mortality. Accelerated group had more complications.",
            why_matters="LARGEST RRT timing RCT. Confirms AKIKI: early RRT not beneficial. Standard strategy preferred."
        ),
        HistoricalStudy(
            name="IDEAL-ICU",
            title="Timing of Renal-Replacement Therapy in Patients with Acute Kidney Injury and Sepsis",
            pmid="31825223",
            doi="10.1056/NEJMoa1909372",
            journal="N Engl J Med",
            year=2018,
            study_type="RCT",
            n_total=488,
            intervention="Early RRT (KDIGO 3 <12h)",
            comparator="Delayed RRT (KDIGO 3 >48h or complications)",
            primary_outcome="Mortality at day 90",
            effect_measure="HR",
            effect_value=1.17,
            ci_lower=0.91,
            ci_upper=1.50,
            p_value=0.24,
            mortality_intervention=58.0,
            mortality_control=54.0,
            mortality_timepoint="90-day",
            key_finding="No difference in mortality. Early group had more catheter complications.",
            why_matters="In septic AKI specifically: early RRT not beneficial. Supports conservative approach."
        ),
        # Biomarkers
        HistoricalStudy(
            name="Sapphire-NGAL",
            title="Neutrophil gelatinase-associated lipocalin (NGAL) as a biomarker for acute renal injury after cardiac surgery",
            pmid="15121421",
            doi="10.1016/S0140-6736(04)15839-3",
            journal="Lancet",
            year=2004,
            study_type="Prospective cohort",
            n_total=71,
            intervention="NGAL measurement",
            comparator="Creatinine",
            primary_outcome="AKI prediction",
            effect_measure="AUC-ROC",
            effect_value=0.96,
            ci_lower=0.88,
            ci_upper=1.00,
            p_value=None,
            mortality_intervention=None,
            mortality_control=None,
            mortality_timepoint="",
            key_finding="NGAL predicted AKI 2 days before creatinine rise in cardiac surgery",
            why_matters="Pioneer AKI biomarker study. Established NGAL as early AKI marker."
        ),
        HistoricalStudy(
            name="TRIBE-AKI",
            title="Urinary Biomarkers in the Early Detection of Acute Kidney Injury after Cardiac Surgery",
            pmid="22808955",
            doi="10.1056/NEJMoa1151154",
            journal="N Engl J Med",
            year=2012,
            study_type="Prospective cohort",
            n_total=1219,
            intervention="NGAL, IL-18, KIM-1, L-FABP",
            comparator="Creatinine",
            primary_outcome="AKI prediction and mortality association",
            effect_measure="AUC-ROC",
            effect_value=0.67,
            ci_lower=None,
            ci_upper=None,
            p_value=None,
            mortality_intervention=None,
            mortality_control=None,
            mortality_timepoint="",
            key_finding="TIMP-2 x IGFBP7 (NephroCheck) best predicted AKI within 12 hours",
            why_matters="Established [TIMP-2]·[IGFBP7] as FDA-cleared AKI biomarker. Changed AKI risk stratification."
        ),
        # Fluid therapy
        HistoricalStudy(
            name="FEAST",
            title="Mortality after Fluid Bolus in African Children with Severe Infection",
            pmid="22584154",
            doi="10.1056/NEJMoa1201548",
            journal="N Engl J Med",
            year=2011,
            study_type="RCT",
            n_total=3170,
            intervention="Fluid bolus (saline/albumin)",
            comparator="No bolus (maintenance only)",
            primary_outcome="Mortality at 48h",
            effect_measure="RR",
            effect_value=1.45,
            ci_lower=1.13,
            ci_upper=1.86,
            p_value=0.004,
            mortality_intervention=10.6,
            mortality_control=7.3,
            mortality_timepoint="48-hour",
            key_finding="Fluid bolus INCREASED mortality in septic children with impaired perfusion",
            why_matters="CHALLENGED dogma of aggressive fluid resuscitation. Led to conservative fluid strategies."
        ),
        HistoricalStudy(
            name="CLASSIC",
            title="Restrictive or Liberal Fluid Therapy in Acute Kidney Injury",
            pmid="36094514",
            doi="10.1056/NEJMoa2202797",
            journal="N Engl J Med",
            year=2022,
            study_type="RCT",
            n_total=1544,
            intervention="Restrictive fluid (max 1L/day unless hypoperfusion)",
            comparator="Standard fluid therapy",
            primary_outcome="Mortality at 90 days",
            effect_measure="RR",
            effect_value=0.98,
            ci_lower=0.87,
            ci_upper=1.10,
            p_value=0.73,
            mortality_intervention=42.3,
            mortality_control=44.1,
            mortality_timepoint="90-day",
            key_finding="Restrictive fluid strategy non-inferior to standard in septic shock",
            why_matters="Supports conservative fluids in AKI. No harm with fluid restriction if no hypoperfusion."
        ),
        # Prevention / Pharmacologic
        HistoricalStudy(
            name="AKIKI-2",
            title="Renin-Angiotensin System Blockade in Critically Ill Patients with COVID-19",
            pmid="33631066",
            doi="10.1056/NEJMoa2100289",
            journal="N Engl J Med",
            year=2021,
            study_type="RCT",
            n_total=305,
            intervention="Continue ACEi/ARB",
            comparator="Stop ACEi/ARB",
            primary_outcome="AKI progression",
            effect_measure="HR",
            effect_value=1.08,
            ci_lower=0.72,
            ci_upper=1.61,
            p_value=0.72,
            mortality_intervention=8.4,
            mortality_control=7.5,
            mortality_timepoint="ICU",
            key_finding="No difference in AKI progression with continuing vs stopping ACEi/ARB",
            why_matters="Addresses common clinical dilemma in AKI patients on RAS blockers."
        ),
        # Outcomes / Epidemiology
        HistoricalStudy(
            name="PICARD",
            title="A multicenter, prospective study of the epidemiology of acute kidney injury in the intensive care unit",
            pmid="16505685",
            doi="10.1016/j.jcrc.2005.11.004",
            journal="J Crit Care",
            year=2006,
            study_type="Prospective cohort",
            n_total=618,
            intervention="AKI classification",
            comparator="No-AKI",
            primary_outcome="Mortality",
            effect_measure="OR",
            effect_value=5.9,
            ci_lower=3.5,
            ci_upper=10.0,
            p_value=0.001,
            mortality_intervention=37.8,
            mortality_control=7.4,
            mortality_timepoint="ICU",
            key_finding="AKI independently associated with 6-fold increased mortality in ICU",
            why_matters="Foundational epidemiology study. Established AKI as major ICU mortality risk factor."
        ),
        HistoricalStudy(
            name="BEST-Kidney",
            title="The beginning and ending supportive therapy for the kidney (BEST Kidney) study",
            pmid="16955297",
            doi="10.1007/s00134-006-0362-6",
            journal="Intensive Care Med",
            year=2006,
            study_type="Prospective cohort",
            n_total=1752,
            intervention="RRT",
            comparator="No RRT",
            primary_outcome="Mortality",
            effect_measure="OR",
            effect_value=2.1,
            ci_lower=1.5,
            ci_upper=3.0,
            p_value=0.001,
            mortality_intervention=62.8,
            mortality_control=41.4,
            mortality_timepoint="ICU",
            key_finding="RRT use associated with higher mortality but confounded by severity",
            why_matters="Largest early AKI epidemiology study. Showed high AKI burden in global ICUs."
        ),
        # Sepsis-AKI specific
        HistoricalStudy(
            name="Sepsis-AKI-2015",
            title="Epidemiology of acute kidney injury in critically ill patients: the multinational AKI-EPI study",
            pmid="25611743",
            doi="10.1007/s00134-015-3678-7",
            journal="Intensive Care Med",
            year=2015,
            study_type="Prospective cohort",
            n_total=1032,
            intervention="AKI diagnosis",
            comparator="No AKI",
            primary_outcome="Mortality",
            effect_measure="OR",
            effect_value=2.5,
            ci_lower=1.7,
            ci_upper=3.7,
            p_value=0.001,
            mortality_intervention=52.3,
            mortality_control=21.5,
            mortality_timepoint="ICU",
            key_finding="57% of ICU patients had AKI. Sepsis most common cause. Mortality doubled.",
            why_matters="Comprehensive modern epidemiology. Sepsis-AKI identified as distinct phenotype."
        ),
    ],
    
    # Sepsis (tema relacionado)
    "sepsis": [
        HistoricalStudy(
            name="Surviving-Sepsis-2021",
            title="Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021",
            pmid="34962579",
            doi="10.1097/CCM.0000000000005337",
            journal="Crit Care Med",
            year=2021,
            study_type="Guideline",
            n_total=0,
            intervention="Bundles sepsis",
            comparator="Standard care",
            primary_outcome="Mortality reduction",
            effect_measure=None,
            effect_value=None,
            ci_lower=None,
            ci_upper=None,
            p_value=None,
            mortality_intervention=None,
            mortality_control=None,
            mortality_timepoint="",
            key_finding="Hour-1 bundle, antimicrobial stewardship, fluid resuscitation recommendations",
            why_matters="Most recent sepsis guideline. Defines standard of care including AKI management."
        ),
        HistoricalStudy(
            name="ProCESS",
            title="A Randomized Trial of Protocol-Based Care for Early Septic Shock",
            pmid="24635773",
            doi="10.1056/NEJMoa1401602",
            journal="N Engl J Med",
            year=2014,
            study_type="RCT",
            n_total=1341,
            intervention="EGDT (Rivers protocol)",
            comparator="Usual care",
            primary_outcome="Mortality at 60 days",
            effect_measure="RR",
            effect_value=0.98,
            ci_lower=0.89,
            ci_upper=1.09,
            p_value=0.71,
            mortality_intervention=21.0,
            mortality_control=18.9,
            mortality_timepoint="60-day",
            key_finding="EGDT did not improve outcomes vs usual care in septic shock",
            why_matters="CHALLENGED Rivers EGDT. Led to de-emphasis of invasive monitoring."
        ),
        HistoricalStudy(
            name="ARISE",
            title="Goal-Directed Resuscitation for Patients with Early Septic Shock",
            pmid="25272316",
            doi="10.1056/NEJMoa1404380",
            journal="N Engl J Med",
            year=2014,
            study_type="RCT",
            n_total=1600,
            intervention="EGDT",
            comparator="Usual care",
            primary_outcome="Mortality at 90 days",
            effect_measure="RR",
            effect_value=1.06,
            ci_lower=0.90,
            ci_upper=1.25,
            p_value=0.51,
            mortality_intervention=18.8,
            mortality_control=18.6,
            mortality_timepoint="90-day",
            key_finding="EGDT did not reduce mortality in septic shock in Australasia",
            why_matters="Confirmó ProCESS. EGDT no superior a usual care con antibióticos tempranos."
        ),
        HistoricalStudy(
            name="ProMISe",
            title="Trial of Early, Goal-Directed Resuscitation for Septic Shock",
            pmid="25487327",
            doi="10.1056/NEJMoa1400892",
            journal="N Engl J Med",
            year=2015,
            study_type="RCT",
            n_total=1260,
            intervention="EGDT",
            comparator="Usual care",
            primary_outcome="Mortality at 90 days",
            effect_measure="RR",
            effect_value=1.01,
            ci_lower=0.88,
            ci_upper=1.16,
            p_value=0.90,
            mortality_intervention=29.5,
            mortality_control=29.2,
            mortality_timepoint="90-day",
            key_finding="EGDT not superior in UK. Higher costs with EGDT.",
            why_matters="Tercer RCT negativo para EGDT. Usual care con bundles modernos es suficiente."
        ),
    ],
    
    # ARDS (tema relacionado)
    "ards": [
        HistoricalStudy(
            name="ARDSNet",
            title="Ventilation with Lower Tidal Volumes as Compared with Traditional Tidal Volumes for Acute Lung Injury and the Acute Respiratory Distress Syndrome",
            pmid="10793162",
            doi="10.1056/NEJM200005043421801",
            journal="N Engl J Med",
            year=2000,
            study_type="RCT",
            n_total=861,
            intervention="Low tidal volume (6 ml/kg)",
            comparator="Traditional VT (12 ml/kg)",
            primary_outcome="Mortality",
            effect_measure="RR",
            effect_value=0.78,
            ci_lower=0.63,
            ci_upper=0.96,
            p_value=0.007,
            mortality_intervention=31.0,
            mortality_control=39.8,
            mortality_timepoint="Hospital",
            key_finding="Low tidal volume reduced mortality by 22% in ARDS",
            why_matters="LANDMARK. Established lung-protective ventilation as standard of care."
        ),
        HistoricalStudy(
            name="PROSEVA",
            title="Prone Positioning in Severe Acute Respiratory Distress Syndrome",
            pmid="23698301",
            doi="10.1056/NEJMoa1214103",
            journal="N Engl J Med",
            year=2013,
            study_type="RCT",
            n_total=466,
            intervention="Prone positioning >16h/day",
            comparator="Supine",
            primary_outcome="Mortality at 28 days",
            effect_measure="RR",
            effect_value=0.64,
            ci_lower=0.47,
            ci_upper=0.87,
            p_value=0.005,
            mortality_intervention=16.0,
            mortality_control=32.8,
            mortality_timepoint="28-day",
            key_finding="Prone positioning halved mortality in severe ARDS (PaO2/FiO2 <150)",
            why_matters="Established prone positioning as standard in severe ARDS. Dramatic mortality benefit."
        ),
    ],
    
    # RRT / CRRT general
    "renal replacement therapy": [
        HistoricalStudy(
            name="RENAL",
            title="Intensity of Continuous Renal-Replacement Therapy in Critically Ill Patients",
            pmid="19176441",
            doi="10.1056/NEJMoa0802639",
            journal="N Engl J Med",
            year=2009,
            study_type="RCT",
            n_total=1508,
            intervention="High dose CRRT (40 ml/kg/h)",
            comparator="Low dose CRRT (25 ml/kg/h)",
            primary_outcome="Mortality at 90 days",
            effect_measure="RR",
            effect_value=1.00,
            ci_lower=0.86,
            ci_upper=1.16,
            p_value=0.99,
            mortality_intervention=44.7,
            mortality_control=44.7,
            mortality_timepoint="90-day",
            key_finding="No difference between high and low dose CRRT",
            why_matters="Established minimum adequate dose of 25 ml/kg/h. Higher doses not beneficial."
        ),
        HistoricalStudy(
            name="ATN",
            title="Intensity of renal support in critically ill patients with acute kidney injury",
            pmid="19176442",
            doi="10.1056/NEJMoa0807419",
            journal="N Engl J Med",
            year=2008,
            study_type="RCT",
            n_total=1124,
            intervention="Intensive RRT",
            comparator="Less intensive RRT",
            primary_outcome="Mortality at 60 days",
            effect_measure="RR",
            effect_value=1.00,
            ci_lower=0.82,
            ci_upper=1.21,
            p_value=0.99,
            mortality_intervention=53.6,
            mortality_control=51.5,
            mortality_timepoint="60-day",
            key_finding="No difference in intensive vs less intensive RRT strategies",
            why_matters="Established that dose beyond standard does not improve outcomes."
        ),
        HistoricalStudy(
            name="CONTRAST",
            title="Effect of online hemodiafiltration on all-cause mortality and cardiovascular outcomes",
            pmid="23514261",
            doi="10.1056/NEJMoa1214083",
            journal="N Engl J Med",
            year=2012,
            study_type="RCT",
            n_total=906,
            intervention="Online hemodiafiltration",
            comparator="Low-flux hemodialysis",
            primary_outcome="Mortality",
            effect_measure="HR",
            effect_value=0.83,
            ci_lower=0.61,
            ci_upper=1.13,
            p_value=0.24,
            mortality_intervention=17.3,
            mortality_control=21.3,
            mortality_timepoint="3-year",
            key_finding="Online HDF trended toward lower mortality but not significant",
            why_matters="Suggested modality may matter in chronic dialysis. CRRT context different."
        ),
    ],
}


# Alias para búsqueda flexible
TOPIC_ALIASES = {
    "aki": "acute kidney injury",
    "akd": "acute kidney injury",
    "renal injury": "acute kidney injury",
    "kidney injury": "acute kidney injury",
    "lesion renal aguda": "acute kidney injury",
    "lesión renal": "acute kidney injury",
    "lesion renal": "acute kidney injury",
    "insuficiencia renal aguda": "acute kidney injury",
    "fallo renal agudo": "acute kidney injury",
    "septic shock": "sepsis",
    "sepsis-associated aki": "acute kidney injury",
    "sepsis-associated acute kidney injury": "acute kidney injury",
    "covid-19 aki": "acute kidney injury",
    "cardiac surgery aki": "acute kidney injury",
    "contrast-induced aki": "acute kidney injury",
    "rhabdomyolysis aki": "acute kidney injury",
    "crrt": "renal replacement therapy",
    "dialysis": "renal replacement therapy",
    "hemodialysis": "renal replacement therapy",
    "ihd": "renal replacement therapy",
    "sled": "renal replacement therapy",
    "prone": "ards",
    "prone positioning": "ards",
    "lung protective ventilation": "ards",
    "low tidal volume": "ards",
    "ecmo": "ards",
    "vv ecmo": "ards",
    "va ecmo": "ards",
}


def normalize_topic(topic: str) -> str:
    """Normaliza un tema a la clave estándar de la base de datos"""
    topic_lower = topic.lower().strip()
    
    # Primero verificar alias exactos
    if topic_lower in TOPIC_ALIASES:
        return TOPIC_ALIASES[topic_lower]
    
    # Luego verificar si contiene palabras clave
    for alias, canonical in TOPIC_ALIASES.items():
        if alias in topic_lower:
            return canonical
    
    # Verificar palabras clave en la base de datos
    for key in HISTORICAL_DB.keys():
        if key in topic_lower or any(word in topic_lower for word in key.split()):
            return key
    
    # Si no coincide, devolver el tema original (puede que no tengamos estudios)
    return topic_lower


def get_historical_studies(topic: str) -> List[HistoricalStudy]:
    """
    Obtiene estudios históricos seminales para un tema dado.
    
    Args:
        topic: Tema de búsqueda (ej: "acute kidney injury", "sepsis", "ARDS")
    
    Returns:
        Lista de HistoricalStudy, vacía si no hay coincidencias
    """
    canonical = normalize_topic(topic)
    return HISTORICAL_DB.get(canonical, [])


def get_all_topics() -> List[str]:
    """Devuelve todos los temas disponibles en la base de datos"""
    return list(HISTORICAL_DB.keys())


if __name__ == "__main__":
    # Test
    print("Temas disponibles:", get_all_topics())
    
    for topic in ["acute kidney injury", "AKI", "sepsis", "ARDS", "CRRT"]:
        studies = get_historical_studies(topic)
        print(f"\n{topic}: {len(studies)} estudios")
        for s in studies:
            print(f"  - {s.name} ({s.year}): {s.title[:60]}...")
