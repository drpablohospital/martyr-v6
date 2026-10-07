"""
data_loaders.py - Carga de datos de estudios para meta-análisis

Funciones compartidas para cargar datos desde CSV y JSON.
Elimina duplicación entre claim_extractor.py, pipeline_integrator.py y martyr.py
"""

import csv
import json
from pathlib import Path


def load_studies(csv_path):
    """
    Carga datos de estudios desde CSV con múltiples formatos soportados.
    
    Soporta formatos:
    - Formato estándar: study, year, n_exp, events_exp, n_ctrl, events_ctrl
    - Formato alternativo: study_id, author, year, n_i, events_i, n_c, events_c
    - Con efectos pre-calculados: rr, rr_ci_lower, rr_ci_upper, etc.
    
    Parameters
    ----------
    csv_path : str o Path
        Ruta al archivo CSV
    
    Returns
    -------
    list
        Lista de diccionarios con datos de estudios
    """
    studies = []
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        
        # Mapeo flexible de nombres de columnas
        column_map = {
            'n_exp': ['n_i', 'n_intervention', 'n_treatment', 'sample_size_exp'],
            'events_exp': ['events_i', 'events_intervention', 'outcomes_exp'],
            'n_ctrl': ['n_c', 'n_control', 'n_placebo', 'sample_size_ctrl'],
            'events_ctrl': ['events_c', 'events_control', 'outcomes_ctrl'],
            'effect_size': ['rr', 'or', 'hr', 'risk_ratio', 'odds_ratio'],
            'ci_lower': ['rr_ci_lower', 'or_ci_lower', 'hr_ci_lower', 'lower_ci'],
            'ci_upper': ['rr_ci_upper', 'or_ci_upper', 'hr_ci_upper', 'upper_ci'],
            'study_id': ['study', 'trial', 'author', 'reference'],
            'intervention': ['treatment', 'therapy', 'exposure'],
            'control': ['comparator', 'placebo', 'usual_care'],
        }
        
        for row in reader:
            # Convertir campos numéricos
            numeric_fields = ['effect_size', 'se', 'ci_lower', 'ci_upper', 
                              'n_total', 'weight', 'rr', 'rr_ci_lower', 'rr_ci_upper',
                              'or', 'or_ci_lower', 'or_ci_upper',
                              'hr', 'hr_ci_lower', 'hr_ci_upper',
                              'n_i', 'n_c', 'events_i', 'events_c',
                              'n_exp', 'events_exp', 'n_ctrl', 'events_ctrl']
            
            for key in numeric_fields:
                if key in row and row[key]:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        row[key] = None
            
            # Aplicar mapeo de columnas si faltan estándares
            for standard, alternatives in column_map.items():
                if standard not in row or not row[standard]:
                    for alt in alternatives:
                        if alt in row and row[alt]:
                            row[standard] = row[alt]
                            break
            
            studies.append(row)
    
    return studies


def load_json_data(json_path):
    """
    Carga datos desde archivo JSON.
    
    Parameters
    ----------
    json_path : str o Path
        Ruta al archivo JSON
    
    Returns
    -------
    dict
        Datos del JSON
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_studies_data(studies, required_fields=None):
    """
    Valida que los datos de estudios tengan los campos mínimos necesarios.
    
    Parameters
    ----------
    studies : list
        Lista de diccionarios con datos de estudios
    required_fields : list, optional
        Campos requeridos. Default: ['study_id', 'n_exp', 'events_exp', 'n_ctrl', 'events_ctrl']
    
    Returns
    -------
    tuple
        (is_valid: bool, errors: list)
    """
    if required_fields is None:
        required_fields = ['study_id']
    
    if not studies:
        return False, ["No se encontraron estudios en el CSV"]
    
    errors = []
    
    for i, study in enumerate(studies):
        missing = [f for f in required_fields if f not in study or not study[f]]
        if missing:
            errors.append(f"Estudio {i+1} ({study.get('study_id', 'N/A')}): faltan campos {missing}")
    
    return len(errors) == 0, errors
