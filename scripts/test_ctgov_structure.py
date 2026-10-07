#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, 'scripts')
from ctgov_api import ClinicalTrialsAPI

api = ClinicalTrialsAPI()
trial = api.get_trial_details('NCT03758118')

if trial:
    results = trial.get('resultsSection', {})
    outcomes = results.get('outcomeMeasuresModule', {}).get('outcomeMeasures', [])
    
    print('=== ESTRUCTURA COMPLETA DEL PRIMER OUTCOME ===')
    if outcomes:
        out = outcomes[0]
        print(json.dumps(out, indent=2)[:3000])
else:
    print('No se pudo obtener el trial')
