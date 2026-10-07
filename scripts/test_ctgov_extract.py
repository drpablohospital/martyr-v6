#!/usr/bin/env python3
import sys
sys.path.insert(0, 'scripts')
from ctgov_api import ClinicalTrialsAPI

api = ClinicalTrialsAPI()
trial = api.get_trial_details('NCT03758118')

if trial:
    print('=== TRIAL ENCONTRADO ===')
    print(f"NCT ID: {trial.get('protocolSection', {}).get('identificationModule', {}).get('nctId')}")
    print(f"Titulo: {trial.get('protocolSection', {}).get('identificationModule', {}).get('briefTitle')}")
    
    # Verificar si tiene resultados
    results = trial.get('resultsSection', {})
    if results:
        print(f'Resultados: SI')
        print(f'Keys: {list(results.keys())}')
        
        # Outcome measures
        outcomes = results.get('outcomeMeasuresModule', {}).get('outcomeMeasures', [])
        print(f'Outcomes: {len(outcomes)}')
        for i, out in enumerate(outcomes[:2]):
            print(f"  Outcome {i+1}: {out.get('title', 'N/A')[:60]}")
            print(f"    Type: {out.get('type', 'N/A')}")
            groups = out.get('groups', [])
            print(f"    Groups: {len(groups)}")
            for g in groups:
                print(f"      Group {g.get('groupId')}: {g.get('value')} (spread: {g.get('spread')})")
                print(f"      CI: [{g.get('lowerLimit')}-{g.get('upperLimit')}]")
    else:
        print('Resultados: NO')
else:
    print('No se pudo obtener el trial')
